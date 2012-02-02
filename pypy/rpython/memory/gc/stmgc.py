from pypy.rpython.lltypesystem import lltype, llmemory, llarena
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.lltypesystem.llmemory import raw_malloc_usage
from pypy.rpython.memory.gc.base import GCBase
from pypy.rlib.rarithmetic import LONG_BIT
from pypy.rlib.debug import ll_assert


WORD = LONG_BIT // 8
NULL = llmemory.NULL

first_gcflag = 1 << (LONG_BIT//2)

GCFLAG_GLOBAL     = first_gcflag << 0
GCFLAG_WAS_COPIED = first_gcflag << 1


def always_inline(fn):
    fn._always_inline_ = True
    return fn
def dont_inline(fn):
    fn._dont_inline_ = True
    return fn


class StmOperations(object):
    def _freeze_(self):
        return True


class StmGC(GCBase):
    _alloc_flavor_ = "raw"
    inline_simple_malloc = True
    inline_simple_malloc_varsize = True
    needs_write_barrier = "stm"
    prebuilt_gc_objects_are_static_roots = False
    malloc_zero_filled = True    # xxx?

    HDR = lltype.Struct('header', ('tid', lltype.Signed),
                                  ('version', lltype.Signed))
    typeid_is_in_field = 'tid'
    withhash_flag_is_in_field = 'tid', 'XXX'

    GCTLS = lltype.Struct('GCTLS', ('nursery_free', llmemory.Address),
                                   ('nursery_top', llmemory.Address),
                                   ('nursery_start', llmemory.Address),
                                   ('nursery_size', lltype.Signed),
                                   ('malloc_flags', lltype.Signed))


    def __init__(self, config, stm_operations,
                 max_nursery_size=1024,
                 **kwds):
        GCBase.__init__(self, config, **kwds)
        self.stm_operations = stm_operations
        self.max_nursery_size = max_nursery_size
        #
        self.declare_readers()
        self.declare_write_barrier()

    def setup(self):
        """Called at run-time to initialize the GC."""
        GCBase.setup(self)
        self.main_thread_tls = self.setup_thread(True)

    def _alloc_nursery(self):
        nursery = llarena.arena_malloc(self.max_nursery_size, 1)
        if not nursery:
            raise MemoryError("cannot allocate nursery")
        return nursery

    def _free_nursery(self, nursery):
        llarena.arena_free(nursery)

    def setup_thread(self, in_main_thread):
        tls = lltype.malloc(self.GCTLS, flavor='raw')
        self.stm_operations.set_tls(self, llmemory.cast_ptr_to_adr(tls))
        tls.nursery_start = self._alloc_nursery()
        tls.nursery_size  = self.max_nursery_size
        tls.nursery_free  = tls.nursery_start
        tls.nursery_top   = tls.nursery_start + tls.nursery_size
        #
        # XXX for now, we use as the "global area" the nursery of the
        # main thread.  So allocation in the main thread is the same as
        # allocation in another thread, except that the new objects
        # should be immediately marked as GCFLAG_GLOBAL.
        if in_main_thread:
            tls.malloc_flags = GCFLAG_GLOBAL
        else:
            tls.malloc_flags = 0
        return tls

    def teardown_thread(self):
        tls = self.get_tls()
        self.stm_operations.set_tls(self, NULL)
        self._free_nursery(tls.nursery_start)
        lltype.free(tls, flavor='raw')

    @always_inline
    def get_tls(self):
        tls = self.stm_operations.get_tls()
        return llmemory.cast_adr_to_ptr(tls, lltype.Ptr(self.GCTLS))

    def allocate_bump_pointer(self, size):
        return self._allocate_bump_pointer(self.get_tls(), size)

    @always_inline
    def _allocate_bump_pointer(self, tls, size):
        free = tls.nursery_free
        top  = tls.nursery_top
        new  = free + size
        tls.nursery_free = new
        if new > top:
            free = self.local_collection(free)
        return free

    @dont_inline
    def local_collection(self, oldfree):
        raise MemoryError("nursery exhausted")   # XXX for now


    def malloc_fixedsize_clear(self, typeid, size,
                               needs_finalizer=False,
                               is_finalizer_light=False,
                               contains_weakptr=False):
        assert not needs_finalizer, "XXX"
        assert not contains_weakptr, "XXX"
        #
        # Check the mode: either in a transactional thread, or in
        # the main thread.  For now we do the same thing in both
        # modes, but set different flags.
        tls = self.get_tls()
        flags = tls.malloc_flags
        #
        # Get the memory from the nursery.
        size_gc_header = self.gcheaderbuilder.size_gc_header
        totalsize = size_gc_header + size
        result = self._allocate_bump_pointer(tls, totalsize)
        #
        # Build the object.
        llarena.arena_reserve(result, totalsize)
        obj = result + size_gc_header
        self.init_gc_object(result, typeid, flags=flags)
        #
        return llmemory.cast_adr_to_ptr(obj, llmemory.GCREF)


    def _malloc_local_raw(self, size):
        # for _stm_write_barrier_global(): a version of malloc that does
        # no initialization of the malloc'ed object
        size_gc_header = self.gcheaderbuilder.size_gc_header
        totalsize = size_gc_header + size
        result = self.allocate_bump_pointer(totalsize)
        llarena.arena_reserve(result, totalsize)
        obj = result + size_gc_header
        return obj


    @always_inline
    def combine(self, typeid16, flags):
        return llop.combine_ushort(lltype.Signed, typeid16, flags)

    @always_inline
    def init_gc_object(self, addr, typeid16, flags=0):
        hdr = llmemory.cast_adr_to_ptr(addr, lltype.Ptr(self.HDR))
        hdr.tid = self.combine(typeid16, flags)

    # ----------

    def declare_readers(self):
        # Reading functions.  Defined here to avoid the extra burden of
        # passing 'self' explicitly.
        stm_operations = self.stm_operations
        #
        @always_inline
        def read_signed(obj, offset):
            if self.header(obj).tid & GCFLAG_GLOBAL == 0:
                return (obj + offset).signed[0]    # local obj: read directly
            else:
                return _read_word_global(obj, offset)   # else: call a helper
        self.read_signed = read_signed
        #
        @dont_inline
        def _read_word_global(obj, offset):
            hdr = self.header(obj)
            if hdr.tid & GCFLAG_WAS_COPIED != 0:
                #
                # Look up in the thread-local dictionary.
                localobj = stm_operations.tldict_lookup(obj)
                if localobj:
                    ll_assert(self.header(localobj).tid & GCFLAG_GLOBAL == 0,
                              "stm_read: tldict_lookup() -> GLOBAL obj")
                    return (localobj + offset).signed[0]
            #
            return stm_operations.stm_read_word(obj, offset)


    def declare_write_barrier(self):
        # Write barrier.  Defined here to avoid the extra burden of
        # passing 'self' explicitly.
        stm_operations = self.stm_operations
        #
        @always_inline
        def write_barrier(obj):
            if self.header(obj).tid & GCFLAG_GLOBAL != 0:
                obj = _stm_write_barrier_global(obj)
            return obj
        self.write_barrier = write_barrier
        #
        @dont_inline
        def _stm_write_barrier_global(obj):
            # we need to find of make a local copy
            hdr = self.header(obj)
            if hdr.tid & GCFLAG_WAS_COPIED == 0:
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
            try:
                localobj = self._malloc_local_raw(size)
            except MemoryError:
                # XXX
                fatalerror("MemoryError in _stm_write_barrier_global -- sorry")
                return llmemory.NULL
            #
            # Initialize the copy by doing an stm raw copy of the bytes
            stm_operations.stm_copy_transactional_to_raw(obj, localobj, size)
            #
            # The raw copy done above includes all header fields.
            # Check at least the gc flags of the copy.
            hdr = self.header(obj)
            localhdr = self.header(localobj)
            GCFLAGS = (GCFLAG_GLOBAL | GCFLAG_WAS_COPIED)
            ll_assert(hdr.tid & GCFLAGS == GCFLAGS,
                      "stm_write: bogus flags on source object")
            ll_assert(localhdr.tid & GCFLAGS == GCFLAGS,
                      "stm_write: flags not copied!")
            #
            # Remove the GCFLAG_GLOBAL from the copy
            localhdr.tid &= ~GCFLAG_GLOBAL
            #
            # Register the object as a valid copy
            stm_operations.tldict_add(obj, localobj)
            #
            return localobj
