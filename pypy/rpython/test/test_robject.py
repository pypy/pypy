from pypy.translator.translator import Translator
from pypy.rpython.lltype import *


def rtype(fn, argtypes=[]):
    t = Translator(fn)
    t.annotate(argtypes)
    t.specialize()
    t.checkgraphs()
    return t


def test_set_del_item():
    def dummyfn(obj):
        return obj + 1
    rtype(dummyfn, [object])
