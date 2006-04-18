"""
Check that backendopt is able to remove most of the overhead introduced
by the rctypes rtyping.
"""

import py
import pypy.rpython.rctypes.implementation
from pypy import conftest
from pypy.rpython.test.test_llinterp import gengraph
from pypy.translator.backendopt.all import backend_optimizations

try:
    import ctypes
except ImportError:
    py.test.skip("this test needs ctypes installed")

from ctypes import c_int, Structure, pointer, POINTER


def find_mallocs(func, argtypes):
    t, typer, graph = gengraph(func, argtypes)
    backend_optimizations(t, inline_threshold=10)
    if conftest.option.view:
        t.view()

    result = []
    for block in t.graphs[0].iterblocks():
        for op in block.operations:
            if op.opname.startswith('malloc'):
                result.append(op.result.concretetype)
    return result


def test_simple():
    def func(n):
        x = c_int(n)
        return x.value

    mallocs = find_mallocs(func, [int])
    assert not mallocs

def test_labs():
    from pypy.rpython.rctypes.test import test_rfunc
    def func(n):
        return test_rfunc.labs(n)

    mallocs = find_mallocs(func, [int])
    assert not mallocs

def test_atoi():
    from pypy.rpython.rctypes.test import test_rfunc
    def func(s):
        return test_rfunc.atoi(s)

    mallocs = find_mallocs(func, [str])
    assert not mallocs

def test_array_getitem():
    A = c_int * 10
    def func(n):
        a = A()
        a[n] = n*2
        return a[n]

    mallocs = find_mallocs(func, [int])
    assert len(mallocs) <= 1    # for A() only

def test_array_setitem():
    class S(Structure):
        _fields_ = [('x', c_int)]
    A = POINTER(S) * 10

    def func(a, s, i):
        while i > 0:
            s.x = i*i
            a[i] = pointer(s)
            i -= 1
        return a[i].contents.x

    mallocs = find_mallocs(func, [A, S, int])
    assert not mallocs

def test_struct_setitem():
    py.test.skip("not working yet")
    class S(Structure):
        _fields_ = [('x', c_int)]
    class T(Structure):
        _fields_ = [('s', POINTER(S))]
    def make_t(i):
        t = T()
        s = S()
        s.x = i*i
        t.s = pointer(s)
        return t
    def func():
        t = make_t(17)
        return t.s.contents.x
    
    mallocs = find_mallocs(func, [])
    assert not mallocs    # depends on inlining
