from pypy.translator.translator import Translator
from pypy.rpython.lltype import *
from pypy.rpython.rtyper import RPythonTyper


def test_simple():
    def dummyfn(x):
        return x+1

    t = Translator(dummyfn)
    t.annotate([int])
    typer = RPythonTyper(t.annotator)
    typer.specialize()
    #t.view()
    t.checkgraphs()


def test_function_call():
    def g(x, y):
        return x-y
    def f(x):
        return g(1, x)

    t = Translator(f)
    t.annotate([int])
    typer = RPythonTyper(t.annotator)
    typer.specialize()
    #t.view()
    t.checkgraphs()
