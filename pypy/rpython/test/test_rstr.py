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

def test_char_compare():
    res = interpret(lambda c1, c2: c1 == c2,  ['a', 'b'])
    assert res is False
    res = interpret(lambda c1, c2: c1 == c2,  ['a', 'a'])
    assert res is True
    res = interpret(lambda c1, c2: c1 <= c2,  ['z', 'a'])
    assert res is False

def test_str_compare():
    def fn(i, j):
        s1 = ['one', 'two']
        s2 = ['one', 'two', 'o', 'on', 'twos', 'foobar']
        return s1[i] == s2[j]
    for i in range(2):
        for j in range(6):
            res = interpret(fn, [i, j])
            assert res is fn(i, j)

    def fn(i, j):
        s1 = ['one', 'two']
        s2 = ['one', 'two', 'o', 'on', 'twos', 'foobar']
        return s1[i] != s2[j]
    for i in range(2):
        for j in range(6):
            res = interpret(fn, [i, j])
            assert res is fn(i, j)

