from pypy.rpython.lltypesystem import lltype, llmemory, lloperation
from pypy.rpython.annlowlevel import cast_base_ptr_to_instance
from pypy.rpython.annlowlevel import cast_instance_to_base_ptr
from pypy.rlib.unroll import unrolling_iterable

debug_print = lloperation.llop.debug_print

def define_touch_update(TOPPTR, fielddescs, access_touched):
    fielddescs = unrolling_iterable(fielddescs)

    def touch_update(strucref):
        struc = lltype.cast_opaque_ptr(TOPPTR, strucref)
        vable_rti = struc.vable_rti
        vable_rti = cast_base_ptr_to_instance(VirtualizableRTI, vable_rti)
        vable_rti.touch(struc.vable_base)
        
        j = 0
        for fielddesc, _ in fielddescs:
            if fielddesc.canbevirtual and fielddesc.gcref:
                if vable_rti.is_field_virtual(j):
                    continue
            v = vable_rti.read_field(fielddesc, struc.vable_base, j)
            tgt = lltype.cast_pointer(fielddesc.PTRTYPE, struc)            
            setattr(tgt, fielddesc.fieldname, v)
            j += 1
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
            if vable_rti.is_field_virtual(j):
                # this will force
                s = vable_rti.read_field(fielddesc, struc.vable_base, j)
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


class VirtualRTI(object):
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
        assert isinstance(T, lltype.Ptr)
        assert fielddesc.canbevirtual
        assert fielddesc.gcref
        return vrti._get_forced(vablerti, fielddesc, base)
    _read_field._annspecialcase_ = "specialize:arg(2)"

    def _is_virtual(self, forcestate):
        return self.bitmask not in forcestate

    def _get_forced(self, vablerti, fielddesc, base):
        T = fielddesc.RESTYPE
        assert isinstance(T, lltype.Ptr)
        forcestate = vablerti.getforcestate(base).forced
        bitmask = self.bitmask
        if bitmask in forcestate:
            s = forcestate[bitmask] 
            return lltype.cast_opaque_ptr(T, s)
        S = T.TO
        s = lltype.malloc(S)
        sref = lltype.cast_opaque_ptr(llmemory.GCREF, s)
        forcestate[bitmask] = sref
        fielddesc.fill_into(vablerti, s, base, self)
        return s
    _get_forced._annspecialcase_ = "specialize:arg(2)"

class VirtualizableRTI(VirtualRTI):
    _attrs_ = "frameinfo vable_getset_rtis touch_update".split()
            
    def get_global_shape(self):
        return 0

    def is_field_virtual(self, index):
        frameindex = self.varindexes[index]
        if frameindex >= 0:
            return False
        index = -frameindex-1
        assert index >= 0
        return self._is_field_virtual(index)

    def _is_field_virtual(self, index):
       return True

    def read_frame_var(self, T, base, frameindex):
        return self.rgenop.read_frame_var(T, base, self.frameinfo, frameindex)
    read_frame_var._annspecialcase_ = "specialize:arg(1)"

    def read_field(self, fielddesc, base, index):
        return self._read_field(self, fielddesc, base, index)
    read_field._annspecialcase_ = "specialize:arg(1)"

    def getforcestate(self, base):
        state = State()
        for i, get, set in self.vable_getset_rtis:
            p = get(base, self.frameinfo, i)
            vablerti = cast_base_ptr_to_instance(VirtualizableRTI, p)
            # xxx see below
            wforcestate = WithForcedStateVirtualizableRTI(vablerti, state) 
            p = cast_instance_to_base_ptr(wforcestate)
            set(base, self.frameinfo, i, p)
        return state

    def touch(self, base):
        touched = self.getforcestate(base).touched
        touched[self.bitmask] = None

    def touched_ptr_field(self, base, index):
        frameindex = self.varindexes[index]
        if frameindex >= 0:
            return
        posshift = -frameindex
        assert posshift > 0
        touched = self.getforcestate(base).touched
        touched[self.bitmask<<posshift] = None


class State(object):
    forced = {}
    touched = {}

class WithForcedStateVirtualizableRTI(VirtualizableRTI):
    _attrs_ = "state"
    state = None
    
    def __init__(self, vablerti, state):
        self.rgenop = vablerti.rgenop
        self.varindexes = vablerti.varindexes
        self.vrtis = vablerti.vrtis # xxx what if these contain virtualizables 
        self.frameinfo = vablerti.frameinfo
        self.bitmask = vablerti.bitmask
        self.state = state

    def _is_field_virtual(self, index):
       vinfo = self.vrtis[index]
       return vinfo._is_virtual(self.state.forced)

    def getforcestate(self, base):
        return self.state

    def get_global_shape(self):
        assert self.state
        bitmask = 0
        for bitkey in self.state.forced:
            bitmask |= bitkey
        for bitkey in self.state.touched:
            bitmask |= bitkey  
        return bitmask

    def read_forced(self, bitkey):
        assert self.state
        assert self.state.forced
        return self.state.forced[bitkey]


class VirtualStructRTI(VirtualRTI):
    pass
