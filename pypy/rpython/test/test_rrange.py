from pypy.translator.translator import Translator
from pypy.rpython.rrange import *
from pypy.rpython.test.test_llinterp import interpret

def test_rlist_range():
    def test1(start, stop, step):
        expected = range(start, stop, step)
        length = len(expected)
        l = ll_newrange(start, stop)
        assert ll_rangelen(l, step) == length
        lst = [ll_rangeitem(l, i, step) for i in range(length)]
        assert lst == expected
        lst = [ll_rangeitem_nonneg(l, i, step) for i in range(length)]
        assert lst == expected
        lst = [ll_rangeitem(l, i-length, step) for i in range(length)]
        assert lst == expected

    for start in (-10, 0, 1, 10):
        for stop in (-8, 0, 4, 8, 25):
            for step in (1, 2, 3, -1, -2):
                test1(start, stop, step)

# ____________________________________________________________

def test_range():
    def dummyfn(N):
        total = 0
        for i in range(N):
            total += i
        return total
    res = interpret(dummyfn, [10])
    assert res == 45

def test_range_is_lazy():
    def dummyfn(N, M):
        total = 0
        for i in range(M):
            if i == N:
                break
            total += i
        return total
    res = interpret(dummyfn, [10, 2147418112])
    assert res == 45

def test_range_item():
    def dummyfn(start, stop, i):
        r = range(start, stop)
        return r[i]
    res = interpret(dummyfn, [10, 17, 4])
    assert res == 14
    res = interpret(dummyfn, [10, 17, -2])
    assert res == 15

def test_range():
    def dummyfn(N):
        total = 0
        for i in xrange(N):
            total += i
        return total
    res = interpret(dummyfn, [10])
    assert res == 45
