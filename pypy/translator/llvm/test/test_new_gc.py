import sys

import py
from pypy.translator.llvm.test.runtest import *
from pypy.rpython.lltypesystem import lltype, llmemory, llarena

def test_gc_offsets():
    py.test.skip("in-progress")
    STRUCT = lltype.GcStruct('S1', ('x', lltype.Signed))
    ARRAY = lltype.GcArray(lltype.Signed)
    s1 = llarena.round_up_for_allocation(llmemory.sizeof(STRUCT))
    s2 = llmemory.offsetof(STRUCT, 'x')
    s3 = llmemory.ArrayLengthOffset(ARRAY)
    s4 = llmemory.sizeof(ARRAY, 0)
    s5 = llmemory.ArrayItemsOffset(ARRAY)
    def fn():
        return (s1 * 100000000 +
                s2 * 1000000 +
                s3 * 10000 +
                s4 * 100 +
                s5)
    mod, f = compile_test(fn, [], gcpolicy="semispace")
    res = f()
    i1 = (res // 100000000) % 100
    i2 = (res // 1000000) % 100
    i3 = (res // 10000) % 100
    i4 = (res // 100) % 100
    i5 = (res // 1) % 100
    assert i1 % 8 == 0
    assert 12 <= i1 <= 24
    assert 8 <= i2 <= i1 - 4
    assert 8 <= i3 <= 16
    assert i4 == i5
    assert i3 + 4 <= i5

def test_1():
    py.test.skip("in-progress")
    def fn(n):
        d = {}
        for i in range(n):
            d[i] = str(i)
        return d[n//2]

    mod, f = compile_test(fn, [int], gcpolicy="semispace")
    assert f(5000) == fn(5000)
