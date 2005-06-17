from pypy.translator.translator import Translator
from pypy.rpython.lltype import *
from pypy.rpython.rtyper import RPythonTyper
from pypy.rpython.test.test_llinterp import interpret


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

def test_concat():
    def dummyfn(s1, s2):
        return s1 + s2

    t = Translator(dummyfn)
    t.annotate([str, str])
    typer = RPythonTyper(t.annotator)
    typer.specialize()
    #t.view()
    t.checkgraphs()

def test_char_constant():
    def dummyfn(s):
        return s + '.'
    res = interpret(dummyfn, ['x'])
    assert len(res.chars) == 2
    assert res.chars[0] == 'x'
    assert res.chars[1] == '.'
