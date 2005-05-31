from pypy.translator.translator import Translator
from pypy.rpython.lltype import *
from pypy.rpython.rtyper import RPythonTyper


def test_simple():
    def dummyfn(i):
        s = 'hello'
        return s[i]

    t = Translator(dummyfn)
    t.annotate([int])
    typer = RPythonTyper(t.annotator)
    typer.specialize()
    #t.view()
    t.checkgraphs()


def test_nonzero():
    def dummyfn(i, s):
        if i < 0:
            s = None
        if i > -2:
            return bool(s)
        else:
            return False

    t = Translator(dummyfn)
    t.annotate([int, str])
    typer = RPythonTyper(t.annotator)
    typer.specialize()
    #t.view()
    t.checkgraphs()

def test_hash():
    def dummyfn(s):
        return hash(s)

    t = Translator(dummyfn)
    t.annotate([str])
    typer = RPythonTyper(t.annotator)
    typer.specialize()
    #t.view()
    t.checkgraphs()
