"""
Minimal GC interface for STM.  The actual GC is implemented in C code,
from rpython/translator/stm/src_stm/.
"""

from rpython.memory.gc.base import MovingGCBase
from rpython.rtyper.lltypesystem import lltype, llmemory, llgroup, rffi
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rlib.debug import ll_assert


class PrebuiltStmGCHeader(llmemory.Symbolic):
    def __init__(self, typeid16):
        self.typeid16 = typeid16
    def annotation(self):
        from rpython.annotator import model
        return model.SomePtr(self.lltype())
    def lltype(self):
        return lltype.Ptr(StmGC.HDR)


class StmGC(MovingGCBase):
    _alloc_flavor_ = "raw"
    inline_simple_malloc = True
    inline_simple_malloc_varsize = True
    needs_write_barrier = True
    prebuilt_gc_objects_are_static_roots = False
    malloc_zero_filled = True
    #gcflag_extra = GCFLAG_EXTRA

    HDR = rffi.COpaque('struct stm_object_s')
    typeid_is_in_field = None

    TRANSLATION_PARAMS = {}

    def get_type_id(self, obj):
        return llop.stm_get_tid(llgroup.HALFWORD, obj)

    def init_gc_object_immortal(self, addr, typeid16, flags=0):
        assert flags == 0
        return PrebuiltStmGCHeader(typeid16)

    def malloc_fixedsize_clear(self, typeid, size,
                               needs_finalizer=False,
                               is_finalizer_light=False,
                               contains_weakptr=False):
        ll_assert(not needs_finalizer, 'XXX')
        ll_assert(not is_finalizer_light, 'XXX')
        ll_assert(not contains_weakptr, 'XXX')
        return llop.stm_allocate(llmemory.GCREF, size, typeid)

    def malloc_varsize_clear(self, typeid, length, size, itemsize,
                             offset_to_length):
        ll_assert(False, 'XXX')
        return llop.stm_allocate(llmemory.GCREF)

    def collect(self, gen=1):
        """Do a minor (gen=0) or major (gen>0) collection."""
        if gen > 0:
            llop.stm_major_collect(lltype.Void)
        else:
            llop.stm_minor_collect(lltype.Void)

    def writebarrier_before_copy(self, source_addr, dest_addr,
                                 source_start, dest_start, length):
        ll_assert(False, 'XXX')
        return False

    def id(self, gcobj):
        return llop.stm_id(lltype.Signed, gcobj)

    def identityhash(self, gcobj):
        return llop.stm_hash(lltype.Signed, gcobj)
