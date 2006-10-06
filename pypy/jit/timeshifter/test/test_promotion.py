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

    def test_promote_after_yellow_call(self):
        S = lltype.GcStruct('S', ('x', lltype.Signed))
        def ll_two(k, s):
            if k > 5:
                s.x = 20*k
                return 7
            else:
                s.x = 10*k
                return 9
            
        def ll_function(n):
            s = lltype.malloc(S)
            c = ll_two(n, s)
            k = hint(s.x, promote=True)
            k += c
            return hint(k, variable=True)
        ll_function._global_merge_points_ = True

        res = self.timeshift(ll_function, [4], [], policy=P_NOVIRTUAL)
        assert res == 49
        self.check_insns(int_add=0)

    def test_promote_inside_call(self):
        def ll_two(n):
            k = hint(n, promote=True)
            k *= 17
            return hint(k, variable=True)
        def ll_function(n):
            return ll_two(n + 1) - 1
        ll_function._global_merge_points_ = True

        res = self.timeshift(ll_function, [10], [], policy=P_NOVIRTUAL)
        assert res == 186
        self.check_insns(int_add=1, int_mul=0, int_sub=0)

    def test_two_promotions(self):
        def ll_function(n, m):
            n1 = hint(n, promote=True)
            m1 = hint(m, promote=True)
            s1 = n1 + m1
            return hint(s1, variable=True)
        ll_function._global_merge_points_ = True

        res = self.timeshift(ll_function, [40, 2], [], policy=P_NOVIRTUAL)
        assert res == 42
        self.check_insns(int_add=0)

    def test_merge_then_promote(self):
        S = lltype.GcStruct('S', ('x', lltype.Signed))
        def ll_two(n):
            s = lltype.malloc(S)
            if n < 0:
                s.x = 10
            else:
                s.x = 20
            k = hint(s.x, promote=True)
            k *= 17
            return hint(k, variable=True)
        def ll_function(n):
            return ll_two(n)
        ll_function._global_merge_points_ = True

        res = self.timeshift(ll_function, [3], [], policy=P_NOVIRTUAL)
        assert res == 340
        self.check_insns(int_lt=1, int_mul=0)

    def test_vstruct_unfreeze(self):
        S = lltype.GcStruct('S', ('x', lltype.Signed))
        def ll_two(k):
            return (k+1)*2
        def ll_function(n):
            s = lltype.malloc(S)
            s.x = n
            k = hint(n, promote=True)
            k = ll_two(k)
            return hint(k, variable=True) + s.x
        ll_function._global_merge_points_ = True

        # easy case: no promotion needed
        res = self.timeshift(ll_function, [20], [0], policy=P_NOVIRTUAL)
        assert res == 62
        self.check_insns({})

        # the real test: with promotion
        res = self.timeshift(ll_function, [20], [], policy=P_NOVIRTUAL)
        assert res == 62
        self.check_insns(int_add=0, int_mul=0)

    def test_more_promotes(self):
        S = lltype.GcStruct('S', ('x', lltype.Signed), ('y', lltype.Signed))
        def ll_two(s, i, m):
            if i > 4:
                s.x += i
                return 10
            else:
                s.y = i
                return s.x + m
        def ll_three(s, k):
            k = hint(k, promote=True)
            if s.x > 6:
                k *= hint(s.y, promote=True)
                return k
            else:
                return hint(1, concrete=True)
        def ll_function(n, m):
            s = lltype.malloc(S)
            s.x = 0
            s.y = 0
            i = 0
            while i < n:
                k = ll_two(s, i, m)
                if m & 1:
                    k *= 3
                else:
                    s.y += 1
                j = ll_three(s, k)
                j = hint(j, variable=True)
                i += j
            return s.x + s.y * 17
        ll_function._global_merge_points_ = True

        res = self.timeshift(ll_function, [100, 2], [], policy=P_NOVIRTUAL)
        assert res == ll_function(100, 2)


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
