from pypy.translator.translator import Translator
from pypy.rpython.lltypes import *
from pypy.rpython.typer import RPythonTyper


def test_simple():
    def dummyfn(x):
        return x+1

    t = Translator(dummyfn)
    t.annotate([int])
    typer = RPythonTyper(t.annotator)
    typer.specialize()
    #t.view()
    assert "did not crash"
