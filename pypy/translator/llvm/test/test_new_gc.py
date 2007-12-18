import sys

import py
from pypy.translator.llvm.test.runtest import *


def test_1():
    py.test.skip("in-progress")
    def fn(n):
        d = {}
        for i in range(n):
            d[i] = str(i)
        return d[n//2]

    mod, f = compile_test(fn, [int], gcpolicy="semispace")
    assert f(5000) == fn(5000)
