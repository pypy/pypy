import py
import sys

from pypy.annotation import model as annmodel
from pypy.translator.annrpython import RPythonAnnotator
from pypy.objspace.flow import FlowObjSpace
from pypy.rpython.rtyper import RPythonTyper
from pypy.rpython.memory.lladdress import address, NULL
from pypy.rpython.memory.lladdress import raw_malloc, raw_free, raw_memcopy
from pypy.rpython.memory.lladdress import get_py_object, get_address_of_object
from pypy.rpython.memory.lladdress import Address
from pypy.rpython.memory.simulator import MemorySimulatorError
from pypy.rpython.memory.test.test_llinterpsim import interpret

class TestAddressAnnotation(object):
    def test_null(self):
        def f():
            return NULL
        a = RPythonAnnotator()
        s = a.build_types(f, [])
        assert isinstance(s, annmodel.SomeAddress)
        assert s.is_null
        assert f() is NULL

    def test_raw_malloc(self):
        def f():
            return raw_malloc(100)
        a = RPythonAnnotator()
        s = a.build_types(f, [])
        assert isinstance(s, annmodel.SomeAddress)
        assert not s.is_null

    def test_raw_free(self):
        def f(addr):
            raw_free(addr)
        a = RPythonAnnotator()
        s = a.build_types(f, [annmodel.SomeAddress()]) #does not raise
        a = RPythonAnnotator()
        py.test.raises(AssertionError,
                       a.build_types, f, [annmodel.SomeAddress(is_null=True)])
        py.test.raises(MemorySimulatorError, f, NULL)

    def test_memcopy(self):
        def f(addr1, addr2):
            raw_memcopy(addr1, addr2, 100)
        a = RPythonAnnotator()
        #does not raise:
        s = a.build_types(f, [annmodel.SomeAddress(), annmodel.SomeAddress()])
        a = RPythonAnnotator()
        py.test.raises(AssertionError, a.build_types, f,
                       [annmodel.SomeAddress(is_null=True),
                        annmodel.SomeAddress()])

    def test_union(self):
        def f(x, y):
            if y:
                addr = NULL
            else:
                if x:
                    addr = NULL
                else:
                    addr = raw_malloc(10)
            return addr
        a = RPythonAnnotator()
        s_true = annmodel.SomeBool()
        s_true.const = True
        s_false = annmodel.SomeBool()
        s_false.const = False
        s = a.build_types(f, [bool, bool])
        assert isinstance(s, annmodel.SomeAddress)
        assert not s.is_null
        a = RPythonAnnotator()
        s = a.build_types(f, [s_true, bool])
        assert isinstance(s, annmodel.SomeAddress)
        assert s.is_null
        assert f(True, False) == NULL
        a = RPythonAnnotator()
        s = a.build_types(f, [s_false, bool])
        assert isinstance(s, annmodel.SomeAddress)
        assert not s.is_null
        
    def test_memory_access(self):
        def f(offset, value):
            addr = raw_malloc(offset * 2 + 1)
            addr.signed[offset] = value
            return addr.signed[offset]
        a = RPythonAnnotator()
        s = a.build_types(f, [annmodel.SomeInteger(), annmodel.SomeInteger()])
        assert isinstance(s, annmodel.SomeInteger)

    def test_address_arithmetic(self):
        def f(offset, char):
            addr = raw_malloc(10000)
            same_offset = (addr + offset) - addr
            addr.char[offset] = char
            return (addr + same_offset).char[0]
        a = RPythonAnnotator()
        s = a.build_types(f, [annmodel.SomeInteger(), annmodel.SomeChar()])
        assert isinstance(s, annmodel.SomeChar)
        assert f(0, "c") == "c"
        assert f(123, "c") == "c"
        

    def test_address_comparison(self):
        def f(offset):
            return NULL < NULL + offset
        a = RPythonAnnotator()
        s = a.build_types(f, [annmodel.SomeInteger()])
        assert isinstance(s, annmodel.SomeBool)
        assert f(1)
        assert not f(0)
        assert not f(-1)


