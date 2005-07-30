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
        py.test.raises(AssertionError,
                       a.build_types, f, [annmodel.SomeAddress(is_null=True)])

    def test_memcopy(self):
        def f(addr1, addr2):
            raw_memcopy(addr1, addr2, 100)
        a = RPythonAnnotator()
        #does not raise:
        s = a.build_types(f, [annmodel.SomeAddress(), annmodel.SomeAddress()])
        py.test.raises(AssertionError, a.build_types, f,
                       [annmodel.SomeAddress(is_null=True),
                        annmodel.SomeAddress()])

    
