import py

from pypy.annotation import model as annmodel
from pypy.translator.annrpython import RPythonAnnotator
from pypy.objspace.flow import FlowObjSpace
from pypy.rpython.memory.lladdress import raw_malloc, raw_free, NULL, raw_memcopy

class TestAddressAnnotation(object):
    def test_raw_malloc(self):
        def f():
            return raw_malloc(100)
        a = RPythonAnnotator()
        s = a.build_types(f, [])
        assert isinstance(s, annmodel.SomeAddress)
        assert not s.is_null

    def test_null(self):
        def f():
            return NULL
        a = RPythonAnnotator()
        s = a.build_types(f, [])
        assert isinstance(s, annmodel.SomeAddress)
        assert s.is_null

    def test_raw_free(self):
        def f(addr):
            raw_free(addr)
        a = RPythonAnnotator()
        s = a.build_types(f, [annmodel.SomeAddress()]) #does not raise
        a = RPythonAnnotator()
        py.test.raises(AssertionError,
                       a.build_types, f, [annmodel.SomeAddress(is_null=True)])

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
            addr = raw_malloc(offset * 2 + 1)
            same_offset = (addr + offset) - addr
            addr.char[offset] = char
            return (addr + same_offset).char[0]
        a = RPythonAnnotator()
        s = a.build_types(f, [annmodel.SomeInteger(), annmodel.SomeChar()])
        assert isinstance(s, annmodel.SomeChar)

    def test_address_comparison(self):
        def f(offset):
            return NULL < NULL + offset
        a = RPythonAnnotator()
        s = a.build_types(f, [annmodel.SomeInteger()])
        a.translator.view()
        assert isinstance(s, annmodel.SomeBool)
