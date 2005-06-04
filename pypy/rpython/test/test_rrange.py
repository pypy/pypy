from pypy.rpython.rrange import *

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
