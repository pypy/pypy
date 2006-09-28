import py
from pypy.rpython.lltypesystem import lltype
from pypy.jit.timeshifter.test.test_timeshift import TimeshiftingTests
from pypy.jit.timeshifter.test.test_timeshift import P_NOVIRTUAL
from pypy.rpython.objectmodel import hint


class TestPromotion(TimeshiftingTests):

    def test_simple_promotion(self):
        def ll_two(k):
            return (k+1)*2
        def ll_function(n):
            k = hint(n, promote=True)
            k = ll_two(k)
            return hint(k, variable=True)
        ll_function._global_merge_points_ = True

        # easy case: no promotion needed
        res = self.timeshift(ll_function, [20], [0])
        assert res == 42
        self.check_insns({})

        # the real test: with promotion
        res = self.timeshift(ll_function, [20], [])
        assert res == 42
        self.check_insns(int_add=0, int_mul=0)

    def test_many_promotions(self):
        def ll_two(k):
            return k*k
        def ll_function(n, total):
            while n > 0:
                k = hint(n, promote=True)
                k = ll_two(k)
                total += hint(k, variable=True)
                n -= 1
            return total
        ll_function._global_merge_points_ = True

        res = self.timeshift(ll_function, [10, 0], [], policy=P_NOVIRTUAL)
        assert res == ll_function(10, 0)
        self.check_insns(int_add=10, int_mul=0)

##    def test_method_call(self):
##        class Base(object):
##            pass
##        class Int(Base):
##            def __init__(self, n):
##                self.n = n
##            def double(self):
##                return Int(self.n * 2)
##        class Str(Base):
##            def __init__(self, s):
##                self.s = s
##            def double(self):
##                return Str(self.s + self.s)
