import py

from pypy.rpython.memory.gc import free_non_gc_object, GCError

def test_free_non_gc_object():
    class TestClass(object):
        _raw_allocate_ = True
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
    py.test.raises(GCError, "t.method1()")
    py.test.raises(GCError, "t.method2()") 
    py.test.raises(GCError, "t.a")
    py.test.raises(AssertionError, "free_non_gc_object(TestClass2())")
