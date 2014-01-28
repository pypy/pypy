import py
from rpython.jit.metainterp.test.support import LLJitMixin
from rpython.rlib.jit import JitDriver
from rpython.rlib import objectmodel
from collections import OrderedDict

class DictTests:
    @staticmethod
    def newdict():   # overridden in TestLLOrderedDict
        return {}

    def _freeze_(self):
        return True

    def test_dict_set_none(self):
        def fn(n):
            d = self.newdict()
            d[0] = None
            return bool(d[n])
        res = self.interp_operations(fn, [0])
        assert not res

    def test_dict_keys_values_items(self):
        for name, extract, expected in [('keys', None, 'k'),
                                        ('values', None, 'v'),
                                        ('items', 0, 'k'),
                                        ('items', 1, 'v'),
                                        ]:
            myjitdriver = JitDriver(greens = [], reds = ['n', 'dct'])
            def f(n):
                dct = self.newdict()
                while n > 0:
                    myjitdriver.can_enter_jit(n=n, dct=dct)
                    myjitdriver.jit_merge_point(n=n, dct=dct)
                    dct[n] = n*n
                    n -= 1
                sum = 0
                for x in getattr(dct, name)():
                    if extract is not None:
                        x = x[extract]
                    sum += x
                return sum

            if expected == 'k':
                expected = 1 + 2 + 3 + 4 + 5 + 6 + 7 + 8 + 9 + 10
            else:
                expected = 1 + 4 + 9 + 16 + 25 + 36 + 49 + 64 + 81 + 100

            assert f(10) == expected
            res = self.meta_interp(f, [10], listops=True)
            assert res == expected

    def test_dict_iter(self):
        for name, extract, expected in [('iterkeys', None, 60),
                                        ('itervalues', None, 111),
                                        ('iteritems', 0, 60),
                                        ('iteritems', 1, 111),
                                        ]:
            myjitdriver = JitDriver(greens = [], reds = ['total', 'it'])
            def f(n):
                dct = self.newdict()
                dct[n] = 100
                dct[50] = n + 1
                it = getattr(dct, name)()
                total = 0
                while True:
                    myjitdriver.can_enter_jit(total=total, it=it)
                    myjitdriver.jit_merge_point(total=total, it=it)
                    try:
                        x = it.next()
                    except StopIteration:
                        break
                    if extract is not None:
                        x = x[extract]
                    total += x
                return total

            assert f(10) == expected
            res = self.meta_interp(f, [10], listops=True)
            assert res == expected

    def test_dict_trace_hash(self):
        if type(self.newdict()) is not dict:
            py.test.skip("this is an r_dict test")
        myjitdriver = JitDriver(greens = [], reds = ['total', 'dct'])
        def key(x):
            return x % 2
        def eq(x, y):
            return (x % 2) == (y % 2)

        def f(n):
            dct = objectmodel.r_dict(eq, key)
            total = n
            while total:
                myjitdriver.jit_merge_point(total=total, dct=dct)
                if total not in dct:
                    dct[total] = []
                dct[total].append(total)
                total -= 1
            return len(dct[0])

        res1 = f(100)
        res2 = self.meta_interp(f, [100], listops=True)
        assert res1 == res2
        self.check_resops(int_mod=2) # the hash was traced and eq, but cached

    def test_dict_setdefault(self):
        myjitdriver = JitDriver(greens = [], reds = ['total', 'dct'])
        def f(n):
            dct = self.newdict()
            total = n
            while total:
                myjitdriver.jit_merge_point(total=total, dct=dct)
                dct.setdefault(total % 2, []).append(total)
                total -= 1
            return len(dct[0])

        assert f(100) == 50
        res = self.meta_interp(f, [100], listops=True)
        assert res == 50
        self.check_resops(new=0, new_with_vtable=0)

    def test_dict_as_counter(self):
        if type(self.newdict()) is not dict:
            py.test.skip("this is an r_dict test")
        myjitdriver = JitDriver(greens = [], reds = ['total', 'dct'])
        def key(x):
            return x % 2
        def eq(x, y):
            return (x % 2) == (y % 2)

        def f(n):
            dct = objectmodel.r_dict(eq, key)
            total = n
            while total:
                myjitdriver.jit_merge_point(total=total, dct=dct)
                dct[total] = dct.get(total, 0) + 1
                total -= 1
            return dct[0]

        assert f(100) == 50
        res = self.meta_interp(f, [100], listops=True)
        assert res == 50
        self.check_resops(int_mod=2) # key + eq, but cached

    def test_repeated_lookup(self):
        if type(self.newdict()) is not dict:
            py.test.skip("this is an r_dict test")
        myjitdriver = JitDriver(greens = [], reds = ['n', 'd'])
        class Wrapper(object):
            _immutable_fields_ = ["value"]
            def __init__(self, value):
                self.value = value
        def eq_func(a, b):
            return a.value == b.value
        def hash_func(x):
            return objectmodel.compute_hash(x.value)

        def f(n):
            d = None
            while n > 0:
                myjitdriver.jit_merge_point(n=n, d=d)
                d = objectmodel.r_dict(eq_func, hash_func)
                y = Wrapper(str(n))
                d[y] = n - 1
                n = d[y]
            return d[Wrapper(str(n + 1))]

        res = self.meta_interp(f, [100], listops=True)
        assert res == f(50)
        self.check_resops({'new_array': 2, 'getfield_gc': 2,
                           'guard_true': 2, 'jump': 1,
                           'new_with_vtable': 2, 'getinteriorfield_gc': 2,
                           'setfield_gc': 6, 'int_gt': 2, 'int_sub': 2,
                           'call': 10, 'int_and': 2,
                           'guard_no_exception': 8, 'new': 2,
                           'guard_false': 2, 'int_is_true': 2})

    def test_unrolling_of_dict_iter(self):
        driver = JitDriver(greens = [], reds = ['n'])

        def f(n):
            while n > 0:
                driver.jit_merge_point(n=n)
                d = self.newdict()
                d[1] = 1
                for elem in d:
                    n -= elem
            return n

        res = self.meta_interp(f, [10], listops=True)
        assert res == 0
        self.check_simple_loop({'int_sub': 1, 'int_gt': 1, 'guard_true': 1,
                                'jump': 1})


class TestLLtype(DictTests, LLJitMixin):
    pass

class TestLLOrderedDict(DictTests, LLJitMixin):
    @staticmethod
    def newdict():
        return OrderedDict()

    def test_dict_is_ordered(self):
        def fn(n):
            d = OrderedDict()
            d[3] = 5
            d[n] = 9
            d[2] = 6
            d[1] = 4
            lst = d.items()
            assert len(lst) == 4
            return (    lst[0][0] +       10*lst[0][1] +
                    100*lst[1][0] +     1000*lst[1][1] +
                  10000*lst[3][0] +   100000*lst[2][1] +
                1000000*lst[2][0] + 10000000*lst[3][1])

        res = self.interp_operations(fn, [0])
        assert res == fn(0)

    def test_unrolling_of_dict_iter(self):
        py.test.skip("XXX fix me: ordereddict generates a mess for now")
