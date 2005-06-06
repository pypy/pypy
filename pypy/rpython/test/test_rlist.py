from pypy.translator.translator import Translator
from pypy.rpython.lltype import *
from pypy.rpython.rtyper import RPythonTyper
from pypy.rpython.rlist import *
from pypy.rpython.rint import signed_repr


def test_rlist():
    rlist = ListRepr(signed_repr)
    rlist.setup()
    l = ll_newlist(rlist.lowleveltype, 3)
    ll_setitem(l, 0, 42)
    ll_setitem(l, -2, 43)
    ll_setitem_nonneg(l, 2, 44)
    ll_append(l, 45)
    assert ll_getitem(l, -4) == 42
    assert ll_getitem_nonneg(l, 1) == 43
    assert ll_getitem(l, 2) == 44
    assert ll_getitem(l, 3) == 45
    assert ll_len(l) == 4

# ____________________________________________________________

def rtype(fn, argtypes=[]):
    t = Translator(fn)
    t.annotate(argtypes)
    typer = RPythonTyper(t.annotator)
    typer.specialize()
    #t.view()
    t.checkgraphs()
    return t


def test_simple():
    def dummyfn():
        l = [10,20,30]
        return l[2]
    rtype(dummyfn)

def test_append():
    def dummyfn():
        l = []
        l.append(5)
        l.append(6)
        return l[0]
    rtype(dummyfn)

def test_len():
    def dummyfn():
        l = [5,10]
        return len(l)
    rtype(dummyfn)

def test_iterate():
    def dummyfn():
        total = 0
        for x in [1,3,5,7,9]:
            total += x
        return total
    rtype(dummyfn)

def test_recursive():
    def dummyfn(N):
        l = []
        while N > 0:
            l = [l]
            N -= 1
        return len(l)
    rtype(dummyfn, [int]) #.view()
