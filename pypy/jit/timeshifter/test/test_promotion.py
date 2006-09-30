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

    def test_multiple_portal_calls(self):
        # so far, crashes when we call timeshift() multiple times
        py.test.skip("in-progress")
        def ll_function(n):
            k = n
            if k > 5:
                k //= 2
            k = hint(k, promote=True)
            k *= 17
            return hint(k, variable=True)
        ll_function._global_merge_points_ = True

        res = self.timeshift(ll_function, [4], [], policy=P_NOVIRTUAL)
        assert res == 68
        self.check_insns(int_floordiv=1, int_mul=0)

        res = self.timeshift(ll_function, [4], [], policy=P_NOVIRTUAL)
        assert res == 68
        self.check_insns(int_floordiv=1, int_mul=0)

    def test_promote_after_call(self):
        S = lltype.GcStruct('S', ('x', lltype.Signed))
        def ll_two(k, s):
            if k > 5:
                s.x = 20
            else:
                s.x = 10
        def ll_function(n):
            s = lltype.malloc(S)
            ll_two(n, s)
            k = hint(n, promote=True)
            k *= 17
            return hint(k, variable=True) + s.x
        ll_function._global_merge_points_ = True

        res = self.timeshift(ll_function, [4], [], policy=P_NOVIRTUAL)
        assert res == 4*17 + 10
        self.check_insns(int_mul=0, int_add=1)


    def test_method_call_nonpromote(self):
        class Base(object):
            pass
        class Int(Base):
            def __init__(self, n):
                self.n = n
            def double(self):
                return Int(self.n * 2)
            def get(self):
                return self.n
        class Str(Base):
            def __init__(self, s):
                self.s = s
            def double(self):
                return Str(self.s + self.s)
            def get(self):
                return int(self.s)

        def ll_make(n):
            if n > 0:
                return Int(n)
            else:
                return Str('123')

        def ll_function(n):
            o = ll_make(n)
            return o.double().get()

        res = self.timeshift(ll_function, [5], [], policy=P_NOVIRTUAL)
        assert res == 10
        self.check_insns(indirect_call=2)

        res = self.timeshift(ll_function, [0], [], policy=P_NOVIRTUAL)
        assert res == 123123
        self.check_insns(indirect_call=2)


    def test_method_call_promote(self):
        py.test.skip("in-progress")
        class Base(object):
            pass
        class Int(Base):
            def __init__(self, n):
                self.n = n
            def double(self):
                return Int(self.n * 2)
            def get(self):
                return self.n
        class Str(Base):
            def __init__(self, s):
                self.s = s
            def double(self):
                return Str(self.s + self.s)
            def get(self):
                return ord(self.s[4])

        def ll_make(n):
            if n > 0:
                return Int(n)
            else:
                return Str('123')

        def ll_function(n):
            o = ll_make(n)
            hint(o.__class__, promote=True)
            return o.double().get()
        ll_function._global_merge_points_ = True

        res = self.timeshift(ll_function, [5], [], policy=P_NOVIRTUAL)
        assert res == 10
        self.check_insns(indirect_call=0, direct_call=1)

        res = self.timeshift(ll_function, [0], [], policy=P_NOVIRTUAL)
        assert res == ord('2')
        self.check_insns(indirect_call=0, direct_call=1)
