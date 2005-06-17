from pypy.translator.translator import Translator
from pypy.rpython.lltype import *
from pypy.rpython.test.test_llinterp import interpret


class EmptyBase(object):
    pass


def test_simple():
    def dummyfn():
        x = EmptyBase()
        return x
    res = interpret(dummyfn, [])
    T = typeOf(res)
    assert isinstance(T, Ptr) and isinstance(T.TO, GcStruct)

def test_instanceattr():
    def dummyfn():
        x = EmptyBase()
        x.a = 5
        x.a += 1
        return x.a
    res = interpret(dummyfn, [])
    assert res == 6

class Random:
    xyzzy = 12
    yadda = 21

def test_classattr():
    def dummyfn():
        x = Random()
        return x.xyzzy
    res = interpret(dummyfn, [])
    assert res == 12

def test_classattr_as_defaults():
    def dummyfn():
        x = Random()
        x.xyzzy += 1
        return x.xyzzy
    res = interpret(dummyfn, [])
    assert res == 13

def test_prebuilt_instance():
    a = EmptyBase()
    a.x = 5
    def dummyfn():
        a.x += 1
        return a.x
    interpret(dummyfn, [])

def test_recursive_prebuilt_instance():
    a = EmptyBase()
    b = EmptyBase()
    a.x = 5
    b.x = 6
    a.peer = b
    b.peer = a
    def dummyfn():
        return a.peer.peer.peer.x
    res = interpret(dummyfn, [])
    assert res == 6

# method calls
class A:
    def f(self):
        return self.g()

    def g(self):
        return 42

class B(A):
    def g(self):
        return 1

def test_simple_method_call():
    def f(i):
        if i:
            a = A()
        else:
            a = B()
        return a.f()
    res = interpret(f, [True])
    assert res == 42
    res = interpret(f, [False])
    assert res == 1
