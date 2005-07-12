from pypy.translator.translator import Translator
from pypy.rpython.lltype import *
from pypy.rpython.rtyper import RPythonTyper
from pypy.rpython.test.test_llinterp import interpret


def test_easy_call():
    def f(x):
        return x+1
    def g(y):
        return f(y+2)
    res = interpret(g, [5])
    assert res == 8

def test_multiple_call():
    def f1(x):
        return x+1
    def f2(x):
        return x+2
    def g(y):
        if y < 0:
            f = f1
        else:
            f = f2
        return f(y+3)
    res = interpret(g, [-1])
    assert res == 3
    res = interpret(g, [1])
    assert res == 6


class MyBase:
    def m(self, x):
        return self.z + x

class MySubclass(MyBase):
    def m(self, x):
        return self.z - x

class MyStrangerSubclass(MyBase):
    def m(self, x, y):
        return x*y

def test_method_call():
    def f(a, b):
        obj = MyBase()
        obj.z = a
        return obj.m(b)
    res = interpret(f, [4, 5])
    assert res == 9

def test_virtual_method_call():
    def f(a, b):
        if a > 0:
            obj = MyBase()
        else:
            obj = MySubclass()
        obj.z = a
        return obj.m(b)
    res = interpret(f, [1, 2.3])
    assert res == 3.3
    res = interpret(f, [-1, 2.3])
    assert res == -3.3

def test_stranger_subclass_1():
    def f1():
        obj = MyStrangerSubclass()
        obj.z = 100
        return obj.m(6, 7)
    res = interpret(f1, [])
    assert res == 42

def test_stranger_subclass_2():
    def f2():
        obj = MyStrangerSubclass()
        obj.z = 100
        return obj.m(6, 7) + MyBase.m(obj, 58)
    res = interpret(f2, [])
    assert res == 200


class MyBaseWithInit:
    def __init__(self, a):
        self.a1 = a

class MySubclassWithInit(MyBaseWithInit):
    def __init__(self, a, b):
        MyBaseWithInit.__init__(self, a)
        self.b1 = b

def test_class_init():
    def f(a):
        instance = MyBaseWithInit(a)
        return instance.a1
    assert interpret(f, [5]) == 5

def test_class_init_2():
    def f(a, b):
        instance = MySubclassWithInit(a, b)
        return instance.a1 * instance.b1
    assert interpret(f, [6, 7]) == 42

def test_class_calling_init():
    def f():
        instance = MySubclassWithInit(1, 2)
        instance.__init__(3, 4)
        return instance.a1 * instance.b1
    assert interpret(f, []) == 12


class Freezing:
    def _freeze_(self):
        return True
    def mymethod(self, y):
        return self.x + y

def test_freezing():
    fr1 = Freezing()
    fr2 = Freezing()
    fr1.x = 5
    fr2.x = 6
    def g(fr):
        return fr.x
    def f(n):
        if n > 0:
            fr = fr1
        elif n < 0:
            fr = fr2
        else:
            fr = None
        return g(fr)
    res = interpret(f, [1])
    assert res == 5
    res = interpret(f, [-1])
    assert res == 6

def test_call_frozen_pbc_simple():
    fr1 = Freezing()
    fr1.x = 5
    def f(n):
        return fr1.mymethod(n)
    res = interpret(f, [6])
    assert res == 11

def test_call_frozen_pbc_multiple():
    fr1 = Freezing()
    fr2 = Freezing()
    fr1.x = 5
    fr2.x = 6
    def f(n):
        if n > 0:
            fr = fr1
        else:
            fr = fr2
        return fr.mymethod(n)
    res = interpret(f, [1])
    assert res == 6
    res = interpret(f, [-1])
    assert res == 5

def test_unbound_method():
    def f():
        inst = MySubclass()
        inst.z = 40
        return MyBase.m(inst, 2)
    res = interpret(f, [])
    assert res == 42

def test_call_defaults():
    def g(a, b=2, c=3):
        return a+b+c
    def f1():
        return g(1)
    def f2():
        return g(1, 10)
    def f3():
        return g(1, 10, 100)
    res = interpret(f1, [])
    assert res == 1+2+3
    res = interpret(f2, [])
    assert res == 1+10+3
    res = interpret(f3, [])
    assert res == 1+10+100

