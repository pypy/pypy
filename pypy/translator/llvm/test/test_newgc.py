import sys

import py
from pypy.translator.llvm.test.runtest import *
from pypy.rpython.lltypesystem import lltype, llmemory, llarena

def test_gc_offsets():
    STRUCT = lltype.GcStruct('S1', ('x', lltype.Signed), ('y', lltype.Char))
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
    assert i1 % 4 == 0
    assert 12 <= i1 <= 24
    assert 4 <= i2 <= i1 - 8
    assert 4 <= i3 <= 12
    assert i4 == i5
    assert i3 + 4 <= i5

def test_1():
    def fn(n):
        d = {}
        for i in range(n):
            d[i] = str(i)
        return int(d[n//2])

    mod, f = compile_test(fn, [int], gcpolicy="semispace")
    assert f(5000) == fn(5000)

class BaseTestGC(object):

    def test_weakref(self):
        import weakref
        from pypy.rlib import rgc

        class A:
            pass

        keepalive = []
        def fn():
            n = 7000
            weakrefs = []
            a = None
            for i in range(n):
                if i & 1 == 0:
                    a = A()
                    a.index = i
                assert a is not None
                weakrefs.append(weakref.ref(a))
                if i % 7 == 6:
                    keepalive.append(a)
            rgc.collect()
            count_free = 0
            for i in range(n):
                a = weakrefs[i]()
                if i % 7 == 6:
                    assert a is not None
                if a is not None:
                    assert a.index == i & ~1
                else:
                    count_free += 1
            return count_free

        mod, f = compile_test(fn, [], gcpolicy=self.gcpolicy)
        res = f()
        # more than half of them should have been freed, ideally up to 6000
        assert 3500 <= res <= 6000

    def test_prebuilt_weakref(self):
        import weakref
        from pypy.rlib import rgc
        class A:
            pass
        a = A()
        a.hello = 42
        refs = [weakref.ref(a), weakref.ref(A())]
        rgc.collect()
        def fn():
            result = 0
            for i in range(2):
                a = refs[i]()
                rgc.collect()
                if a is None:
                    result += (i+1)
                else:
                    result += a.hello * (i+1)
            return result

        mod, f = compile_test(fn, [], gcpolicy=self.gcpolicy)
        res = f()
        assert res == fn()


class TestBoehmGC(BaseTestGC):
    gcpolicy = "boehm"

class TestFrameworkGC(BaseTestGC):
    gcpolicy = "semispace"
