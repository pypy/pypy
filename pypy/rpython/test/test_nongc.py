import py

from pypy.annotation import model as annmodel
from pypy.translator.annrpython import RPythonAnnotator
from pypy.rpython.rtyper import RPythonTyper
from pypy.rpython.objectmodel import free_non_gc_object

def test_free_non_gc_object():
    class TestClass(object):
        _alloc_flavor_ = ""
        def __init__(self, a):
            self.a = a
        def method1(self):
            return self.a
        def method2(self):
            return 42
    class TestClass2(object):
        pass
    t = TestClass(1)
    assert t.method1() == 1
    assert t.method2() == 42
    free_non_gc_object(t)
    py.test.raises(RuntimeError, "t.method1()")
    py.test.raises(RuntimeError, "t.method2()") 
    py.test.raises(RuntimeError, "t.a")
    py.test.raises(AssertionError, "free_non_gc_object(TestClass2())")

def DONOTtest_rtype_free_non_gc_object():
    class TestClass(object):
        _alloc_flavor_ = ""
        def __init__(self, a):
            self.a = a
        def method1(self):
            return self.a
        def method2(self):
            return 42
    def malloc_and_free(a):
        ci = TestClass(a)
        b = ci.a
        free_non_gc_object(ci)
        return b
    a = RPythonAnnotator()
    #does not raise:
    s = a.build_types(malloc_and_free, [annmodel.SomeAddress()])
    assert isinstance(s, annmodel.SomeAddress)
    rtyper = RPythonTyper(a)
    rtyper.specialize()
