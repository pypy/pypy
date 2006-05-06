import sys
from pypy.rpython.test.test_llinterp import interpret
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.objectmodel import UnboxedValue


class A(object):
    def meth(self, x):
        raise NotImplementedError

class B(A):
    def __init__(self, normalint):
        self.normalint = normalint
    def meth(self, x):
        return self.normalint + x + 2

class C(A, UnboxedValue):
    __slots__ = 'smallint'
    def meth(self, x):
        return self.smallint + x + 3

# ____________________________________________________________

def test_instantiate():
    def fn1(n):
        return C(n)
    res = interpret(fn1, [42])
    value = lltype.cast_ptr_to_int(res)
    assert value == 42 * 2 + 1    # for now

def test_attribute():
    def fn1(n):
        return C(n).smallint
    res = interpret(fn1, [42])
    assert res == 42

def test_getvalue():
    def fn1(n):
        return C(n).getvalue()
    res = interpret(fn1, [42])
    assert res == 42

def test_overflowerror():
    def makeint(n):
        try:
            return C(n)
        except OverflowError:   # 'n' out of range
            return B(n)

    def fn2(n):
        x = makeint(n)
        if isinstance(x, B):
            return 'B', x.normalint
        elif isinstance(x, C):
            return 'C', x.smallint
        else:
            return 'A', 0

    res = interpret(fn2, [-117])
    assert res.item0 == 'C'
    assert res.item1 == -117

    res = interpret(fn2, [sys.maxint])
    assert res.item0 == 'B'
    assert res.item1 == sys.maxint

def test_prebuilt():
    c = C(111)
    b = B(939393)

    def makeint(n):
        if n < 0:
            x = c
        elif n > 0:
            x = C(n)
        else:
            x = b
        return x

    def fn(n):
        x = makeint(n)
        if isinstance(x, B):
            return 'B', x.normalint
        elif isinstance(x, C):
            return 'C', x.smallint
        else:
            return 'A', 0

    res = interpret(fn, [12])
    assert res.item0 == 'C'
    assert res.item1 == 12
    res = interpret(fn, [-1])
    assert res.item0 == 'C'
    assert res.item1 == 111
    res = interpret(fn, [0])
    assert res.item0 == 'B'
    assert res.item1 == 939393

def test_C_or_None():
    def g(x):
        if x is None:
            return sys.maxint
        else:
            return x.smallint
    def fn(n):
        if n < 0:
            x = None
        else:
            x = C(n)
        return g(x)

    res = interpret(fn, [-1])
    assert res == sys.maxint
    res = interpret(fn, [56])
    assert res == 56

def test_type():
    def fn(n):
        if n < 0:
            x = B(n)
        else:
            x = C(n)
        return type(x) is B, type(x) is C

    res = interpret(fn, [-212])
    assert res.item0 and not res.item1
    res = interpret(fn, [9874])
    assert res.item1 and not res.item0

def test_str():
    def fn(n):
        if n > 0:
            x = B(n)
        else:
            x = C(n)
        return str(x)
    res = interpret(fn, [-832])
    assert ''.join(res.chars) == '<unboxed -832>'
    res = interpret(fn, [1])
    assert ''.join(res.chars) == '<B object>'

def test_method():
    def fn(n):
        if n > 0:
            x = B(n)
        else:
            x = C(n)
        return x.meth(100)
    res = interpret(fn, [1000])
    assert res == 1102
    res = interpret(fn, [-1000])
    assert res == -897
