from pypy.translator.translator import Translator
from pypy.rpython.lltypes import *
from pypy.rpython.typer import RPythonTyper


def test_simple():
    def dummyfn():
        l = [10,20,30]
        return l[2]

    t = Translator(dummyfn)
    t.annotate([])
    typer = RPythonTyper(t.annotator)
    typer.specialize()
    #t.view()
    assert "did not crash"
