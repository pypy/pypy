from pypy.rlib.rarithmetic import r_longlong, r_uint, intmask
from pypy.jit.metainterp.test.test_basic import LLJitMixin

class WrongResult(Exception):
    pass

def compare(xll, highres, lores):
    if intmask(xll) != lores:
        raise WrongResult
    if intmask(xll >> 32) != highres:
        raise WrongResult


class LongLongTests:

    def test_long_long_1(self):
        def g(n, m, o, p):
            # On 64-bit platforms, long longs == longs.  On 32-bit platforms,
            # this function should be either completely marked as residual
            # (with supports_longlong==False), or be compiled as a
            # sequence of residual calls (with long long arguments).
            n = r_longlong(n)
            m = r_longlong(m)
            return intmask((n*m + p) // o)
        def f(n, m, o, p):
            return g(n, m, o, p) // 3
        #
        res = self.interp_operations(f, [1000000000, 90, 91, -17171],
                                     supports_longlong=False)
        assert res == ((1000000000 * 90 - 17171) // 91) // 3
        #
        res = self.interp_operations(f, [1000000000, 90, 91, -17171],
                                     supports_longlong=True)
        assert res == ((1000000000 * 90 - 17171) // 91) // 3

    def test_simple_ops(self):
        def f(n1, n2, m1, m2):
            # n == -30000000000000, m == -20000000000
            n = (r_longlong(n1) << 32) | r_longlong(n2)
            m = (r_longlong(m1) << 32) | r_longlong(m2)
            compare(n, -6985, 346562560)
            compare(m, -5, 1474836480)
            if not n: raise WrongResult
            if n-n: raise WrongResult
            compare(-n, 6984, -346562560)
            compare(~n, 6984, -346562561)
            compare(n + m, -6990, 1821399040)
            compare(n - m, -6981, -1128273920)
            compare(n * (-3), 20954, -1039687680)
            compare((-4) * m, 18, -1604378624)
            return 1
        self.interp_operations(f, [-6985, 346562560, -5, 1474836480])

    def test_compare_ops(self):
        def f(n1, n2):
            # n == -30000000000000
            n = (r_longlong(n1) << 32) | r_longlong(n2)
            o = n + 2000000000
            compare(o, -6985, -1948404736)
            compare(n <  o, 0, 1)     # low word differs
            compare(n <= o, 0, 1)
            compare(o <  n, 0, 0)
            compare(o <= n, 0, 0)
            compare(n >  o, 0, 0)
            compare(n >= o, 0, 0)
            compare(o >  n, 0, 1)
            compare(o >= n, 0, 1)
            p = -o
            compare(n <  p, 0, 1)     # high word differs
            compare(n <= p, 0, 1)
            compare(p <  n, 0, 0)
            compare(p <= n, 0, 0)
            compare(n >  p, 0, 0)
            compare(n >= p, 0, 0)
            compare(p >  n, 0, 1)
            compare(p >= n, 0, 1)
            return 1
        self.interp_operations(f, [-6985, 346562560])

    def test_long_long_field(self):
        from pypy.rlib.rarithmetic import r_longlong, intmask
        class A:
            pass
        def g(a, n, m):
            a.n = r_longlong(n)
            a.m = r_longlong(m)
            a.n -= a.m
            return intmask(a.n)
        def f(n, m):
            return g(A(), n, m)
        #
        res = self.interp_operations(f, [2147483647, -21474],
                                     supports_longlong=False)
        assert res == intmask(2147483647 + 21474)
        #
        res = self.interp_operations(f, [2147483647, -21474],
                                     supports_longlong=True)
        assert res == intmask(2147483647 + 21474)


class TestLLtype(LongLongTests, LLJitMixin):
    pass
