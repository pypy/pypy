from pypy.translator.translator import Translator
from pypy.rpython.rrange import *
from pypy.rpython.test.test_llinterp import interpret

def test_rlist_range():
    def test1(start, stop, step, varstep):
        expected = range(start, stop, step)
        length = len(expected)
        if varstep:
            l = ll_newrangest(start, stop, step)
            step = l.step
        else:
            l = ll_newrange(start,stop)
        assert ll_rangelen(l, step) == length
        lst = [ll_rangeitem(dum_nocheck, l, i, step) for i in range(length)]
        assert lst == expected
        lst = [ll_rangeitem_nonneg(dum_nocheck, l, i, step) for i in range(length)]
        assert lst == expected
        lst = [ll_rangeitem(dum_nocheck, l, i-length, step) for i in range(length)]
        assert lst == expected

    for start in (-10, 0, 1, 10):
        for stop in (-8, 0, 4, 8, 25):
            for step in (1, 2, 3, -1, -2):
                for varstep in False, True:
                    test1(start, stop, step, varstep)

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

def test_xrange():
    def dummyfn(N):
        total = 0
        for i in xrange(N):
            total += i
        return total
    res = interpret(dummyfn, [10])
    assert res == 45

def test_range_len():
    def dummyfn(start, stop):
        r = range(start, stop)
        return len(r)
    start, stop = 10, 17
    res = interpret(dummyfn, [start, stop])
    assert res == dummyfn(start, stop)

def test_range2list():
    def dummyfn(start, stop):
        r = range(start, stop)
        r.reverse()
        return r[0]
    start, stop = 10, 17
    res = interpret(dummyfn, [start, stop])
    assert res == dummyfn(start, stop)

def check_failed(func, *args):
    try:
        interpret(func, *args)
    except:
        return True
    else:
        return False

def test_range_extra():
    def failingfn_const():
        r = range(10, 17, 0)
        return r[-1]
    assert check_failed(failingfn_const, [])

    def failingfn_var(step):
        r = range(10, 17, step)
        return r[-1]
    step = 3
    res = interpret(failingfn_var, [step])
    assert res == failingfn_var(step)
    step = 0
    assert check_failed(failingfn_var, [step])

def test_range_iter():
    def fn(start, stop, step):
        res = 0
        if step == 0:
            if stop >= start:
                r = range(start, stop, 1)
            else:
                r = range(start, stop, -1)
        else:
            r = range(start, stop, step)
        for i in r:
            res = res * 51 + i
        return res
    res = interpret(fn, [2, 7, 1])#, view=True)
    # XXX not finished, stunned

# XXX the above test works, but it always turns the range into a list!!!
#
# here another test that show that this even happens in a simple case.
# I think this is an annotator problem

def test_range_funny():
    # this is just an example.
    # making start/stop different is ok
    def fn(start, stop):
        if stop >= start:
            r = range(start, stop, 1)
        else:
            r = range(start, stop-1, 1)
        return r[-2]
    # making step different turns the range into a list!
    # I think, we should instead either specialize the blocks,
    # or morph the whole thing into the variable step case???
    def fn(start, stop):
        if stop >= start:
            r = range(start, stop, 1)
        else:
            r = range(start, stop, -1)
        return r[-2]
    res = interpret(fn, [2, 7])#, view=True)
