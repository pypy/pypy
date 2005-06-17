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


class MyBaseWithInit:
    def __init__(self, a):
        self.a1 = a

def test_class_init():
    def f(a):
        instance = MyBaseWithInit(a)
        return instance.a1
    assert interpret(f, [5]) == 5


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
