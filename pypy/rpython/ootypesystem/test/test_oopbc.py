from pypy.rpython.ootypesystem import ootype
from pypy.rpython.test.test_llinterp import interpret
import py

def test_function_pointer():
    def g1():
        return 111
    def g2():
        return 222
    def f(flag):
        if flag:
            g = g1
        else:
            g = g2
        return g() - 1
    res = interpret(f, [True], type_system='ootype')
    assert res == 110
    res = interpret(f, [False], type_system='ootype')
    assert res == 221

def test_call_classes():
    class A: pass
    class B(A): pass
    def f(i):
        if i == 1:
            cls = B
        else:
            cls = A
        return cls()
    res = interpret(f, [0], type_system='ootype')
    assert ootype.dynamicType(res)._name.split(".")[-1] == 'A'
    res = interpret(f, [1], type_system='ootype')
    assert ootype.dynamicType(res)._name.split(".")[-1] == 'B'

def test_call_classes_init():
    class A: 
        def __init__(self, a, b=0):
            self.a = a
    class B(A): 
        def __init__(self, a):
            self.a = a + 1
    def f(i):
        if i == 1:
            cls = B
        else:
            cls = A
        return cls(a=1).a
    res = interpret(f, [0], type_system='ootype')
    assert res == 1
    res = interpret(f, [1], type_system='ootype')
    assert res == 2

def test_method_call_kwds():
    class A:
        def m(self, a, b=0, c=0):
            return a + b + c
    
    def f1():
        a = A()
        return a.m(1, b=2)
    def f2():
        a = A()
        return a.m(1, b=2, c=3)
    assert 3 == interpret(f1, [], type_system="ootype")
    assert 6 == interpret(f2, [], type_system="ootype")

def test_classes_attribute():
    class A: 
        a = 3
    class B(A): 
        a = 2
    def f(i):
        if i == 1:
            cls = B
        else:
            cls = A
        instance = cls()
        return cls.a
    res = interpret(f, [0], type_system='ootype')
    assert res == 3
    res = interpret(f, [1], type_system='ootype')
    assert res == 2

def test_quasi_immutable():
    class A(object):
        _immutable_fields_ = ['x?']
        def __init__(self):
            self.x = 3
        def foo(self):
            return self.x

    a = A()

    def f():
        return a.foo()
    
    res = interpret(f, [], type_system='ootype')
    assert res == 3
