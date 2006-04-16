import py
from pypy.rpython.test.test_llinterp import interpret 
from pypy.rpython.ootypesystem.ootype import *

def test_new():
    LT = List(Signed)
    l = new(LT)
    assert typeOf(l) == LT

def test_len():
    LT = List(Signed)
    l = new(LT)
    assert l.ll_length() == 0

def test_append():
    LT = List(Signed)
    l = new(LT)
    l.append(1)
    assert l.ll_length() == 1

def test_extend():
    LT = List(Signed)
    l1 = new(LT)
    l2 = new(LT)
    l1.append(1)
    l2.append(2)
    l1.extend(l2)
    assert l1.ll_length() == 2

def test_setitem_getitem():
    LT = List(Signed)
    l = new(LT)
    l.append(2)
    assert l.ll_getitem_fast(0) == 2
    l.ll_setitem_fast(0, 3)
    assert l.ll_getitem_fast(0) == 3

def test_setitem_indexerror():
    LT = List(Signed)
    l = new(LT)
    py.test.raises(IndexError, l.ll_getitem_fast, 0)
    py.test.raises(IndexError, l.ll_setitem_fast, 0, 1)

def test_null():
    LT = List(Signed)
    n = null(LT)
    py.test.raises(RuntimeError, "n.append(0)")

def test_eq_hash():
    LT1 = List(Signed)
    LT2 = List(Signed)
    LT3 = List(Unsigned)
    assert LT1 == LT2
    assert LT1 != LT3
    assert hash(LT1) == hash(LT2)

def test_recursive():
    FORWARD = ForwardReference()
    LT = List(FORWARD)
    FORWARD.become(LT)
    assert LT == LT
    assert hash(LT) == hash(LT)
    str(LT) # make sure this doesn't recurse infinitely

    FORWARD2 = ForwardReference()
    LT2 = List(FORWARD2)
    FORWARD2.become(LT2)
    assert LT == LT2
    assert hash(LT) == hash(LT2)

class TestInterpreted:

    def test_append_length(self):
        def f(x):
            l = []
            l.append(x)
            return len(l)
        res = interpret(f, [2], type_system="ootype")
        assert res == 1 

    def test_setitem_getitem(self):
        def f(x):
            l = []
            l.append(3)
            l[0] = x
            return l[0]
        res = interpret(f, [2], type_system="ootype")
        assert res == 2 

    def test_getitem_exception(self):
        def f(x):
            l = []
            l.append(x)
            try:
                return l[1]
            except IndexError:
                return -1
        res = interpret(f, [2], type_system="ootype")
        assert res == -1 

    def test_initialize(self):
        def f(x):
            l = [1, 2]
            l.append(x)
            return l[2]
        res = interpret(f, [3], type_system="ootype")
        assert res == 3 