class TestAddressRTyping(object):
    def test_null(self):
        def f():
            return NULL
        a = RPythonAnnotator()
        s = a.build_types(f, [])
        rtyper = RPythonTyper(a)
        rtyper.specialize()
        rtyp = a.translator.flowgraphs[f].returnblock.inputargs[0].concretetype
        assert rtyp == Address

    def test_convert_to_bool(self):
        def f(addr):
            return bool(addr)
        a = RPythonAnnotator()
        s = a.build_types(f, [annmodel.SomeAddress()])
        assert isinstance(s, annmodel.SomeBool)

    def test_raw_malloc(self):
        def f():
            return raw_malloc(100)
        a = RPythonAnnotator()
        s = a.build_types(f, [])
        rtyper = RPythonTyper(a)
        rtyper.specialize() #does not raise

    def test_raw_free(self):
        def f(addr):
            raw_free(addr)
        a = RPythonAnnotator()
        s = a.build_types(f, [annmodel.SomeAddress()])
        rtyper = RPythonTyper(a)
        rtyper.specialize() #does not raise

    def test_memcopy(self):
        def f(addr1, addr2):
            raw_memcopy(addr1, addr2, 100)
        a = RPythonAnnotator()
        #does not raise:
        s = a.build_types(f, [annmodel.SomeAddress(), annmodel.SomeAddress()])
        rtyper = RPythonTyper(a)
        rtyper.specialize() #does not raise

    def test_memory_access(self):
        def f(offset, value):
            addr = raw_malloc(offset * 2 + 1)
            addr.signed[offset] = value
            return addr.signed[offset]
        a = RPythonAnnotator()
        s = a.build_types(f, [annmodel.SomeInteger(), annmodel.SomeInteger()])
        rtyper = RPythonTyper(a)
        rtyper.specialize() #does not raise

    def test_addr_as_bool(self):
        def f(addr1, addr2):
            if addr1:
                return 1
            else:
                if not addr2:
                    return 0
                else:
                    return -1
        a = RPythonAnnotator()
        #does not raise:
        s = a.build_types(f, [annmodel.SomeAddress(), annmodel.SomeAddress()])
        rtyper = RPythonTyper(a)
        rtyper.specialize() #does not raise

    def test_address_arithmetic(self):
        def f(offset, char):
            addr = raw_malloc(10000)
            same_offset = (addr + offset) - addr
            addr.char[offset] = char
            return (addr + same_offset).char[0]
        a = RPythonAnnotator()
        s = a.build_types(f, [annmodel.SomeInteger(), annmodel.SomeChar()])
        rtyper = RPythonTyper(a)
        rtyper.specialize() #does not raise

    def test_address_comparison(self):
        def f(offset):
            return NULL < NULL + offset
        a = RPythonAnnotator()
        s = a.build_types(f, [annmodel.SomeInteger()])
        rtyper = RPythonTyper(a)
        rtyper.specialize() #does not raise
        graph = a.translator.flowgraphs[f] 
        assert graph.startblock.operations[0].result.concretetype == Address

class TestAddressInLLInterp(object):
    def test_null(self):
        def f():
            return NULL
        assert interpret(f, []) is NULL

    def test_convert_to_bool(self):
        def f(addr):
            return bool(addr)
        res = interpret(f, [NULL])
        assert isinstance(res, bool) and not res
        res = interpret(f, [address(1)])
        assert isinstance(res, bool) and res

    def test_memory_access(self):
        def f(value):
            addr = raw_malloc(16)
            addr.signed[0] = value
            return addr.signed[0]
        res = interpret(f, [42])
        assert res == 42
        res = interpret(f, [1])
        assert res == 1
        
    def test_pointer_arithmetic(self):
        def f(offset, char):
            addr = raw_malloc(10000)
            same_offset = (addr + 2 * offset - offset) - addr 
            addr.char[offset] = char
            result = (addr + same_offset).char[0]
            raw_free(addr)
            return result
        res = interpret(f, [10, "c"])
        assert res == "c"
        res = interpret(f, [12, "x"])
        assert res == "x"

    def test_address_comparison(self):
        def f(offset):
            return NULL < NULL + offset or NULL == NULL + offset
        res = interpret(f, [10])
        assert res
        res = interpret(f, [-10])
        assert not res
        res = interpret(f, [0])
        assert res


class TestAddressSimulation(object):
    def test_null_is_singleton(self):
        assert address() is NULL
        assert address() is address(0)

    def test_convert_to_bool(self):
        assert not address()
        assert not NULL
        assert address(1)
        assert address(2)
        assert bool(address(3))

    def test_memory_access(self):
        addr = raw_malloc(1000)
        addr.signed[0] = -1
        assert addr.unsigned[0] == sys.maxint * 2 + 1
        addr.address[0] = addr
        assert addr.address[0] == addr
        py.test.raises(MemorySimulatorError, "NULL.signed[0]")

    def test_pointer_arithmetic(self):
        addr = raw_malloc(100)
        assert addr + 10 - 10 == addr
        addr.char[10] = "c"
        assert (addr + 10).char[0] == "c"

    def test_pyobjects(self):
        def f(x):
            return x + 1
        def g(x):
            return x - 1
        addr = raw_malloc(100)
        addr.address[0] = get_address_of_object(f)
        addr.address[1] = get_address_of_object(g)
        assert get_py_object(addr.address[0]) == f
        assert get_py_object(addr.address[1]) == g
        assert get_py_object(addr.address[0])(1) == 2
        assert get_py_object(addr.address[1])(0) == -1

    def test_memcopy(self):
        def f(x):
            return x + 1
        addr = raw_malloc(100)
        addr.address[0] = get_address_of_object(f)
        (addr + 10).signed[0] = 42
        (addr + 20).char[0] = "a"
        addr1 = raw_malloc(100)
        raw_memcopy(addr, addr1, 100)
        assert get_py_object(addr1.address[0])(0) == 1
        assert (addr1 + 10).signed[0] == 42
        assert (addr1 + 20).char[0] == "a"