def test_call_memoized_function():
    fr1 = Freezing()
    fr2 = Freezing()
    def getorbuild(key):
        a = 1
        if key is fr1:
            result = eval("a+2")
        else:
            result = eval("a+6")
        return result
    getorbuild._annspecialcase_ = "specialize:memo"

    def f1(i):
        if i > 0:
            fr = fr1
        else:
            fr = fr2
        return getorbuild(fr)

    res = interpret(f1, [0]) 
    assert res == 7
    res = interpret(f1, [1]) 
    assert res == 3

def test_call_memoized_cache():

    # this test checks that we add a separate field 
    # per specialization and also it uses a subclass of 
    # the standard pypy.tool.cache.Cache

    from pypy.tool.cache import Cache
    fr1 = Freezing()
    fr2 = Freezing()

    class Cache1(Cache): 
        def _build(self, key): 
            "NOT_RPYTHON" 
            if key is fr1:
                return fr2 
            else:
                return fr1 

    class Cache2(Cache): 
        def _build(self, key): 
            "NOT_RPYTHON" 
            a = 1
            if key is fr1:
                result = eval("a+2")
            else:
                result = eval("a+6")
            return result

    cache1 = Cache1()
    cache2 = Cache2()

    def f1(i):
        if i > 0:
            fr = fr1
        else:
            fr = fr2
        newfr = cache1.getorbuild(fr)
        return cache2.getorbuild(newfr)

    res = interpret(f1, [0], view=0, viewbefore=0)  
    assert res == 3
    res = interpret(f1, [1]) 
    assert res == 7

def test_rpbc_bound_method_static_call():
    class R:
        def meth(self):
            return 0
    r = R()
    m = r.meth
    def fn():
        return m()
    res = interpret(fn, [])
    assert res == 0

def test_constant_return_disagreement():
    class R:
        def meth(self):
            return 0
    r = R()
    def fn():
        return r.meth()
    res = interpret(fn, [])
    assert res == 0

def test_None_is_false():
    def fn(i):
        return bool([None, fn][i])
    res = interpret(fn, [1])
    assert res is True
    res = interpret(fn, [0])
    assert res is False

def test_classpbc_getattr():
    class A:
        myvalue = 123
    class B(A):
        myvalue = 456
    def f(i):
        return [A,B][i].myvalue
    res = interpret(f, [0])
    assert res == 123
    res = interpret(f, [1])
    assert res == 456

def test_function_or_None():
    def g1():
        return 42
    def f(i):
        g = None
        if i > 5:
            g = g1
        if i > 6:
            return g()
        else:
            return 12

    res = interpret(f, [0])
    assert res == 12
    res = interpret(f, [6])
    assert res == 12
    res = interpret(f, [7])
    assert res == 42

def test_classdef_getattr():
    class A:
        myvalue = 123
    class B(A):
        myvalue = 456
    def f(i):
        B()    # for A and B to have classdefs
        return [A,B][i].myvalue
    res = interpret(f, [0])
    assert res == 123
    res = interpret(f, [1])
    assert res == 456

def test_call_classes():
    class A: pass
    class B(A): pass
    def f(i):
        if i == 1:
            cls = B
        else:
            cls = A
        return cls()
    res = interpret(f, [0])
    assert res.super.typeptr.name[0] == 'A'
    res = interpret(f, [1])
    assert res.super.typeptr.name[0] == 'B'

def test_call_classes_with_init():
    class A:
        def __init__(self, z):
            self.z = z
    class B(A):
        def __init__(self, z):
            A.__init__(self, z)
            self.extra = 42
    def f(i, z):
        if i == 1:
            cls = B
        else:
            cls = A
        return cls(z)
    res = interpret(f, [0, 5])
    assert res.super.typeptr.name[0] == 'A'
    assert res.inst_z == 5
    res = interpret(f, [1, -7645])
    assert res.super.typeptr.name[0] == 'B'
    assert res.inst_z == -7645
    assert res._obj._parentstructure().inst_extra == 42
