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
#     All GLOBAL objects are non-movable.
#
#   - The LOCAL objects might be YOUNG or OLD depending on whether they
#     already survived a collection.  YOUNG LOCAL objects are either in
#     the nursery or, if they are big, raw-malloced.  OLD LOCAL objects
#     are in the shared area.  Getting the write barrier right for both
#     this and the general STM mechanisms is tricky, so for now this GC
#     is not actually generational (slow when running long transactions
#     or before running transactions at all).
#
#   - A few details are different depending on the running mode:
#     either "transactional" or "non-transactional".  The transactional
#     mode is where we have multiple threads, in a transaction.run()
#     call.  The non-transactional mode has got only the main thread.
#
# GC Flags on objects:
#
#   - GCFLAG_GLOBAL: identifies GLOBAL objects.  All prebuilt objects
#     start as GLOBAL; conversely, all freshly allocated objects start
#     as LOCAL.  But they may switch between the two; see below.
#     All objects that are or have been GLOBAL are immortal for now
#     (global_collect() will be done later).
#
#   - GCFLAG_WAS_COPIED: means that the object is either a LOCAL COPY
#     or, if GLOBAL, then it has or had at least one LOCAL COPY.  Used
#     in transactional mode only; see below.
#
#   - GCFLAG_VISITED: used during collections to flag objects found to be
#     surviving.  Between collections, it must be set on the LOCAL COPY
#     objects or the ones from 'mt_global_turned_local' (see below), and
#     only on them.
#
#   - GCFLAG_HAS_SHADOW: set on nursery objects whose id() or identityhash()
#     was taken.  Means that we already have a corresponding object allocated
#     outside the nursery.
#
#   - GCFLAG_FIXED_HASH: only on some prebuilt objects.  For identityhash().
#
# When the mutator (= the program outside the GC) wants to write to an
# object, stm_writebarrier() does something special on GLOBAL objects:
#
#   - In non-transactional mode, the write barrier turns the object LOCAL
#     and add it in the list 'main_thread_tls.mt_global_turned_local'.
#     This list contains all previously-GLOBAL objects that have been
#     modified.  [XXX:TODO]Objects turned LOCAL are changed back to GLOBAL and
#     removed from 'mt_global_turned_local' by the next collection,
#     unless they are also found in the stack (the reason being that if
#     they are in the stack and stm_writebarrier() has already been
#     called, then it might not be called a second time if they are
#     changed again after collection).
#
#   - In transactional mode, the write barrier creates a LOCAL COPY of
#     the object and returns it (or, if already created by the same
#     transaction, finds it again).  The list of LOCAL COPY objects has
#     a role similar to 'mt_global_turned_local', but is maintained by C
#     code (see tldict_lookup()).
#
# Invariant: between two transactions, all objects visible from the current
# thread are always GLOBAL.  In particular:
#
#   - The LOCAL object of a thread are not visible at all from other threads.
#     This means that in transactional mode there is *no* pointer from a
#     GLOBAL object directly to a LOCAL object.
#
#   - At the end of enter_transactional_mode(), and at the beginning of
#     leave_transactional_mode(), *all* objects everywhere are GLOBAL.
#
# Collection: for now we have only local_collection(), which ignores all
# GLOBAL objects.
#
#   - In non-transactional mode, we use 'mt_global_turned_local' as a list
#     of roots, together with the stack.  By construction, all objects that
#     are still GLOBAL can be ignored, because they cannot point to a LOCAL
#     object (except to a 'mt_global_turned_local' object).
#
#   - In transactional mode, we similarly use the list maintained by C code
#     of the LOCAL COPY objects of the current transaction, together with
#     the stack.  Again, GLOBAL objects can be ignored because they have no
#     pointer to any LOCAL object at all in that mode.
#
#   - A special case is the end-of-transaction collection, done by the same
#     local_collection() with a twist: all pointers to a LOCAL COPY object
#     are replaced with copies to the corresponding GLOBAL original.  When
#     it is done, we mark all surviving LOCAL objects as GLOBAL too, and we
#     are back to the situation where this thread sees only GLOBAL objects.
#     What we leave to the C code to do "as a finishing touch" is to copy
#     transactionally the content of the LOCAL COPY objects back over the
#     GLOBAL originals; before this is done, the transaction can be aborted
#     at any point with no visible side-effect on any object that other
#     threads can see.
#
# All objects have an address-sized 'version' field in their header.  On
# GLOBAL objects, it is used as a version by C code to handle STM (it must
# be set to 0 when the object first turns GLOBAL).   On the LOCAL objects,
# though, it is abused here in the GC:
#
#   - if GCFLAG_WAS_COPIED, it points to the GLOBAL original.
#
#   - if GCFLAG_HAS_SHADOW, to the shadow object outside the nursery.
#     (It is not used on any other nursery object.)
#
#   - it contains the 'next' object of the 'mt_global_turned_local' list.
#
#   - it contains the 'next' object of the 'sharedarea_tls.chained_list'
#     list, which describes all LOCAL objects malloced outside the nursery
#     (excluding the ones that were GLOBAL at some point).
#
#   - for nursery objects, during collection, if they are copied outside
#     the nursery, they grow GCFLAG_VISITED and their 'version' points
#     to the fresh copy.
#

