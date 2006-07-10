import struct
from pypy.rpython.memory.simulator import MemorySimulator, MemorySimulatorError
from pypy.rpython.rarithmetic import r_uint
from pypy.rpython.lltypesystem import llmemory
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.memory.lltypelayout import convert_offset_to_int
from pypy.rpython.objectmodel import ComputedIntSymbolic

NULL = llmemory.NULL


class _address(object):

    def __new__(cls, intaddress=0):
        if intaddress == 0:
            return NULL
        else:
            return object.__new__(cls)

    def __init__(self, intaddress=0):
        self.intaddress = intaddress

    def __add__(self, offset):
        if isinstance(offset, int):
            return _address(self.intaddress + offset)
        else:
            assert isinstance(offset, llmemory.AddressOffset)
            return _address(self.intaddress + convert_offset_to_int(offset))

    def __sub__(self, other):
        if isinstance(other, int):
            return _address(self.intaddress - other)
        elif isinstance(other, llmemory.AddressOffset):
            return _address(self.intaddress - convert_offset_to_int(other))
        else:
            assert isinstance(other, _address)
            return self.intaddress - other.intaddress

    def __cmp__(self, other):
        return cmp(self.intaddress, other.intaddress)

    def __repr__(self):
        return "<addr: %s>" % self.intaddress

    def _load(self, fmt):
        return simulator.getstruct(fmt, self.intaddress)

    def _store(self, fmt, *values):
        # XXX annoyance: suddenly a Symbolic changes into a Signed?!
        from pypy.rpython.memory.lltypelayout import convert_offset_to_int
        if len(values) == 1 and isinstance(values[0], llmemory.AddressOffset):
            values = [convert_offset_to_int(values[0])]
        elif len(values) == 1 and isinstance(values[0], ComputedIntSymbolic):
            values = [values[0].compute_fn()]
        simulator.setstruct(fmt, self.intaddress, *values)

    def __nonzero__(self):
        return self.intaddress != 0

    def _cast_to_ptr(self, EXPECTED_TYPE):
        from pypy.rpython.memory.lltypesimulation import simulatorptr
        return simulatorptr(EXPECTED_TYPE, self)

    def _cast_to_int(self):
        return self.intaddress
    

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
    from pypy.tool.uid import HUGEVAL_FMT as format
    from pypy.tool.uid import HUGEVAL_BYTES as size
    convert_from = _address
    convert_to = staticmethod(lambda addr: addr.intaddress)


_address.signed = property(_signed_accessor)
_address.unsigned = property(_unsigned_accessor)
_address.char = property(_char_accessor)
_address.address = property(_address_accessor)

simulator = MemorySimulator()

def raw_malloc(size):
    return _address(simulator.malloc(size))

def raw_malloc_usage(size):
    assert isinstance(size, int)
    return size

def raw_free(addr):
    simulator.free(addr.intaddress)

def raw_memcopy(addr1, addr2, size):
    simulator.memcopy(addr1.intaddress, addr2.intaddress, size)

def get_address_of_object(obj):
    return _address(simulator.get_address_of_object(obj))

def get_py_object(address):
    return simulator.get_py_object(address.intaddress)

_address._TYPE = llmemory.Address

supported_access_types = {"signed":    lltype.Signed,
                          "unsigned":  lltype.Unsigned,
                          "char":      lltype.Char,
                          "address":   llmemory.Address,
                          }
