from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.annlowlevel import cast_base_ptr_to_instance
from pypy.rpython.annlowlevel import cast_instance_to_base_ptr

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
        vinfo = self.vrtis[index]
        assert isinstance(T, lltype.Ptr)
        assert fielddesc.canbevirtual
        return vinfo.get_forced(vablerti, fielddesc, base)
    _read_field._annspecialcase_ = "specialize:arg(2)"

    def _write_field(self, vablerti, fielddesc, base, index, value):
        T = fielddesc.RESTYPE
        frameindex = self.varindexes[index]
        if frameindex >= 0:
            return vablerti.write_frame_var(T, base, frameindex, value)
        raise NotImplementedError
    _write_field._annspecialcase_ = "specialize:arg(2)"

    def get_forced(self, vablerti, fielddesc, base):
        T = fielddesc.RESTYPE
        assert isinstance(T, lltype.Ptr)
        forcestate = vablerti.getforcestate(base)
        bitmask = self.bitmask
        if bitmask in forcestate:
            s = forcestate[bitmask] 
            return lltype.cast_opaque_ptr(T, s)
        S = T.TO
        s = lltype.malloc(S)
        forcestate[bitmask] = lltype.cast_opaque_ptr(llmemory.GCREF, s)
        fielddesc.fill_into(vablerti, s, base, self)
        return s
    get_forced._annspecialcase_ = "specialize:arg(2)"

class VirtualizableRTI(VirtualRTI):
    _attrs_ = "frameinfo vable_getset_rtis".split()
            
    def get_global_shape(self):
        return 0

    def read_frame_var(self, T, base, frameindex):
        return self.rgenop.read_frame_var(T, base, self.frameinfo, frameindex)
    read_frame_var._annspecialcase_ = "specialize:arg(1)"

    def read_field(self, fielddesc, base, index):
        return self._read_field(self, fielddesc, base, index)
    read_field._annspecialcase_ = "specialize:arg(1)"

    def write_frame_var(self, T, base, frameindex, value):
        return self.rgenop.write_frame_var(T, base, self.frameinfo, frameindex,
                                           value)
    write_frame_var._annspecialcase_ = "specialize:arg(1)"

    def write_field(self, fielddesc, base, index, value):
        return self._write_field(self, fielddesc, base, index, value)
    write_field._annspecialcase_ = "specialize:arg(1)"

    def getforcestate(self, base):
        state = {}
        for i, get, set in self.vable_getset_rtis:
            p = get(base, self.frameinfo, i)
            vablerti = cast_base_ptr_to_instance(VirtualizableRTI, p)
            # xxx see below
            wforcestate = WithForcedStateVirtualizableRTI(vablerti, state) 
            p = cast_instance_to_base_ptr(wforcestate)
            set(base, self.frameinfo, i, p)
        return state

class WithForcedStateVirtualizableRTI(VirtualizableRTI):
    _attrs_ = "state"
    state = {}
    
    def __init__(self, vablerti, state):
        self.rgenop = vablerti.rgenop
        self.varindexes = vablerti.varindexes
        self.vrtis = vablerti.vrtis # xxx what if these contain virtualizables 
        self.frameinfo = vablerti.frameinfo
        self.bitmask = vablerti.bitmask
        self.state = state
        
    def getforcestate(self, base):
        return self.state

    def get_global_shape(self):
        bitmask = 0
        for bitkey in self.state:
            bitmask |= bitkey
        return bitmask

    def read_forced(self, bitkey):
        assert self.state
        return self.state[bitkey]


class VirtualStructRTI(VirtualRTI):
    pass
