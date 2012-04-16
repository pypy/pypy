from pypy.rpython.lltypesystem import lltype, llmemory, llarena, llgroup
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.lltypesystem.llmemory import raw_malloc_usage
from pypy.rpython.memory.gc.base import GCBase, MovingGCBase
from pypy.rpython.memory.support import mangle_hash
from pypy.rpython.annlowlevel import llhelper
from pypy.rlib.rarithmetic import LONG_BIT
from pypy.rlib.debug import ll_assert, debug_start, debug_stop, fatalerror
from pypy.rlib.debug import debug_print
from pypy.module.thread import ll_thread


WORD = LONG_BIT // 8
NULL = llmemory.NULL

first_gcflag = 1 << (LONG_BIT//2)

# Terminology:
#
#   - Objects can be LOCAL or GLOBAL.  This is what STM is based on.
#     Local objects are not visible to any other transaction, whereas
#     global objects are, and need care.
#
#   - Each object lives either in the shared area, or in a thread-local
#     nursery.  The shared area contains:
#       - the prebuilt objects
#       - the small objects allocated via minimarkpage.py
#       - the non-small raw-malloced objects
#
#   - The GLOBAL objects are all located in the shared area.
#     All global objects are non-movable.
#
#   - The LOCAL objects might be YOUNG or OLD depending on whether they
#     already survived a collection.  YOUNG LOCAL objects are either in
#     the nursery or, if they are big, raw-malloced.  OLD LOCAL objects
#     are in the shared area.  Getting the write barrier right for both
#     this and the general STM mechanisms is tricky, so for now this GC
#     is not actually generational (slow when running long transactions
#     or before running transactions at all).
#
GCFLAG_GLOBAL     = first_gcflag << 0     # keep in sync with et.c
GCFLAG_WAS_COPIED = first_gcflag << 1     # keep in sync with et.c
GCFLAG_HAS_SHADOW = first_gcflag << 2
GCFLAG_FIXED_HASH = first_gcflag << 3
GCFLAG_WEAKREF    = first_gcflag << 4
GCFLAG_VISITED    = first_gcflag << 5


def always_inline(fn):
    fn._always_inline_ = True
    return fn
def dont_inline(fn):
    fn._dont_inline_ = True
    return fn


class StmGC(MovingGCBase):
    _alloc_flavor_ = "raw"
    inline_simple_malloc = True
    inline_simple_malloc_varsize = True
    #needs_write_barrier = "stm"
    prebuilt_gc_objects_are_static_roots = False
    malloc_zero_filled = True    # xxx?

    HDR = lltype.Struct('header', ('tid', lltype.Signed),
                                  ('version', llmemory.Address))
    typeid_is_in_field = 'tid'
    withhash_flag_is_in_field = 'tid', GCFLAG_FIXED_HASH

    TRANSLATION_PARAMS = {
        'stm_operations': 'use_real_one',
        'nursery_size': 32*1024*1024,           # 32 MB

        #"page_size": 1024*WORD,                 # copied from minimark.py
        #"arena_size": 65536*WORD,               # copied from minimark.py
        #"small_request_threshold": 35*WORD,     # copied from minimark.py
    }

    def __init__(self, config,
                 stm_operations='use_emulator',
                 nursery_size=1024,
                 #page_size=16*WORD,
                 #arena_size=64*WORD,
                 #small_request_threshold=5*WORD,
                 #ArenaCollectionClass=None,
                 **kwds):
        MovingGCBase.__init__(self, config, multithread=True, **kwds)
        #
        if isinstance(stm_operations, str):
            assert stm_operations == 'use_real_one', (
                "XXX not provided so far: stm_operations == %r" % (
                stm_operations,))
            from pypy.translator.stm.stmgcintf import StmOperations
            stm_operations = StmOperations()
        #
        from pypy.rpython.memory.gc import stmshared
        self.stm_operations = stm_operations
        self.nursery_size = nursery_size
        self.sharedarea = stmshared.StmGCSharedArea(self)
        self.transactional_mode = False
        #
        def _get_size(obj):     # indirection to hide 'self'
            return self.get_size(obj)
        self._getsize_fn = _get_size
        #
        ##for size, TYPE in PRIMITIVE_SIZES.items():
        ##    self.declare_reader(size, TYPE)
        self.declare_write_barrier()

    def setup(self):
        """Called at run-time to initialize the GC."""
        #
        # Hack: MovingGCBase.setup() sets up stuff related to id(), which
        # we implement differently anyway.  So directly call GCBase.setup().
        GCBase.setup(self)
        #
        self.stm_operations.setup_size_getter(
                llhelper(self.stm_operations.GETSIZE, self._getsize_fn))
        #
        self.sharedarea.setup()
        #
        from pypy.rpython.memory.gc.stmtls import StmGCTLS
        self.main_thread_tls = StmGCTLS(self, in_main_thread=True)
        self.main_thread_tls.start_transaction()

    def setup_thread(self):
        from pypy.rpython.memory.gc.stmtls import StmGCTLS
        StmGCTLS(self, in_main_thread=False)

    def teardown_thread(self):
        self.get_tls().teardown_thread()

    @always_inline
    def get_tls(self):
        from pypy.rpython.memory.gc.stmtls import StmGCTLS
        tls = self.stm_operations.get_tls()
        return StmGCTLS.cast_address_to_tls_object(tls)

    def enter_transactional_mode(self):
        ll_assert(not self.transactional_mode, "already in transactional mode")
        self.main_thread_tls.enter_transactional_mode()
        self.transactional_mode = True

    def leave_transactional_mode(self):
        ll_assert(self.transactional_mode, "already in non-transactional mode")
        self.transactional_mode = False
        self.main_thread_tls.leave_transactional_mode()

    # ----------

    def malloc_fixedsize_clear(self, typeid, size,
                               needs_finalizer=False,
                               is_finalizer_light=False,
                               contains_weakptr=False):
        #assert not needs_finalizer, "XXX" --- finalizer is just ignored
        #
        # Check the mode: either in a transactional thread, or in
        # the main thread.  For now we do the same thing in both
        # modes, but set different flags.
        #
        # Get the memory from the nursery.
        size_gc_header = self.gcheaderbuilder.size_gc_header
        totalsize = size_gc_header + size
        result = self.get_tls().allocate_bump_pointer(totalsize)
        #
        # Build the object.
        llarena.arena_reserve(result, totalsize)
        obj = result + size_gc_header
        flags = 0
        if contains_weakptr:   # check constant-folded
            flags |= GCFLAG_WEAKREF
        self.init_gc_object(result, typeid, flags=flags)
        #
        return llmemory.cast_adr_to_ptr(obj, llmemory.GCREF)


    def malloc_varsize_clear(self, typeid, length, size, itemsize,
                             offset_to_length):
        # XXX blindly copied from malloc_fixedsize_clear() for now.
        # XXX Be more subtle, e.g. detecting overflows, at least
        size_gc_header = self.gcheaderbuilder.size_gc_header
        nonvarsize = size_gc_header + size
        totalsize = nonvarsize + itemsize * length
        totalsize = llarena.round_up_for_allocation(totalsize)
        result = self.get_tls().allocate_bump_pointer(totalsize)
        llarena.arena_reserve(result, totalsize)
        obj = result + size_gc_header
        self.init_gc_object(result, typeid, flags=0)
        (obj + offset_to_length).signed[0] = length
        return llmemory.cast_adr_to_ptr(obj, llmemory.GCREF)


    def collect(self, gen=1):
        self.get_tls().local_collection()
        if gen > 0:
            debug_print("XXX not doing a global collect()")

    def start_transaction(self):
        self.get_tls().start_transaction()

    def commit_transaction(self):
        self.get_tls().stop_transaction()


    @always_inline
    def get_type_id(self, obj):
        tid = self.header(obj).tid
        return llop.extract_ushort(llgroup.HALFWORD, tid)

    @always_inline
    def combine(self, typeid16, flags):
        return llop.combine_ushort(lltype.Signed, typeid16, flags)

    @always_inline
    def init_gc_object(self, addr, typeid16, flags=0):
        hdr = llmemory.cast_adr_to_ptr(addr, lltype.Ptr(self.HDR))
        hdr.tid = self.combine(typeid16, flags)

    def init_gc_object_immortal(self, addr, typeid16, flags=0):
        flags |= GCFLAG_GLOBAL
        self.init_gc_object(addr, typeid16, flags)

    # ----------

##    TURNED OFF, maybe temporarily: the following logic is now entirely
##    done by C macros and functions.
##
##    def declare_reader(self, size, TYPE):
##        # Reading functions.  Defined here to avoid the extra burden of
##        # passing 'self' explicitly.
##        assert rffi.sizeof(TYPE) == size
##        PTYPE = rffi.CArrayPtr(TYPE)
##        stm_read_int = getattr(self.stm_operations, 'stm_read_int%d' % size)
##        #
##        @always_inline
##        def reader(obj, offset):
##            if self.header(obj).tid & GCFLAG_GLOBAL == 0:
##                adr = rffi.cast(PTYPE, obj + offset)
##                return adr[0]                      # local obj: read directly
##            else:
##                return stm_read_int(obj, offset)   # else: call a helper
##        setattr(self, 'read_int%d' % size, reader)
##        #
##        @dont_inline
##        def _read_word_global(obj, offset):
##            hdr = self.header(obj)
##            if hdr.tid & GCFLAG_WAS_COPIED != 0:
##                #
##                # Look up in the thread-local dictionary.
##                localobj = stm_operations.tldict_lookup(obj)
##                if localobj:
##                    ll_assert(self.header(localobj).tid & GCFLAG_GLOBAL == 0,
##                              "stm_read: tldict_lookup() -> GLOBAL obj")
##                    return (localobj + offset).signed[0]
##            #
##            return stm_operations.stm_read_word(obj, offset)


    def declare_write_barrier(self):
        # Write barrier.  Defined here to avoid the extra burden of
        # passing 'self' explicitly.
        stm_operations = self.stm_operations
        #
        @always_inline
        def stm_writebarrier(obj):
            """The write barrier must be called on any object that may be
            a global.  It looks for, and possibly makes, a local copy of
            this object.  The result of this call is the local copy ---
            or 'obj' itself if it is already local.
            """
            if self.header(obj).tid & GCFLAG_GLOBAL != 0:
                obj = _stm_write_barrier_global(obj)
            return obj
        self.stm_writebarrier = stm_writebarrier
        #
        @dont_inline
        def _stm_write_barrier_global(obj):
            tls = self.get_tls()
            if not tls.in_transaction():
                return obj # not in transaction: only when running the code
                           # in _run_thread(), i.e. in sub-threads outside
                           # transactions.  xxx statically detect this case?
            # we need to find or make a local copy
            hdr = self.header(obj)
            if hdr.tid & GCFLAG_WAS_COPIED == 0:
                #
                # in this case, we are sure that we don't have a copy
                hdr.tid |= GCFLAG_WAS_COPIED
                # ^^^ non-protected write, but concurrent writes should
                #     have the same effect, so fine
            else:
                # in this case, we need to check first
                localobj = stm_operations.tldict_lookup(obj)
                if localobj:
                    hdr = self.header(localobj)
                    ll_assert(hdr.tid & GCFLAG_GLOBAL == 0,
                              "stm_write: tldict_lookup() -> GLOBAL obj")
                    ll_assert(hdr.tid & GCFLAG_WAS_COPIED != 0,
                              "stm_write: tldict_lookup() -> non-COPIED obj")
                    return localobj
            #
            # Here, we need to really make a local copy
            size = self.get_size(obj)
            totalsize = self.gcheaderbuilder.size_gc_header + size
            try:
                localobj = tls.malloc_local_copy(totalsize)
            except MemoryError:
                # XXX
                fatalerror("MemoryError in _stm_write_barrier_global -- sorry")
                return llmemory.NULL
            #
            # Initialize the copy by doing an stm raw copy of the bytes
            stm_operations.stm_copy_transactional_to_raw(obj, localobj, size)
            #
            # The raw copy done above does not include the header fields.
            hdr = self.header(obj)
            localhdr = self.header(localobj)
            GCFLAGS = (GCFLAG_GLOBAL | GCFLAG_WAS_COPIED)
            ll_assert(hdr.tid & GCFLAGS == GCFLAGS,
                      "stm_write: bogus flags on source object")
            #
            # Remove the GCFLAG_GLOBAL from the copy
            localhdr.tid = hdr.tid & ~GCFLAG_GLOBAL
            #
            # Set the 'version' field of the local copy to be a pointer
            # to the global obj.  (The field is called 'version' because
            # of its use by the C STM library: on global objects (only),
            # it is a version number.)
            localhdr.version = obj
            #
            # Register the object as a valid copy
            stm_operations.tldict_add(obj, localobj)
            #
            return localobj
        #
        def stm_normalize_global(obj):
            """Normalize a pointer for the purpose of equality
            comparison with another pointer.  If 'obj' is the local
            version of an existing global object, then returns the
            global object.  Don't use for e.g. hashing, because if 'obj'
            is a purely local object, it just returns 'obj' --- which
            will change at the next commit.
            """
            if not obj:
                return obj
            tid = self.header(obj).tid
            if tid & (GCFLAG_GLOBAL|GCFLAG_WAS_COPIED) != GCFLAG_WAS_COPIED:
                return obj
            # the only relevant case: it's the local copy of a global object
            return self.header(obj).version
        self.stm_normalize_global = stm_normalize_global

    # ----------
    # id() and identityhash() support

    def id_or_identityhash(self, gcobj, is_hash):
        """Implement the common logic of id() and identityhash()
        of an object, given as a GCREF.
        """
        raise NotImplementedError
        obj = llmemory.cast_ptr_to_adr(gcobj)
        hdr = self.header(obj)
        #
        if hdr.tid & GCFLAG_GLOBAL == 0:
            #
            # The object is a local object.  Find or allocate a corresponding
            # global object.
            if hdr.tid & (GCFLAG_WAS_COPIED | GCFLAG_HAS_SHADOW) == 0:
                #
                # We need to allocate a global object here.  We only allocate
                # it for now; it is left completely uninitialized.
                size = self.get_size(obj)
                tls = self.collector.get_tls()
                globalobj = self._malloc_global_raw(tls, size)
                self.header(globalobj).tid = GCFLAG_GLOBAL
                #
                # Update the header of the local 'obj'
                hdr.tid |= GCFLAG_HAS_SHADOW
                hdr.version = globalobj
                #
            else:
                # There is already a corresponding globalobj
                globalobj = hdr.version
            #
            obj = globalobj
        #
        ll_assert(self.header(obj).tid & GCFLAG_GLOBAL != 0,
                  "id_or_identityhash: unexpected local object")
        i = llmemory.cast_adr_to_int(obj)
        if is_hash:
            # For identityhash(), we need a special case for some
            # prebuilt objects: their hash must be the same before
            # and after translation.  It is stored as an extra word
            # after the object.  But we cannot use it for id()
            # because the stored value might clash with a real one.
            if self.header(obj).tid & GCFLAG_FIXED_HASH:
                size = self.get_size(obj)
                i = (obj + size).signed[0]
            else:
                # mangle the hash value to increase the dispertion
                # on the trailing bits, but only if !GCFLAG_FIXED_HASH
                i = mangle_hash(i)
        return i

    def id(self, gcobj):
        return self.id_or_identityhash(gcobj, False)

    def identityhash(self, gcobj):
        return self.id_or_identityhash(gcobj, True)
