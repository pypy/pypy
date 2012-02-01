from pypy.rpython.lltypesystem import lltype, llmemory, llarena
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
                                   ('nursery_size', lltype.Signed))


    def __init__(self, config, stm_operations,
                 max_nursery_size=1024,
                 **kwds):
        GCBase.__init__(self, config, **kwds)
        self.stm_operations = stm_operations
        self.max_nursery_size = max_nursery_size


    def setup(self):
        """Called at run-time to initialize the GC."""
        GCBase.setup(self)
        self.setup_thread()

    def _alloc_nursery(self):
        nursery = llarena.arena_malloc(self.max_nursery_size, 1)
        if not nursery:
            raise MemoryError("cannot allocate nursery")
        return nursery

    def setup_thread(self):
        tls = lltype.malloc(self.GCTLS, flavor='raw')
        self.stm_operations.set_tls(llmemory.cast_ptr_to_adr(tls))
        tls.nursery_start = self._alloc_nursery()
        tls.nursery_size  = self.max_nursery_size
        tls.nursery_free  = tls.nursery_start
        tls.nursery_top   = tls.nursery_start + tls.nursery_size

    @always_inline
    def get_tls(self):
        tls = self.stm_operations.get_tls()
        return llmemory.cast_adr_to_ptr(tls, lltype.Ptr(self.GCTLS))

    @always_inline
    def allocate_bump_pointer(self, size):
        tls = self.get_tls()
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
