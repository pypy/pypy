import py
import sys
from pypy.rlib.rerased import *
from pypy.annotation import model as annmodel
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.rpython.test.test_llinterp import interpret
from pypy.rpython.lltypesystem.rclass import OBJECTPTR
from pypy.rpython.lltypesystem import lltype, llmemory


class X(object):
    pass

class Y(X):
    pass

class Z(X):
    pass


def test_simple():
    x1 = X()
    e = erase(x1)
    assert is_integer(e) is False
    assert unerase(e, X) is x1

def test_simple_none():
    e = erase(None)
    assert unerase(e, X) is None

def test_simple_int():
    e = erase(15)
    assert is_integer(e) is True
    assert unerase(e, int) == 15

def test_simple_int_overflow():
    py.test.raises(OverflowError, erase, sys.maxint)
    py.test.raises(OverflowError, erase, sys.maxint-1)
    py.test.raises(OverflowError, erase, -sys.maxint)
    py.test.raises(OverflowError, erase, -sys.maxint-1)

def test_list():
    l = [X()]
    e = erase_fixedsizelist(l, X)
    assert is_integer(e) is False
    assert unerase_fixedsizelist(e, X) is l

def test_annotate_1():
    def f():
        return erase(X())
    a = RPythonAnnotator()
    s = a.build_types(f, [])
    assert isinstance(s, SomeErased)

def test_annotate_2():
    def f():
        x1 = X()
        e = erase(x1)
        assert not is_integer(e)
        x2 = unerase(e, X)
        return x2
    a = RPythonAnnotator()
    s = a.build_types(f, [])
    assert isinstance(s, annmodel.SomeInstance)
    assert s.classdef == a.bookkeeper.getuniqueclassdef(X)

def test_annotate_3():
    def f():
        e = erase(16)
        assert is_integer(e)
        x2 = unerase(e, int)
        return x2
    a = RPythonAnnotator()
    s = a.build_types(f, [])
    assert isinstance(s, annmodel.SomeInteger)

def test_rtype_1():
    def f():
        return erase(X())
    x = interpret(f, [])
    assert lltype.typeOf(x) == llmemory.GCREF

def test_rtype_2():
    def f():
        x1 = X()
        e = erase(x1)
        assert not is_integer(e)
        x2 = unerase(e, X)
        return x2
    x = interpret(f, [])
    assert lltype.castable(OBJECTPTR, lltype.typeOf(x)) > 0

def test_rtype_3():
    def f():
        e = erase(16)
        assert is_integer(e)
        x2 = unerase(e, int)
        return x2
    x = interpret(f, [])
    assert x == 16


def test_prebuilt_erased():
    e1 = erase(16)
    x1 = X()
    e2 = erase(x1)

    def f():
        assert is_integer(e1)
        assert not is_integer(e2)
        x2 = unerase(e1, int)
        return x2
    x = interpret(f, [])
    assert x == 16

def test_overflow():
    def f(i):
        try:
            e = erase(i)
        except OverflowError:
            return -1
        assert is_integer(e)
        return unerase(e, int)
    x = interpret(f, [16])
    assert x == 16
    x = interpret(f, [sys.maxint])
    assert x == -1

def test_none():
    def foo():
        return unerase(erase(None), X)
    assert foo() is None
    res = interpret(foo, [])
    assert not res

def test_union():
    s_e1 = SomeErased()
    s_e1.const = 1
    s_e2 = SomeErased()
    s_e2.const = 3
    assert not annmodel.pair(s_e1, s_e2).union().is_constant()


def test_rtype_list():
    prebuilt_l = [X()]
    prebuilt_e = erase_fixedsizelist(prebuilt_l, X)
    def l(flag):
        if flag == 1:
            l = [X()]
            e = erase_fixedsizelist(l, X)
        elif flag == 2:
            l = prebuilt_l
            e = erase_fixedsizelist(l, X)
        else:
            l = prebuilt_l
            e = prebuilt_e
        assert is_integer(e) is False
        assert unerase_fixedsizelist(e, X) is l
    interpret(l, [0])
    interpret(l, [1])
    interpret(l, [2])
