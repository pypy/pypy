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

WORD = LONG_BIT // 8
NULL = llmemory.NULL
first_gcflag = 1 << (LONG_BIT//2)


class StmGC(MovingGCBase):
    _alloc_flavor_ = "raw"
    inline_simple_malloc = True
    inline_simple_malloc_varsize = True
    needs_write_barrier = True
    prebuilt_gc_objects_are_static_roots = False
    malloc_zero_filled = True
    #gcflag_extra = GCFLAG_EXTRA

    HDR = rffi.COpaque('struct stm_object_s')
    H_TID = 0
    H_REVISION = WORD
    H_ORIGINAL = WORD + WORD
    typeid_is_in_field = None

    VISIT_FPTR = lltype.Ptr(lltype.FuncType([llmemory.Address], lltype.Void))

    minimal_size_in_nursery = llmemory.sizeof(HDR)

    TRANSLATION_PARAMS = {
    }

    # keep in sync with stmgc.h & et.h:
    GCFLAG_OLD                    = first_gcflag << 0
    GCFLAG_VISITED                = first_gcflag << 1
    GCFLAG_PUBLIC                 = first_gcflag << 2
    GCFLAG_PREBUILT_ORIGINAL      = first_gcflag << 3
    GCFLAG_PUBLIC_TO_PRIVATE      = first_gcflag << 4
    GCFLAG_WRITE_BARRIER          = first_gcflag << 5 # stmgc.h
    GCFLAG_MOVED                  = first_gcflag << 6
    GCFLAG_BACKUP_COPY            = first_gcflag << 7 # debug
    GCFLAG_STUB                   = first_gcflag << 8 # debug
    GCFLAG_PRIVATE_FROM_PROTECTED = first_gcflag << 9
    GCFLAG_HAS_ID                 = first_gcflag << 10
    GCFLAG_IMMUTABLE              = first_gcflag << 11
    GCFLAG_SMALLSTUB              = first_gcflag << 12
    GCFLAG_MARKED                 = first_gcflag << 13
    
    PREBUILT_FLAGS    = first_gcflag * ((1<<0) | (1<<1) | (1<<2) | (1<<3) | (1<<13))
    PREBUILT_REVISION = r_uint(1)
    
    FX_MASK = 65535


    def setup(self):
        # Hack: MovingGCBase.setup() sets up stuff related to id(), which
        # we implement differently anyway.  So directly call GCBase.setup().
        GCBase.setup(self)
        #
        llop.stm_initialize(lltype.Void)


    def get_type_id(self, obj):
        return llop.stm_get_tid(llgroup.HALFWORD, obj)

    def get_hdr_tid(self, addr):
        return llmemory.cast_adr_to_ptr(addr + self.H_TID, rffi.SIGNEDP)

    def get_hdr_revision(self, addr):
        return llmemory.cast_adr_to_ptr(addr + self.H_REVISION, rffi.SIGNEDP)

    def get_hdr_original(self, addr):
        return llmemory.cast_adr_to_ptr(addr + self.H_ORIGINAL, rffi.SIGNEDP)

    def get_original_copy(self, obj):
        addr = llmemory.cast_ptr_to_adr(obj)
        if bool(self.get_hdr_tid(addr)[0] & self.GCFLAG_PREBUILT_ORIGINAL):
            return obj
        #
        orig = self.get_hdr_original(addr)[0]
        if orig == 0:
            return obj
        #
        return  llmemory.cast_adr_to_ptr(llmemory.cast_int_to_adr(orig), 
                                         llmemory.GCREF)
        
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

    def malloc_fixedsize_clear(self, typeid16, size,
                               needs_finalizer=False,
                               is_finalizer_light=False,
                               contains_weakptr=False):
        # XXX finalizers are ignored for now
        #ll_assert(not needs_finalizer, 'XXX needs_finalizer')
        #ll_assert(not is_finalizer_light, 'XXX is_finalizer_light')
        ll_assert(not contains_weakptr, 'contains_weakptr: use malloc_weakref')
        # XXX call optimized versions, e.g. if size < GC_NURSERY_SECTION
        return llop.stm_allocate(llmemory.GCREF, size, typeid16)

    def malloc_varsize_clear(self, typeid16, length, size, itemsize,
                             offset_to_length):
        # XXX be careful about overflows, and call optimized versions
        totalsize = size + itemsize * length
        totalsize = llarena.round_up_for_allocation(totalsize)
        obj = llop.stm_allocate(llmemory.Address, totalsize, typeid16)
        (obj + offset_to_length).signed[0] = length
        return llmemory.cast_adr_to_ptr(obj, llmemory.GCREF)

    def malloc_weakref(self, typeid16, size, obj):
        return llop.stm_weakref_allocate(llmemory.GCREF, size,
                                         typeid16, obj)

    def can_move(self, obj):
        """Means the reference will stay valid, except if not
        seen by the GC, then it can get collected."""
        tid = self.get_hdr_tid(obj)[0]
        if bool(tid & self.GCFLAG_OLD):
            return False
        return True
        

    @classmethod
    def JIT_max_size_of_young_obj(cls):
        return None

    @classmethod
    def JIT_minimal_size_in_nursery(cls):
        return cls.minimal_size_in_nursery

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
