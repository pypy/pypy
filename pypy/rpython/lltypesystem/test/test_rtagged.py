import sys
from pypy.rpython.test.test_llinterp import interpret
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.objectmodel import UnboxedValue


class A(object):
    pass
class B(A):
    def __init__(self, normalint):
        self.normalint = normalint
class C(A, UnboxedValue):
    pass

def test_on_top_of_cpython():
    assert C(17).getvalue() == 17

def test_instantiate():
    def fn1(n):
        return C(n)
    res = interpret(fn1, [42])
    value = lltype.cast_ptr_to_int(res)
    assert value == 42 * 2 + 1    # for now

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
            return 'C', x.getvalue()
        else:
            return 'A', 0

    res = interpret(fn2, [-117])
    assert res.item0 == 'C'
    assert res.item1 == -117

    res = interpret(fn2, [sys.maxint])
    assert res.item0 == 'B'
    assert res.item1 == sys.maxint
