from pypy.rpython.lltypesystem import lltype, llmemory, lloperation
from pypy.rpython.annlowlevel import cachedtype
from pypy.rpython.annlowlevel import cast_base_ptr_to_instance
from pypy.rpython.annlowlevel import cast_instance_to_base_ptr
from pypy.rlib.unroll import unrolling_iterable

debug_print = lloperation.llop.debug_print
debug_pdb = lloperation.llop.debug_pdb

def define_touch_update(TOPPTR, redirected_fielddescs, access_touched):
    redirected_fielddescs = unrolling_iterable(redirected_fielddescs)

    def touch_update(strucref):
        struc = lltype.cast_opaque_ptr(TOPPTR, strucref)
        vable_rti = struc.vable_rti
        vable_rti = cast_base_ptr_to_instance(VirtualizableRTI, vable_rti)
        vable_rti.touch(struc.vable_base)
        vable_base = struc.vable_base

        j = -1
        for fielddesc, _ in redirected_fielddescs:
            j += 1
            if fielddesc.canbevirtual and fielddesc.gcref:
                if vable_rti.is_field_virtual(vable_base, j):
                    continue
            v = vable_rti.read_field(fielddesc, vable_base, j)
            tgt = lltype.cast_pointer(fielddesc.PTRTYPE, struc)            
            setattr(tgt, fielddesc.fieldname, v)
        ACCESSPTR = TOPPTR.TO.vable_access
        struc.vable_access = lltype.cast_pointer(ACCESSPTR, access_touched)

    return touch_update

def define_getset_field_ptrs(fielddesc, j):

    def set_field_touched(struc, value):
        T = fielddesc.RESTYPE
        if fielddesc.canbevirtual and fielddesc.gcref:
            vable_rti = struc.vable_rti
            vable_rti = cast_base_ptr_to_instance(VirtualizableRTI, vable_rti)
            vable_rti.touched_ptr_field(struc.vable_base, j)
        struc = lltype.cast_pointer(fielddesc.PTRTYPE, struc)
        setattr(struc, fielddesc.fieldname, value)

    def get_field_touched(struc):
        T = fielddesc.RESTYPE
        tgt = lltype.cast_pointer(fielddesc.PTRTYPE, struc)
        if fielddesc.canbevirtual and fielddesc.gcref:
            vable_rti = struc.vable_rti
            vable_rti = cast_base_ptr_to_instance(VirtualizableRTI, vable_rti)
            vable_base = struc.vable_base
            if vable_rti.is_field_virtual(vable_base, j):
                # this will force
                s = vable_rti.read_field(fielddesc, vable_base, j)
                setattr(tgt, fielddesc.fieldname, s)
                return s
        return getattr(tgt, fielddesc.fieldname)
        
    def set_field_untouched(struc, value):
        vable_rti = struc.vable_rti
        vable_rti = cast_base_ptr_to_instance(VirtualizableRTI, vable_rti)
        vable_rti.touch_update(lltype.cast_opaque_ptr(llmemory.GCREF, struc))
        set_field_touched(struc, value)

    def get_field_untouched(struc):
        vable_rti = struc.vable_rti
        vable_rti = cast_base_ptr_to_instance(VirtualizableRTI, vable_rti)
        return vable_rti.read_field(fielddesc, struc.vable_base, j)
        
    return ((get_field_untouched, set_field_untouched),
            (get_field_touched,   set_field_touched))


class RTI(object):
    _attrs_ = 'rgenop varindexes vrtis bitmask'.split()
    
    def __init__(self, rgenop, bitmask):
        self.rgenop = rgenop
        self.varindexes = []
        self.vrtis = []
        self.bitmask = bitmask

    def _read_field(self, vablerti, fielddesc, base, index):
        T = fielddesc.RESTYPE
        frameindex = self.varindexes[index]
        if frameindex >= 0:
            return vablerti.read_frame_var(T, base, frameindex)
        index = -frameindex-1
        assert index >= 0
        vrti = self.vrtis[index]
        assert fielddesc.canbevirtual
        assert fielddesc.gcref
        assert isinstance(vrti, VirtualRTI)
        return vrti._get_forced(vablerti, fielddesc, base)
    _read_field._annspecialcase_ = "specialize:arg(2)"


class VirtualizableRTI(RTI):
    _attrs_ = "frameinfo touch_update shape_place".split()

    def is_field_virtual(self, base, index):
        frameindex = self.varindexes[index]
        if frameindex >= 0:
            return False
        index = -frameindex-1
        assert index >= 0
        vrti = self.vrtis[index]
        assert isinstance(vrti, VirtualRTI)
        return vrti._is_virtual(self.get_shape(base))       

    def read_frame_var(self, T, base, frameindex):
        return self.rgenop.read_frame_var(T, base, self.frameinfo, frameindex)
    read_frame_var._annspecialcase_ = "specialize:arg(1)"

    def read_field(self, fielddesc, base, index):
        return self._read_field(self, fielddesc, base, index)
    read_field._annspecialcase_ = "specialize:arg(1)"

    def touch(self, base):
        self.set_shape_bits(base, self.bitmask)

    def touched_ptr_field(self, base, index):
        frameindex = self.varindexes[index]
        if frameindex >= 0:
            return
        posshift = -frameindex
        assert posshift > 0
        self.set_shape_bits(base, self.bitmask << posshift)

    def get_shape(self, base):
        return self.rgenop.read_frame_place(lltype.Signed, base,
                                            self.shape_place)

    def set_shape(self, base, shapemask):
        return self.rgenop.write_frame_place(lltype.Signed, base,
                                            self.shape_place, shapemask)

    def set_shape_bits(self, base, bitmask):
        self.set_shape(base, bitmask | self.get_shape(base))


class VirtualRTI(RTI):
    _attrs_ = "forced_place devirtualize".split()

    def _get_forced(self, vablerti, elemdesc, base):
        T = elemdesc.RESTYPE
        assert isinstance(T, lltype.Ptr)
        shapemask = vablerti.get_shape(base)
        bitmask = self.bitmask
        if bitmask & shapemask:
            return self.rgenop.read_frame_place(T, base, self.forced_place)
        make, fill_into = self.devirtualize
        cref = make(self)
        c = lltype.cast_opaque_ptr(T, cref)        
        self.rgenop.write_frame_place(T, base, self.forced_place, c)
        vablerti.set_shape(base, shapemask| bitmask)
        fill_into(vablerti, cref, base, self)
        return c
    _get_forced._annspecialcase_ = "specialize:arg(2)"

    def _is_virtual(self, shapemask):
        return bool(self.bitmask & shapemask)


