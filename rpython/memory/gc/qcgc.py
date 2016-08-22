from rpython.memory.gc.base import GCBase
from rpython.rtyper.lltypesystem import rffi, lltype, llgroup, llmemory, llarena
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rlib.debug import ll_assert

class QCGC(GCBase):
    _alloc_flavor_ = "raw"
    moving_gc = False
    needs_write_barrier = True
    malloc_zero_filled = True
    prebuilt_gc_objects_are_static_roots = True # XXX: ?
    can_usually_pin_objects = False
    object_minimal_size = 0
    gcflag_extra = 0   # or a real GC flag that is always 0 when not collecting

    typeid_is_in_field = 'tid'
    withhash_flag_is_in_field = 'hash', 0

    TRANSLATION_PARAMS = {}
    HDR = lltype.Struct(
            'pypyhdr_t',
            ('hdr', rffi.COpaque('object_t', hints={"is_qcgc_header": True})),
            ('tid', lltype.Signed),
            ('hash', lltype.Signed))
    #HDR = rffi.COpaque('object_t')

    def malloc_fixedsize_clear(self, typeid, size,
                               needs_finalizer=False,
                               is_finalizer_light=False,
                               contains_weakptr=False):
        # XXX: What is the llmemory.GCREF for? (Assumption: return value)
        ll_assert(not needs_finalizer, 'finalizer not supported')
        ll_assert(not is_finalizer_light, 'light finalizer not supported')
        ll_assert(not contains_weakptr, 'weakref not supported')
        # FIXME: set typeid and hash here
        return llop.qcgc_allocate(llmemory.GCREF, size, typeid)

    def malloc_varsize_clear(self, typeid16, length, size, itemsize,
                             offset_to_length):
        totalsize = size + itemsize * length
        #totalsize = llarena.round_up_for_allocation(totalsize)
        obj = llop.qcgc_allocate(llmemory.Address, totalsize, typeid16)
        (obj + offset_to_length).signed[0] = length
        return llmemory.cast_adr_to_ptr(obj, llmemory.GCREF)

    def collect(self, gen=1):
        """Do a minor (gen=0) or major (gen>0) collection."""
        # XXX: Minor collection not supported
        llop.qcgc_collect(lltype.Void)

    def writebarrier_before_copy(self, source_addr, dest_addr,
                                 source_start, dest_start, length):
        raise NotImplementedError
        # Possible implementation?
        #llop.gc_writebarrier(dest_addr)
        #return True

    def identityhash(self, gcobj):
        raise NotImplementedError

    def register_finalizer(self, fq_index, gcobj):
        raise NotImplementedError

    def get_type_id(self, obj):
        return self.header(obj).tid

    def init_gc_object(self, addr, typeid, flags=0):
        assert flags == 0
        hdr = llmemory.cast_adr_to_ptr(addr, lltype.Ptr(self.HDR))
        hdr.tid = typeid.index

    def init_gc_object_immortal(self, addr, typeid, flags=0): # XXX: Prebuilt Objects?
        assert flags == 0
        self.init_gc_object(addr, typeid, flags)
        ptr = self.gcheaderbuilder.object_from_header(addr.ptr)
        prebuilt_hash = lltype.identityhash_nocache(ptr)
        assert prebuilt_hash != 0
        #
        hdr = llmemory.cast_adr_to_ptr(addr, lltype.Ptr(self.HDR))
        hdr.hash = prebuilt_hash
        #hdr._obj._name = typeid.index
        #
        # STMGC CODE:
        #assert flags == 0
        #assert isinstance(typeid16, llgroup.GroupMemberOffset)
        #ptr = self.gcheaderbuilder.object_from_header(addr.ptr)
        #prebuilt_hash = lltype.identityhash_nocache(ptr)
        #assert prebuilt_hash != 0     # xxx probably good enough
        ##
        #hdr = llmemory.cast_adr_to_ptr(addr, lltype.Ptr(self.HDR))
        #hdr._obj._name = typeid16.index   # debug only
        #hdr._obj.typeid16 = typeid16
        #hdr._obj.prebuilt_hash = prebuilt_hash
