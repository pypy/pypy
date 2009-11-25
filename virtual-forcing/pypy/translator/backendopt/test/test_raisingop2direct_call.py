from pypy.translator.backendopt import raisingop2direct_call, support
from pypy.rpython.test.test_llinterp import get_interpreter
from pypy.rlib.rarithmetic import ovfcheck

import sys

import py


def get_runner(f, exceptedop, types):
    values = [t() for t in types]
    interp, graph = get_interpreter(f, values)
    for op in support.graph_operations(graph):
        if op.opname == exceptedop:
            break
    else:
        assert False, "op %r not found!"%(exceptedop,)
    t = interp.typer.annotator.translator # FIIISH!
    raisingop2direct_call.raisingop2direct_call(t, [graph])
    def ret(*args):
        assert map(type, args) == types
        return interp.eval_graph(graph, args)
    return ret

def test_test_machinery():
    def f(x, y):
        try:
            return x + y
        except OverflowError:
            return 123
    py.test.raises(AssertionError, "get_runner(f, 'int_add_ovf', [int, int])")
    def f(x, y):
        try:
            return ovfcheck(x + y)
        except OverflowError:
            return 123
    fn = get_runner(f, 'int_add_ovf', [int, int])
    res = fn(0, 0)
    assert res == 0


def test_division():
    def f(x, y):
        try:
            return x//y
        except ZeroDivisionError:
            return 123
    fn = get_runner(f, 'int_floordiv_zer', [int, int])
    res = fn(1, 0)
    assert res == 123
    res = fn(-5, 2)
    assert res == -3

    # this becomes an int_floordiv_ovf_zer already?
##     def g(x, y):
##         try:
##             return ovfcheck(x//y)
##         except OverflowError:
##             return 123
##     gn = get_runner(g, 'int_floordiv_ovf', [int, int])
##     res = gn(-sys.maxint-1, -1)
##     assert res == 123
##     res = gn(-5, 2)
##     assert res == -3

    def h(x, y):
        try:
            return ovfcheck(x//y)
        except OverflowError:
            return 123
        except ZeroDivisionError:
            return 246
    hn = get_runner(h, 'int_floordiv_ovf_zer', [int, int])
    res = hn(-sys.maxint-1, -1)
    assert res == 123
    res = hn(1, 0)
    assert res == 246
    res = hn(-5, 2)
    assert res == -3

def test_modulo():
    def f(x, y):
        try:
            return x%y
        except ZeroDivisionError:
            return 123
    fn = get_runner(f, 'int_mod_zer', [int, int])
    res = fn(0, 0)
    assert res == 123
    res = fn(-5, 2)
    assert res == 1


    # this becomes an int_mod_ovf_zer already?
##     def g(x, y):
##         try:
##             return ovfcheck(x%y)
##         except OverflowError:
##             return 123
##     gn = get_runner(g, 'int_mod_ovf', [int, int])
##     res = gn(-sys.maxint-1, -1)
##     assert res == 123
##     res = gn(-5, 2)
##     assert res == -3

    def h(x, y):
        try:
            return ovfcheck(x%y)
        except OverflowError:
            return 123
        except ZeroDivisionError:
            return 246
    hn = get_runner(h, 'int_mod_ovf_zer', [int, int])
    res = hn(-sys.maxint-1, -1)
    assert res == 123
    res = hn(1, 0)
    assert res == 246
    res = hn(-5, 2)
    assert res == 1
