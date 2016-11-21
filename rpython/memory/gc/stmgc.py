"""
Minimal GC interface for STM.  The actual GC is implemented in C code,
from rpython/translator/stm/src_stm/.
"""

from rpython.memory.gc.base import GCBase, MovingGCBase
from rpython.rtyper.lltypesystem import lltype, llmemory, llgroup, llarena
from rpython.rtyper.lltypesystem import rffi
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rlib.debug import ll_assert
from rpython.rlib.rarithmetic import LONG_BIT, r_uint
from rpython.rtyper.extregistry import ExtRegistryEntry
from rpython.translator.stm import stmgcintf
from rpython.rlib import rstm
from rpython.rlib.objectmodel import we_are_translated
from rpython.rtyper.lltypesystem.llmemory import raw_malloc_usage

WORD = LONG_BIT // 8
NULL = llmemory.NULL



class StmGC(MovingGCBase):
    _alloc_flavor_ = "raw"
    inline_simple_malloc = True
    inline_simple_malloc_varsize = True
    needs_write_barrier = "stm"
    prebuilt_gc_objects_are_static_roots = False
    ignore_immutable_static_roots = False
    malloc_zero_filled = False
    object_minimal_size = 16
    #gcflag_extra = GCFLAG_EXTRA

    HDR = stmgcintf.GCPTR.TO
    typeid_is_in_field = None

    VISIT_FPTR = lltype.Ptr(lltype.FuncType([llmemory.Address], lltype.Void))

    JIT_WB_IF_FLAG = 0x1   # from stmgc.h
    JIT_WB_CARDS_SET = 0x8 # from stmgc.h
    stm_fast_alloc = rstm.FAST_ALLOC
    minimal_size_in_nursery = 16     # hard-coded lower limit

    TRANSLATION_PARAMS = {
    }

    def get_type_id(self, obj):
        return llop.stm_addr_get_tid(llgroup.HALFWORD, obj)

    def get_card_base_itemsize(self, obj, offset_itemsize):
        typeid = self.get_type_id(obj)
        assert self.is_varsize(typeid)
        ofs = self.fixed_size(typeid)
        isz = self.varsize_item_sizes(typeid)
        offset_itemsize[0] = rffi.cast(lltype.Unsigned, ofs)
        offset_itemsize[1] = rffi.cast(lltype.Unsigned, isz)

    def setup(self):
        # Hack: MovingGCBase.setup() sets up stuff related to id(), which
        # we implement differently anyway.  So directly call GCBase.setup().
        GCBase.setup(self)

    def enumerate_pending_finalizers(self, callback, arg):
        raise NotImplementedError

    def copy_pending_finalizers(self, copy_fn):
        raise NotImplementedError

    def _copy_pending_finalizers_deque(self, deque, copy_fn):
        raise NotImplementedError

    def execute_finalizers(self):
        raise NotImplementedError

    def mark_finalizers_to_run(self, fq_index, obj):
        raise NotImplementedError

    def init_gc_object_immortal(self, addr, typeid16, flags=0):
        assert flags == 0
        assert isinstance(typeid16, llgroup.GroupMemberOffset)
        ptr = self.gcheaderbuilder.object_from_header(addr.ptr)
        prebuilt_hash = lltype.identityhash_nocache(ptr)
        assert prebuilt_hash != 0     # xxx probably good enough
        #
        hdr = llmemory.cast_adr_to_ptr(addr, lltype.Ptr(self.HDR))
        hdr._obj._name = typeid16.index   # debug only
        hdr._obj.typeid16 = typeid16
        hdr._obj.prebuilt_hash = prebuilt_hash

    def malloc_fixedsize(self, typeid16, size,
                               needs_finalizer=False,
                               is_finalizer_light=False,
                               contains_weakptr=False):
        rawsize = raw_malloc_usage(size) # unwrap for tests
        if rawsize < 16:
            rawsize = 16     # minimum size (test usually constant-folded)
        if contains_weakptr:    # check constant-folded
            return llop.stm_allocate_weakref(llmemory.GCREF, rawsize, typeid16)
        obj = llop.stm_allocate_tid(llmemory.GCREF, rawsize, typeid16)
        if needs_finalizer:
            if is_finalizer_light:
                llop.stm_enable_destructor(lltype.Void, obj)
            else:
                # old-style finalizer: queue_index = -1
                self.register_finalizer(-1, obj)
        return obj

    def malloc_varsize(self, typeid16, length, size, itemsize,
                             offset_to_length):
        # XXX be careful here about overflows
        totalsize = size + itemsize * length
        totalsize = llarena.round_up_for_allocation(totalsize)
        result = llop.stm_allocate_tid(llmemory.GCREF, totalsize, typeid16)
        llop.stm_set_into_obj(lltype.Void, result, offset_to_length, length)
        return result

    def register_finalizer(self, fq_index, gcobj):
        llop.stm_enable_finalizer(lltype.Void, fq_index, gcobj)

    def can_optimize_clean_setarrayitems(self):
        return False

    def write_barrier(self, addr_struct):
        """Should be turned into calls to stm_write() instead"""
        dont_see_me


    def can_move(self, obj):
        """An object that cannot move means the pointer to it will stay valid,
        as long as it is not actually collected."""
        return llop.stm_can_move(lltype.Bool, obj)


    @classmethod
    def JIT_max_size_of_young_obj(cls):
        return cls.stm_fast_alloc

    @classmethod
    def JIT_minimal_size_in_nursery(cls):
        return cls.minimal_size_in_nursery

    def collect(self, gen=1):
        """Do a minor (gen=0) or major (gen>0) collection."""
        llop.stm_collect(lltype.Void, gen)

    def writebarrier_before_copy(self, source_addr, dest_addr,
                                 source_start, dest_start, length):
        ll_assert(False, 'XXX')
        return False

    def id(self, gcobj):
        return llop.stm_id(lltype.Signed, gcobj)

    def identityhash(self, gcobj):
        return llop.stm_identityhash(lltype.Signed, gcobj)
