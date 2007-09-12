import py
import sys

from pypy.annotation import model as annmodel
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.translator.translator import graphof
from pypy.objspace.flow import FlowObjSpace
from pypy.rpython.rtyper import RPythonTyper
from pypy.rpython.memory.lladdress import _address, NULL
from pypy.rpython.memory.lladdress import raw_malloc, raw_free, raw_memcopy
from pypy.rpython.memory.lladdress import get_py_object, get_address_of_object
from pypy.rpython.lltypesystem.llmemory import Address, NullAddressError
from pypy.rpython.memory.simulator import MemorySimulatorError
from pypy.rpython.memory.test.test_llinterpsim import interpret
from pypy.rpython.lltypesystem import lltype

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

##    -- no longer valid since NULL is not a regular _address any more
##    def test_address_comparison(self):
##        def f(offset):
##            return NULL < NULL + offset
##        a = RPythonAnnotator()
##        s = a.build_types(f, [annmodel.SomeInteger()])
##        assert isinstance(s, annmodel.SomeBool)
##        assert f(1)
##        assert not f(0)
##        assert not f(-1)

    def test_simple_offsetof(self):
        from pypy.rpython.lltypesystem import lltype
        from pypy.rpython.lltypesystem.llmemory import offsetof
        S = lltype.GcStruct('S', ('x', lltype.Bool), ('y', lltype.Signed))
        def f():
            return offsetof(S, 'x')
        f()
        a = RPythonAnnotator()
        s = a.build_types(f, [])
        assert isinstance(s, annmodel.SomeInteger)

        coff = offsetof(S, 'y')
        def f():
            return coff
        f()
        a = RPythonAnnotator()
        s = a.build_types(f, [])
        assert isinstance(s, annmodel.SomeInteger)

    def test_offset_addition(self):
        from pypy.rpython.lltypesystem import lltype
        from pypy.rpython.lltypesystem.llmemory import offsetof
        S = lltype.Struct('S', ('x', lltype.Bool), ('y', lltype.Signed))
        T = lltype.GcStruct('T', ('r', lltype.Float), ('s1', S), ('s2', S))
        def f():
            return offsetof(T, 's1') + offsetof(S, 'x')
        f()
        a = RPythonAnnotator()
        s = a.build_types(f, [])
        assert isinstance(s, annmodel.SomeInteger)

        coff = offsetof(T, 's2') + offsetof(S, 'y')
        def f():
            return coff
        f()
        a = RPythonAnnotator()
        s = a.build_types(f, [])
        assert isinstance(s, annmodel.SomeInteger)
        
       
class TestAddressRTyping(object):
    def test_null(self):
        def f():
            return NULL
        a = RPythonAnnotator()
        s = a.build_types(f, [])
        rtyper = RPythonTyper(a)
        rtyper.specialize()
        rtyp = graphof(a.translator, f).returnblock.inputargs[0].concretetype
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
        graph = graphof(a.translator, f)
        assert graph.startblock.operations[0].result.concretetype == Address


    def test_simple_offsetof(self):
        from pypy.rpython.lltypesystem import lltype
        from pypy.rpython.lltypesystem.llmemory import offsetof
        S = lltype.GcStruct('S', ('x', lltype.Bool), ('y', lltype.Signed))
        def f():
            return offsetof(S, 'x')
        f()
        a = RPythonAnnotator()
        s = a.build_types(f, [])
        rtyper = RPythonTyper(a)
        rtyper.specialize() #does not raise

        coff = offsetof(S, 'y')
        def f():
            return coff
        f()
        a = RPythonAnnotator()
        s = a.build_types(f, [])
        rtyper = RPythonTyper(a)
        rtyper.specialize() #does not raise

    def test_offset_addition(self):
        from pypy.rpython.lltypesystem import lltype
        from pypy.rpython.lltypesystem.llmemory import offsetof
        S = lltype.Struct('S', ('x', lltype.Bool), ('y', lltype.Signed))
        T = lltype.GcStruct('T', ('r', lltype.Float), ('s1', S), ('s2', S))
        def f():
            return offsetof(T, 's1') + offsetof(S, 'x')
        f()
        a = RPythonAnnotator()
        s = a.build_types(f, [])
        rtyper = RPythonTyper(a)
        rtyper.specialize() #does not raise

        coff = offsetof(T, 's2') + offsetof(S, 'y')
        def f():
            return coff
        f()
        a = RPythonAnnotator()
        s = a.build_types(f, [])
        rtyper = RPythonTyper(a)
        rtyper.specialize() #does not raise


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
        res = interpret(f, [_address(1)])
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

    def test_pointer_arithmetic_inplace(self):
        def f(offset, char):
            addr = raw_malloc(10000)
            addr += offset
            addr.char[-offset] = char
            addr -= offset
            return addr.char[0]
        res = interpret(f, [10, "c"])
        assert res == "c"
        res = interpret(f, [12, "x"])
        assert res == "x"

    def test_address_comparison(self):
        def f(addr, offset):
            return addr < addr + offset or addr == addr + offset
        addr = _address(129820)
        res = interpret(f, [addr, 10])
        assert res
        res = interpret(f, [addr, -10])
        assert not res
        res = interpret(f, [addr, 0])
        assert res

    def test_raw_memcopy(self):
        def f():
            addr = raw_malloc(100)
            addr.signed[0] = 12
            (addr + 10).signed[0] = 42
            (addr + 20).char[0] = "a"
            addr1 = raw_malloc(100)
            raw_memcopy(addr, addr1, 100)
            result = addr1.signed[0] == 12
            result = result and (addr1 + 10).signed[0] == 42
            result = result and (addr1 + 20).char[0] == "a"
            return result
        res = interpret(f, [])
        assert res

class TestAddressSimulation(object):
    def test_null_is_singleton(self):
        assert _address() is NULL
        assert _address() is _address(0)

    def test_convert_to_bool(self):
        assert not _address()
        assert not NULL
        assert _address(1)
        assert _address(2)
        assert bool(_address(3))

    def test_memory_access(self):
        addr = raw_malloc(1000)
        addr.signed[0] = -1
        assert addr.unsigned[0] == sys.maxint * 2 + 1
        addr.address[0] = addr
        assert addr.address[0] == addr
        py.test.raises(NullAddressError, "NULL.signed[0]")

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

    def test_add_offsetofs(self):
        from pypy.rpython.lltypesystem.llmemory import offsetof
        S = lltype.GcStruct("struct", ('a', lltype.Signed), ('b', lltype.Signed))
        addr = raw_malloc(100)
        (addr + offsetof(S, 'b')).signed[0] = 42
        assert (addr + offsetof(S, 'b')).signed[0] == 42
        addr.signed[5] = offsetof(S, 'b')
        offset = addr.signed[5]
        assert (addr + offset).signed[0] == 42
