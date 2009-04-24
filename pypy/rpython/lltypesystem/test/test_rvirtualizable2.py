import py
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.test.test_llinterp import interpret


class V(object):
    _virtualizable2_ = True

    def __init__(self, v):
        self.v = v

def test_simple():
    def f(v):
        vinst = V(v)
        return vinst, vinst.v
    res = interpret(f, [42])
    assert res.item1 == 42
    res = lltype.normalizeptr(res.item0)
    assert res.inst_v == 42
    assert not res.vable_rti
