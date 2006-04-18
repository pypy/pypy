"""
Check that backendopt is able to remove most of the overhead introduced
by the rctypes rtyping.
"""

import pypy.rpython.rctypes.implementation
from pypy import conftest
from pypy.rpython.test.test_llinterp import gengraph
from pypy.translator.backendopt.all import backend_optimizations

try:
    import ctypes
except ImportError:
    py.test.skip("this test needs ctypes installed")

from ctypes import c_int


def find_mallocs(func, argtypes):
    t, typer, graph = gengraph(func, argtypes)
    backend_optimizations(t)
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
