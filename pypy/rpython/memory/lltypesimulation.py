from pypy.rpython.memory import lladdress
from pypy.rpython import lltype

import struct

primitive_to_fmt = {lltype.Signed:   "i",
                    lltype.Unsigned: "I",
                    lltype.Char:     "c",
                    }

def get_layout(TYPE):
    layout = {}
    if isinstance(TYPE, lltype.Primitive):
        return primitive_to_fmt[TYPE]
    if isinstance(TYPE, lltype.Ptr):
        return "P"
    if isinstance(TYPE, lltype.Struct):
        curr = 0
        for name in TYPE._names:
            layout[name] = curr
            curr += get_size(TYPE._flds[name])
        layout["_size"] = curr
        return layout
    else:
        assert 0, "not yet implemented"

def get_size(TYPE):
    if isinstance(TYPE, lltype.Primitive):
        return struct.calcsize(primitive_to_fmt[TYPE])
    elif isinstance(TYPE, lltype.Ptr):
        return struct.calcsize("P")
    elif isinstance(TYPE, lltype.Struct):
        return get_layout(TYPE)["_size"]
    else:
        assert 0, "not yet implemented"
        
# this class is intended to replace the _ptr class in lltype
# using the memory simulator
class SimulatorPtr(object):
    def __init__(self, TYPE, address):
        self.__dict__['_TYPE'] = TYPE
        self.__dict__['_T'] = TYPE.TO
        self.__dict__['_address'] = address
        self.__dict__['_layout'] = get_layout(TYPE.TO)
        self._zero_initialize()

    def _zero_initialize(self):
        size = get_size(self._T)
        self._address._store("c" * size, *(["\x00"] * size))

    def __getattr__(self, field_name):
        if isinstance(self._T, lltype.Struct):
            offset = self._layout[field_name]
            if field_name in self._T._flds:
                T = self._T._flds[field_name]
                base = self._layout[field_name]
                if isinstance(T, lltype.Primitive):
                    return (self._address + offset)._load(primitive_to_fmt[T])[0]
                else:
                    assert 0, "not implemented"
        raise AttributeError, ("%r instance has no field %r" % (self._T,
                                                                field_name))

    def __setattr__(self, field_name, value):
        if isinstance(self._T, lltype.Struct):
            if field_name in self._T._flds:
                T = self._T._flds[field_name]
                base = self._layout[field_name]
                if isinstance(T, lltype.Primitive):
                    (self._address + base)._store(primitive_to_fmt[T], value)
                    return
                else:
                    assert 0, "not implemented"
        raise AttributeError, ("%r instance has no field %r" % (self._T,
                                                                field_name))


# for now use the simulators raw_malloc
def malloc(T, n=None, immortal=False):
    size = get_size(T)
    address = lladdress.raw_malloc(size)
    return SimulatorPtr(lltype.Ptr(T), address)
