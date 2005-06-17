from pypy.translator.translator import Translator
from pypy.rpython.lltype import *
from pypy.rpython.rtyper import RPythonTyper
from pypy.rpython.test.test_interp import interpret


def rtype(fn, argtypes=[]):
    t = Translator(fn)
    t.annotate(argtypes)
    typer = RPythonTyper(t.annotator)
    typer.specialize()
    t.checkgraphs()
    return t


def test_easy_call():
    def f(x):
        return x+1
    def g(y):
        return f(y+2)
    rtype(g, [int])

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
    rtype(g, [int])


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
    rtype(f, [int, int])

def test_virtual_method_call():
    def f(a, b):
        if a > 0:
            obj = MyBase()
        else:
            obj = MySubclass()
        obj.z = a
        return obj.m(b)
    rtype(f, [int, int])


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
    rtype(f, [int])
