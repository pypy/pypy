from rpython.memory.gc.base import GCBase
from rpython.memory.support import mangle_hash
from rpython.rtyper.lltypesystem import rffi, lltype, llgroup, llmemory, llarena
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rlib.debug import ll_assert
from rpython.rlib.rarithmetic import ovfcheck

QCGC_HAS_HASH = 0x100 # Upper half of flags for clients, lower half is reserved
QCGC_PREBUILT_OBJECT = 0x2 # XXX: exploits knowledge about qcgc library

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
    withhash_flag_is_in_field = 'flags', QCGC_HAS_HASH

    TRANSLATION_PARAMS = {}
    HDR = lltype.Struct(
            'pypyhdr_t',
            #('hdr', rffi.COpaque('object_t', hints={"is_qcgc_header": True})),
            ('flags', lltype.Signed),   # XXX: exploits knowledge about object_t
            ('tid', lltype.Signed),
            ('hash', lltype.Signed))
    #HDR = rffi.COpaque('object_t')

    def init_gc_object(self, addr, typeid, flags=0):
        hdr = llmemory.cast_adr_to_ptr(addr, lltype.Ptr(self.HDR))
        hdr.flags = rffi.cast(lltype.Signed, flags)
        hdr.tid = rffi.cast(lltype.Signed, typeid)
        hdr.hash = rffi.cast(lltype.Signed, addr)

    def malloc_fixedsize_clear(self, typeid, size,
                               needs_finalizer=False,
                               is_finalizer_light=False,
                               contains_weakptr=False):
        #ll_assert(not needs_finalizer, 'finalizer not supported')
        #ll_assert(not is_finalizer_light, 'light finalizer not supported')
        #ll_assert(not contains_weakptr, 'weakref not supported')
        obj = llop.qcgc_allocate(llmemory.Address, size)
        self.init_gc_object(obj, typeid)
        return llmemory.cast_adr_to_ptr(obj, llmemory.GCREF)

    def malloc_varsize_clear(self, typeid, length, size, itemsize,
                             offset_to_length):
        if length < 0:
            raise MemoryError
        #
        try:
            varsize = ovfcheck(itemsize * length)
            totalsize = ovfcheck(size + varsize)
        except OverflowError:
            raise MemoryError
        #
        obj = llop.qcgc_allocate(llmemory.Address, totalsize)
        self.init_gc_object(obj, typeid)
        (obj + offset_to_length).signed[0] = length
        return llmemory.cast_adr_to_ptr(obj, llmemory.GCREF)

    def init_gc_object_immortal(self, addr, typeid, flags=0): # XXX: Prebuilt Objects?
        assert flags == 0
        ptr = self.gcheaderbuilder.object_from_header(addr.ptr)
        prebuilt_hash = lltype.identityhash_nocache(ptr)
        assert prebuilt_hash != 0
        flags |= QCGC_PREBUILT_OBJECT
        #
        self.init_gc_object(addr, typeid.index, flags)
        llmemory.cast_adr_to_ptr(addr, lltype.Ptr(self.HDR)).hash = prebuilt_hash

    def collect(self, gen=1):
        """Do a minor (gen=0) or major (gen>0) collection."""
        # XXX: Minor collection not supported
        llop.qcgc_collect(lltype.Void)

    def writebarrier_before_copy(self, source_addr, dest_addr,
                                 source_start, dest_start, length):
        # XXX: Seems like returning false is the most conservative way to handle
        # this. Unfortunately I don't fully understand what this is supposed to
        # do, so I can't optimize it ATM.
        return False
        # Possible implementation?
        #llop.gc_writebarrier(dest_addr)
        #return True

    def id_or_identityhash(self, gcobj, is_hash):
        hdr = self.header(llmemory.cast_ptr_to_adr(gcobj))
        has_hash = (hdr.flags & QCGC_HAS_HASH)
        i = hdr.hash
        #
        if is_hash:
            if has_hash:
                return i # Do not mangle for objects with built in hash
            i = mangle_hash(i)
        return i

    def id(self, gcobje):
        return self.id_or_identityhash(gcobj, False)

    def identityhash(self, gcobj):
        return self.id_or_identityhash(gcobj, True)

    def register_finalizer(self, fq_index, gcobj):
        raise NotImplementedError

    def get_type_id(self, obj):
        return self.header(obj).tid
