from py.test import raises
from lib_pypy import itertools

class TestItertools(object):

    def test_compress(self):
        it = itertools.compress(['a', 'b', 'c'], [0, 1, 0])

        assert list(it) == ['b']

    def test_compress_diff_len(self):
        it = itertools.compress(['a'], [])
        raises(StopIteration, it.next)

    def test_product(self):
        l = [1, 2]
        m = ['a', 'b']

        prodlist = itertools.product(l, m)
        assert list(prodlist) == [(1, 'a'), (1, 'b'), (2, 'a'), (2, 'b')]

    def test_product_repeat(self):
        l = [1, 2]
        m = ['a', 'b']

        prodlist = itertools.product(l, m, repeat=2)
        ans = [(1, 'a', 1, 'a'), (1, 'a', 1, 'b'), (1, 'a', 2, 'a'),
               (1, 'a', 2, 'b'), (1, 'b', 1, 'a'), (1, 'b', 1, 'b'),
               (1, 'b', 2, 'a'), (1, 'b', 2, 'b'), (2, 'a', 1, 'a'),
               (2, 'a', 1, 'b'), (2, 'a', 2, 'a'), (2, 'a', 2, 'b'),
               (2, 'b', 1, 'a'), (2, 'b', 1, 'b'), (2, 'b', 2, 'a'),
               (2, 'b', 2, 'b')]
        assert list(prodlist) == ans

    def test_product_diff_sizes(self):
        l = [1, 2]
        m = ['a']

        prodlist = itertools.product(l, m)
        assert list(prodlist) == [(1, 'a'), (2, 'a')]

        l = [1]
        m = ['a', 'b']
        prodlist = itertools.product(l, m)
        assert list(prodlist) == [(1, 'a'), (1, 'b')]

    def test_product_toomany_args(self):
        l = [1, 2]
        m = ['a']
        raises(TypeError, itertools.product, l, m, repeat=1, foo=2)

    def test_tee_copy_constructor(self):
        a, b = itertools.tee(range(10))
        next(a)
        next(a)
        c, d = itertools.tee(a)
        assert list(a) == list(d)

    def test_product_kwargs(self):
        raises(TypeError, itertools.product, range(10), garbage=1)

    def test_takewhile_stops(self):
        tw = itertools.takewhile(lambda x: bool(x), [1, 1, 0, 1, 1])
        next(tw)
        next(tw)
        raises(StopIteration, next, tw)
        raises(StopIteration, next, tw)
