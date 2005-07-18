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

def test_prebuilt_instances_with_void():
    def marker():
        return 42
    a = EmptyBase()
    a.nothing_special = marker
    def dummyfn():
        return a.nothing_special()
    res = interpret(dummyfn, [])
    assert res == 42

# method calls
class A:
    def f(self):
        return self.g()

    def g(self):
        return 42

class B(A):
    def g(self):
        return 1

class C(B):
    pass

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

def test_isinstance():
    def f(i):
        if i == 0:
            o = None
        elif i == 1:
            o = A()
        elif i == 2:
            o = B()
        else:
            o = C()
        return 100*isinstance(o, A)+10*isinstance(o, B)+1*isinstance(o ,C)

    res = interpret(f, [1])
    assert res == 100
    res = interpret(f, [2])
    assert res == 110
    res = interpret(f, [3])
    assert res == 111

    res = interpret(f, [0])
    assert res == 0

def test_method_used_in_subclasses_only():
    class A:
        def meth(self):
            return 123
    class B(A):
        pass
    def f():
        x = B()
        return x.meth()
    res = interpret(f, [])
    assert res == 123

def test_method_both_A_and_B():
    class A:
        def meth(self):
            return 123
    class B(A):
        pass
    def f():
        a = A()
        b = B()
        return a.meth() + b.meth()
    res = interpret(f, [])
    assert res == 246

def test_issubclass_type():
    class A:
        pass
    class B(A):
        pass
    def f(i):
        if i == 0: 
            c1 = A()
        else: 
            c1 = B()
        return issubclass(type(c1), B)
    assert interpret(f, [0], view=False, viewbefore=False) == False 
    assert interpret(f, [1], view=False, viewbefore=False) == True

    def g(i):
        if i == 0: 
            c1 = A()
        else: 
            c1 = B()
        return issubclass(type(c1), A)
    assert interpret(g, [0], view=False, viewbefore=False) == True
    assert interpret(g, [1], view=False, viewbefore=False) == True

def test_staticmethod():
    class A(object):
        f = staticmethod(lambda x, y: x*y)
    def f():
        a = A()
        return a.f(6, 7)
    res = interpret(f, [])
    assert res == 42

def test_is():
    class A: pass
    class B(A): pass
    class C: pass
    def f(i):
        a = A()
        b = B()
        c = C()
        d = None
        e = None
        if i == 0:
            d = a
        elif i == 1:
            d = b
        elif i == 2:
            e = c
        return (0x0001*(a is b) | 0x0002*(a is c) | 0x0004*(a is d) |
                0x0008*(a is e) | 0x0010*(b is c) | 0x0020*(b is d) |
                0x0040*(b is e) | 0x0080*(c is d) | 0x0100*(c is e) |
                0x0200*(d is e))
    res = interpret(f, [0])
    assert res == 0x0004
    res = interpret(f, [1])
    assert res == 0x0020
    res = interpret(f, [2])
    assert res == 0x0100
    res = interpret(f, [3])
    assert res == 0x0200

def test_eq():
    class A: pass
    class B(A): pass
    class C: pass
    def f(i):
        a = A()
        b = B()
        c = C()
        d = None
        e = None
        if i == 0:
            d = a
        elif i == 1:
            d = b
        elif i == 2:
            e = c
        return (0x0001*(a == b) | 0x0002*(a == c) | 0x0004*(a == d) |
                0x0008*(a == e) | 0x0010*(b == c) | 0x0020*(b == d) |
                0x0040*(b == e) | 0x0080*(c == d) | 0x0100*(c == e) |
                0x0200*(d == e))
    res = interpret(f, [0])
    assert res == 0x0004
    res = interpret(f, [1])
    assert res == 0x0020
    res = interpret(f, [2])
    assert res == 0x0100
    res = interpret(f, [3])
    assert res == 0x0200

def test_ne():
    class A: pass
    class B(A): pass
    class C: pass
    def f(i):
        a = A()
        b = B()
        c = C()
        d = None
        e = None
        if i == 0:
            d = a
        elif i == 1:
            d = b
        elif i == 2:
            e = c
        return (0x0001*(a != b) | 0x0002*(a != c) | 0x0004*(a != d) |
                0x0008*(a != e) | 0x0010*(b != c) | 0x0020*(b != d) |
                0x0040*(b != e) | 0x0080*(c != d) | 0x0100*(c != e) |
                0x0200*(d != e))
    res = interpret(f, [0])
    assert res == ~0x0004 & 0x3ff
    res = interpret(f, [1])
    assert res == ~0x0020 & 0x3ff
    res = interpret(f, [2])
    assert res == ~0x0100 & 0x3ff
    res = interpret(f, [3])
    assert res == ~0x0200 & 0x3ff
