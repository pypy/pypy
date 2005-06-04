from pypy.translator.translator import Translator
from pypy.rpython.lltype import *
from pypy.rpython.rtyper import RPythonTyper



class EmptyBase(object):
    pass


def test_simple():
    def dummyfn():
        x = EmptyBase()
        return x

    t = Translator(dummyfn)
    t.annotate([])
    typer = RPythonTyper(t.annotator)
    typer.specialize()
    #t.view()
    t.checkgraphs()

def test_instanceattr():
    def dummyfn():
        x = EmptyBase()
        x.a = 5
        x.a += 1
        return x.a

    t = Translator(dummyfn)
    t.annotate([])
    typer = RPythonTyper(t.annotator)
    typer.specialize()
    #t.view()
    t.checkgraphs()
