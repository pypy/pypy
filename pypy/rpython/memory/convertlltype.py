from pypy.rpython.memory import lladdress
from pypy.rpython.memory.lltypesimulation import simulatorptr, get_total_size
from pypy.rpython.memory.lltypesimulation import get_fixed_size
from pypy.rpython.memory.lltypesimulation import get_variable_size
from pypy.rpython.memory.lltypesimulation import primitive_to_fmt
from pypy.rpython.memory.lltypesimulation import get_layout
from pypy.objspace.flow.model import Constant
from pypy.rpython import lltype

class LLTypeConverter(object):
    def __init__(self, address):
        self.converted = {}
        self.curraddress = address

    def convert(self, val_or_ptr, inline_to_addr=None):
        TYPE = lltype.typeOf(val_or_ptr)
        if isinstance(TYPE, lltype.Primitive):
            if inline_to_addr is not None:
                inline_to_addr._store(primitive_to_fmt[TYPE], val_or_ptr)
            return val_or_ptr
        elif isinstance(TYPE, lltype.Array):
            return self.convert_array(val_or_ptr, inline_to_addr)
        elif isinstance(TYPE, lltype.Struct):
            return self.convert_struct(val_or_ptr, inline_to_addr)
        elif isinstance(TYPE, lltype.Ptr):
            return self.convert_pointer(val_or_ptr, inline_to_addr)
        else:
            assert 0, "not yet implemented"

    def convert_array(self, _array, inline_to_addr):
        if _array in self.converted:
            address = self.converted[_array]
            assert inline_to_addr is None or address == inline_to_addr
            return address
        TYPE = lltype.typeOf(_array)
        arraylength = len(_array.items)
        size = get_total_size(TYPE, arraylength)
        if inline_to_addr is not None:
            startaddr = inline_to_addr
        else:
            startaddr = self.curraddress
        self.converted[_array] = startaddr
        startaddr.signed[0] = arraylength
        curraddr = startaddr + get_fixed_size(TYPE)
        varsize = get_variable_size(TYPE)
        self.curraddress += size
        for item in _array.items:
            self.convert(item, curraddr)
            curraddr += varsize
        return startaddr

    def convert_struct(self, _struct, inline_to_addr):
        if _struct in self.converted:
            address = self.converted[_struct]
            assert inline_to_addr is None or address == inline_to_addr
            return address
        TYPE = lltype.typeOf(_struct)
        layout = get_layout(TYPE)
        size = get_total_size(TYPE)
        if inline_to_addr is not None:
            startaddr = inline_to_addr
        else:
            startaddr = self.curraddress
        self.converted[_struct] = startaddr
        self.curraddress += size
        for name in TYPE._flds:
            addr = startaddr + layout[name]
            self.convert(getattr(_struct, name), addr)
        return startaddr

    def convert_pointer(self, _ptr, inline_to_addr):
        TYPE = lltype.typeOf(_ptr)
        addr = self.convert(_ptr._obj)
        assert isinstance(addr, lladdress.Address)
        if inline_to_addr is not None:
            inline_to_addr.address[0] = addr
        return simulatorptr(TYPE, addr)
