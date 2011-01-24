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