GCFLAG_GLOBAL     = first_gcflag << 0     # keep in sync with et.c
GCFLAG_WAS_COPIED = first_gcflag << 1     # keep in sync with et.c
GCFLAG_VISITED    = first_gcflag << 2
GCFLAG_HAS_SHADOW = first_gcflag << 3
GCFLAG_FIXED_HASH = first_gcflag << 4
GCFLAG_PREBUILT   = first_gcflag << 5


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
        def _stm_getsize(obj):     # indirection to hide 'self'
            return self.get_size(obj)
        self._stm_getsize = _stm_getsize
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
        # The following line causes the _stm_getsize() function to be
        # generated in the C source with a specific signature, where it
        # can be called by the C code.
        llop.nop(lltype.Void, llhelper(self.stm_operations.GETSIZE,
                                       self._stm_getsize))
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
        tls = self.get_tls()
        result = tls.allocate_bump_pointer(totalsize)
        #
        # Build the object.
        llarena.arena_reserve(result, totalsize)
        obj = result + size_gc_header
        self.init_gc_object(result, typeid, flags=0)
        if contains_weakptr:   # check constant-folded
            tls.fresh_new_weakref(obj)
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

    def stop_transaction(self):
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
        flags |= GCFLAG_GLOBAL | GCFLAG_PREBUILT
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
            if tls is self.main_thread_tls:
                # not in a transaction: the main thread writes to a global obj.
                # In this case we turn the object local.
                tls.main_thread_writes_to_global_obj(obj)
                return obj
            #
            # else, in a transaction: we find or make a local copy of the
            # global object
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
            GCFLAGS = (GCFLAG_GLOBAL | GCFLAG_WAS_COPIED | GCFLAG_VISITED)
            ll_assert(hdr.tid & GCFLAGS == (GCFLAG_GLOBAL | GCFLAG_WAS_COPIED),
                      "stm_write: bogus flags on source object")
            #
            # Remove the GCFLAG_GLOBAL from the copy, and add GCFLAG_VISITED
            localhdr.tid = hdr.tid + (GCFLAG_VISITED - GCFLAG_GLOBAL)
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
        obj = llmemory.cast_ptr_to_adr(gcobj)
        hdr = self.header(obj)
        tls = self.get_tls()
        if tls.is_in_nursery(obj):
            #
            # The object is still in the nursery of the current TLS.
            # (It cannot be in the nursery of a different thread, because
            # such objects are not visible to different threads at all.)
            #
            ll_assert(hdr.tid & GCFLAG_WAS_COPIED == 0, "id: WAS_COPIED?")
            #
            if hdr.tid & GCFLAG_HAS_SHADOW == 0:
                #
                # We need to allocate a global object here.  We only allocate
                # it for now; it is left completely uninitialized.
                size_gc_header = self.gcheaderbuilder.size_gc_header
                size = self.get_size(obj)
                totalsize = size_gc_header + size
                fixedobj = tls.sharedarea_tls.malloc_object(totalsize)
                tls.sharedarea_tls.add_regular(fixedobj)
                self.header(fixedobj).tid = 0     # GCFLAG_VISITED is off
                #
                # Update the header of the local 'obj'
                hdr.tid |= GCFLAG_HAS_SHADOW
                hdr.version = fixedobj
                #
            else:
                # There is already a corresponding fixedobj
                fixedobj = hdr.version
            #
            obj = fixedobj
            #
        elif hdr.tid & (GCFLAG_GLOBAL|GCFLAG_WAS_COPIED) == GCFLAG_WAS_COPIED:
            #
            # The object is the local copy of a LOCAL-GLOBAL pair.
            obj = hdr.version
        #
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
