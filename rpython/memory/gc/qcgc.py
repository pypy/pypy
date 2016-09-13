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
    malloc_zero_filled = False
    prebuilt_gc_objects_are_static_roots = True # XXX: ?
    can_usually_pin_objects = False
    object_minimal_size = 0
    gcflag_extra = 0   # or a real GC flag that is always 0 when not collecting

    typeid_is_in_field = 'tid'

    TRANSLATION_PARAMS = {}
    HDR = lltype.Struct(
            'header',
            ('hdr', rffi.COpaque('object_t', hints={"is_qcgc_header": True})),
            ('tid', lltype.Signed),
            ('hash', lltype.Signed))

    def init_gc_object(self, addr, typeid):
        hdr = llmemory.cast_adr_to_ptr(addr, lltype.Ptr(self.HDR))
        hdr.tid = llop.combine_ushort(lltype.Signed, typeid, 0)
        hdr.hash = rffi.cast(lltype.Signed, 0)

    def malloc_fixedsize(self, typeid, size,
                               needs_finalizer=False,
                               is_finalizer_light=False,
                               contains_weakptr=False):
        #ll_assert(not needs_finalizer, 'finalizer not supported')
        #ll_assert(not is_finalizer_light, 'light finalizer not supported')
        #ll_assert(not contains_weakptr, 'weakref not supported')
        obj = llop.qcgc_allocate(llmemory.Address, size)
        self.init_gc_object(obj, typeid)
        return llmemory.cast_adr_to_ptr(obj, llmemory.GCREF)

    def malloc_varsize(self, typeid, length, size, itemsize, offset_to_length):
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

    def init_gc_object_immortal(self, addr, typeid, flags=0):
        assert flags == 0
        #
        self.init_gc_object(addr, typeid)

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

    def write_barrier(self, addr_struct):
        llop.qcgc_write_barrier(lltype.Void, addr_struct)

    def register_finalizer(self, fq_index, gcobj):
        # XXX: Not supported
        pass

    def id_or_identityhash(self, gcobj, is_hash):
        obj = llmemory.cast_ptr_to_adr(gcobj)
        hdr = self.header(obj)
        i = hdr.hash
        #
        if i == 0:
            i = llmemory.cast_adr_to_int(obj)
            if is_hash:
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
