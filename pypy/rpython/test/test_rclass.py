from pypy.translator.translator import Translator
from pypy.rpython.lltype import *
from pypy.rpython.rtyper import RPythonTyper


def rtype(fn, argtypes=[]):
    t = Translator(fn)
    t.annotate(argtypes)
    typer = RPythonTyper(t.annotator)
    typer.specialize()
    #t.view()
    t.checkgraphs()
    return t


class EmptyBase(object):
    pass


def test_simple():
    def dummyfn():
        x = EmptyBase()
        return x
    rtype(dummyfn)

def test_instanceattr():
    def dummyfn():
        x = EmptyBase()
        x.a = 5
        x.a += 1
        return x.a
    rtype(dummyfn)


class Random:
    xyzzy = 12
    yadda = 21

def test_classattr():
    def dummyfn():
        x = Random()
        return x.xyzzy
    rtype(dummyfn)

def test_classattr_as_defaults():
    def dummyfn():
        x = Random()
        x.xyzzy += 1
        return x.xyzzy
    rtype(dummyfn)

def test_prebuilt_instance():
    a = EmptyBase()
    a.x = 5
    def dummyfn():
        a.x += 1
        return a.x
    rtype(dummyfn)

def WORKING_ON_test_recursive_prebuilt_instance():
    a = EmptyBase()
    b = EmptyBase()
    a.x = 5
    b.x = 6
    a.peer = b
    b.peer = a
    def dummyfn():
        return a.peer.x
    rtype(dummyfn)
