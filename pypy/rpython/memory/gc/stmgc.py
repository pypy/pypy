from pypy.rpython.lltypesystem import lltype, llmemory, llarena
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.lltypesystem.llmemory import raw_malloc_usage
from pypy.rpython.memory.gc.base import GCBase
from pypy.rlib.rarithmetic import LONG_BIT


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
        self.stm_operations.set_tls(llmemory.cast_ptr_to_adr(tls))
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
        self.stm_operations.set_tls(NULL)
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


    @always_inline
    def combine(self, typeid16, flags):
        return llop.combine_ushort(lltype.Signed, typeid16, flags)

    @always_inline
    def init_gc_object(self, addr, typeid16, flags=0):
        hdr = llmemory.cast_adr_to_ptr(addr, lltype.Ptr(self.HDR))
        hdr.tid = self.combine(typeid16, flags)
