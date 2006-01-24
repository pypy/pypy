import struct
from pypy.rpython.memory.simulator import MemorySimulator, MemorySimulatorError
from pypy.rpython.rarithmetic import r_uint
from pypy.rpython.lltypesystem import llmemory
from pypy.rpython.lltypesystem import lltype

class address(object):
    #XXX should be _address!
    
    def __new__(cls, intaddress=0):
        if intaddress == 0:
            null = cls.__dict__.get("NULL")
            if null is not None:
                return null
            cls.NULL = object.__new__(cls)
            return cls.NULL
        else:
            return object.__new__(cls)

    def __init__(self, intaddress=0):
        self.intaddress = intaddress

    def _getintattr(self): #needed to make _accessor easy
        return self.intaddress

    def __add__(self, offset):
        from pypy.rpython.memory.lltypelayout import convert_offset_to_int
        if isinstance(offset, int):
            return address(self.intaddress + offset)
        else:
            assert isinstance(offset, llmemory.AddressOffset)
            return address(self.intaddress + convert_offset_to_int(offset))

    def __sub__(self, other):
        if isinstance(other, int):
            return address(self.intaddress - other)
        else:
            assert isinstance(other, address)
            return self.intaddress - other.intaddress

    def __cmp__(self, other):
        return cmp(self.intaddress, other.intaddress)

    def __repr__(self):
        return "<addr: %s>" % self.intaddress

    def _load(self, fmt):
        return simulator.getstruct(fmt, self.intaddress)

    def _store(self, fmt, *values):
        # XXX annoyance: suddenly an OffsetOf changes into a Signed?!
        from pypy.rpython.memory.lltypelayout import convert_offset_to_int
        if len(values) == 1 and isinstance(values[0], llmemory.AddressOffset):
            values = [convert_offset_to_int(values[0])]
        simulator.setstruct(fmt, self.intaddress, *values)

    def __nonzero__(self):
        return self.intaddress != 0
    

class _accessor(object):
    def __init__(self, addr):
        if addr == NULL:
            raise MemorySimulatorError("trying to access NULL pointer")
        self.intaddress = addr.intaddress
    def __getitem__(self, offset):
        result = simulator.getstruct(self.format,
                                     self.intaddress + offset * self.size)
        return self.convert_from(result[0])

    def __setitem__(self, offset, value):
        simulator.setstruct(self.format, self.intaddress + offset * self.size,
                            self.convert_to(value))


class _signed_accessor(_accessor):
    format = "l"
    size = struct.calcsize("l")
    convert_from = int

    def convert_to(self, offset):
        from pypy.rpython.memory.lltypelayout import convert_offset_to_int
        # XXX same annoyance as in _store
        if isinstance(offset, llmemory.AddressOffset):
            return convert_offset_to_int(offset)
        return int(offset)

class _unsigned_accessor(_accessor):
    format = "L"
    size = struct.calcsize("L")
    convert_from = r_uint
    convert_to = long

class _char_accessor(_accessor):
    format = "c"
    size = struct.calcsize("c")
    convert_from = str
    convert_to = str

class _address_accessor(_accessor):
    format = "P"
    size = struct.calcsize("P")
    convert_from = address
    convert_to = address._getintattr


address.signed = property(_signed_accessor)
address.unsigned = property(_unsigned_accessor)
address.char = property(_char_accessor)
address.address = property(_address_accessor)

NULL = address()
simulator = MemorySimulator()

def raw_malloc(size):
    return address(simulator.malloc(size))

def raw_free(addr):
    simulator.free(addr.intaddress)

def raw_memcopy(addr1, addr2, size):
    simulator.memcopy(addr1.intaddress, addr2.intaddress, size)

def get_address_of_object(obj):
    return address(simulator.get_address_of_object(obj))

def get_py_object(address):
    return simulator.get_py_object(address.intaddress)

address._TYPE = llmemory.Address

supported_access_types = {"signed":    lltype.Signed,
                          "unsigned":  lltype.Unsigned,
                          "char":      lltype.Char,
                          "address":   llmemory.Address,
                          }
