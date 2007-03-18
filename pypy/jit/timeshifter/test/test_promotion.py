import py
from pypy.rpython.lltypesystem import lltype
from pypy.jit.timeshifter.test.test_timeshift import TimeshiftingTests
from pypy.jit.timeshifter.test.test_timeshift import StopAtXPolicy
from pypy.jit.timeshifter.test.test_timeshift import P_NOVIRTUAL
from pypy.jit.timeshifter.test.test_vlist import P_OOPSPEC
from pypy.rlib.objectmodel import hint
from pypy.rpython.module.support import LLSupport

class TestPromotion(TimeshiftingTests):

    def test_simple_promotion(self):
        def ll_two(k):
            return (k+1)*2
        def ll_function(n):
            hint(None, global_merge_point=True)
            k = hint(n, promote=True)
            k = ll_two(k)
            return hint(k, variable=True)

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
                hint(None, global_merge_point=True)
                k = hint(n, promote=True)
                k = ll_two(k)
                total += hint(k, variable=True)
                n -= 1
            return total

        res = self.timeshift(ll_function, [10, 0], [], policy=P_NOVIRTUAL)
        assert res == ll_function(10, 0)
        self.check_insns(int_add=10, int_mul=0)

    def test_promote_after_call(self):
        S = lltype.GcStruct('S', ('x', lltype.Signed))
        def ll_two(k, s):
            if k > 5:
                s.x = 20
            else:
                s.x = 10
        def ll_function(n):
            hint(None, global_merge_point=True)
            s = lltype.malloc(S)
            ll_two(n, s)
            k = hint(n, promote=True)
            k *= 17
            return hint(k, variable=True) + s.x

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
            hint(None, global_merge_point=True)
            s = lltype.malloc(S)
            c = ll_two(n, s)
            k = hint(s.x, promote=True)
            k += c
            return hint(k, variable=True)

        res = self.timeshift(ll_function, [4], [], policy=P_NOVIRTUAL)
        assert res == 49
        self.check_insns(int_add=0)

    def test_promote_inside_call(self):
        def ll_two(n):
            k = hint(n, promote=True)
            k *= 17
            return hint(k, variable=True)
        def ll_function(n):
            hint(None, global_merge_point=True)
            return ll_two(n + 1) - 1

        res = self.timeshift(ll_function, [10], [], policy=P_NOVIRTUAL)
        assert res == 186
        self.check_insns(int_add=1, int_mul=0, int_sub=0)

    def test_two_promotions(self):
        def ll_function(n, m):
            hint(None, global_merge_point=True)
            n1 = hint(n, promote=True)
            m1 = hint(m, promote=True)
            s1 = n1 + m1
            return hint(s1, variable=True)

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
            hint(None, global_merge_point=True)
            return ll_two(n)

        res = self.timeshift(ll_function, [3], [], policy=P_NOVIRTUAL)
        assert res == 340
        self.check_insns(int_lt=1, int_mul=0)

    def test_vstruct_unfreeze(self):
        S = lltype.GcStruct('S', ('x', lltype.Signed))
        def ll_two(k):
            return (k+1)*2
        def ll_function(n):
            hint(None, global_merge_point=True)
            s = lltype.malloc(S)
            s.x = n
            k = hint(n, promote=True)
            k = ll_two(k)
            return hint(k, variable=True) + s.x

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
                hint(None, global_merge_point=True)
                k = ll_two(s, i, m)
                if m & 1:
                    k *= 3
                else:
                    s.y += 1
                j = ll_three(s, k)
                j = hint(j, variable=True)
                i += j
            return s.x + s.y * 17

        res = self.timeshift(ll_function, [100, 2], [], policy=P_NOVIRTUAL)
        assert res == ll_function(100, 2)

    def test_mixed_merges(self):
        def ll_function(x, y, z, k):
            if x:
               while x > 0:
                   hint(None, global_merge_point=True)
                   if y < 0:
                       y = -y
                       hint(None, reverse_split_queue=True)
                       return y
                   else:
                       n = 10
                       while n:
                           n -= 1
                       y = hint(y, promote=True)
                       y *= 2
                       y = hint(y, variable=True)
                   x -= 1
            else:
                if z < 0:
                    z = -z
                else:
                    k = 3
                y = y + z*k
            return y

        res = self.timeshift(ll_function, [6, 3, 2, 2], [3], policy=P_NOVIRTUAL)

        assert res == ll_function(6, 3, 2, 2)

    def test_green_across_global_mp(self):
        def ll_function(n1, n2, n3, n4, total):
            while n2:
                hint(None, global_merge_point=True)
                total += n3
                hint(n4, concrete=True)
                hint(n3, concrete=True)
                hint(n2, concrete=True)
                hint(n1, concrete=True)
                n2 -= 1
            return total
        void = lambda s: None
        ll_function.convert_arguments = [void, int, int, void, int]

        res = self.timeshift(ll_function, [None, 4, 3, None, 100], [0],
                             policy=P_NOVIRTUAL)
        assert res == ll_function(None, 4, 3, None, 100)

    def test_remembers_across_mp(self):
        def ll_function(x, flag):
            hint(None, global_merge_point=True)
            hint(x.field, promote=True)
            m = x.field
            if flag:
                m += 1 * flag
            else:
                m += 2 + flag
            hint(x.field, promote=True)
            return m + x.field

        S = lltype.GcStruct('S', ('field', lltype.Signed),
                            hints={'immutable': True})

        def struct_S(string):
            s = lltype.malloc(S)
            s.field = int(string)
            return s
        ll_function.convert_arguments = [struct_S, int]

        res = self.timeshift(ll_function, ["20", 0], [], policy=P_NOVIRTUAL)
        assert res == 42
        self.check_flexswitches(1)

    def test_virtual_list_copy(self):
        def ll_function(x, y):
            hint(None, global_merge_point=True)
            l = [y] * x
            size = len(l)
            size = hint(size, promote=True)
            vl = [0] * size
            i = 0
            while i < size:
                hint(i, concrete=True)
                vl[i] = l[i]
                i = i + 1
            return len(vl)
        res = self.timeshift(ll_function, [6, 5], [], policy=P_OOPSPEC)
        assert res == 6
        self.check_oops(**{'newlist': 1, 'list.len': 1})
            
    def test_promote_bug_1(self):
        def ll_function(x, y, z):
            a = 17
            while True:
                hint(None, global_merge_point=True)
                y += 1

                if a != 17:
                    z = -z
                
                if z > 0:
                    b = 1 - z
                else:
                    b = 2
                y = -y
                if b == 2:
                    hint(z, promote=True)
                    return y + z + a
                a += z

        assert ll_function(1, 5, 8) == 22
        res = self.timeshift(ll_function, [1, 5, 8], [],
                             policy=P_NOVIRTUAL)
        assert res == 22

    def test_raise_result_mixup(self):
        def w(x):
            pass
        class E(Exception):
            def __init__(self, x):
                self.x = x
        def o(x):
            if x < 0:
                e = E(x)
                w(e)
                raise e                
            return x
        def ll_function(c, x):
            i = 0
            while True:
                hint(None, global_merge_point=True)
                op = c[i]
                hint(op, concrete=True)
                if op == 'e':
                    break
                elif op == 'o':
                    x = o(x)
                    x = hint(x, promote=True)
                    i = x
            r = hint(i, variable=True)
            return r
        ll_function.convert_arguments = [LLSupport.to_rstr, int]
        
        assert ll_function("oe", 1) == 1

        res = self.timeshift(ll_function, ["oe", 1], [],
                             policy=StopAtXPolicy(w))
        res == 1

    def test_raise_result_mixup_some_more(self):
        def w(x):
            if x > 1000:
                return None
            else:
                return E(x)
        class E(Exception):
            def __init__(self, x):
                self.x = x
        def o(x):
            if x < 0:
                e = w(x)
                raise e                
            return x
        def ll_function(c, x):
            i = 0
            while True:
                hint(None, global_merge_point=True)
                op = c[i]
                hint(op, concrete=True)
                if op == 'e':
                    break
                elif op == 'o':
                    x = o(x)
                    x = hint(x, promote=True)
                    i = x
            r = hint(i, variable=True)
            return r
        ll_function.convert_arguments = [LLSupport.to_rstr, int]
        
        assert ll_function("oe", 1) == 1

        res = self.timeshift(ll_function, ["oe", 1], [],
                             policy=StopAtXPolicy(w))
        res == 1

    def test_promote_in_yellow_call(self):
        def ll_two(n):
            n = hint(n, promote=True)
            return n + 2
            
        def ll_function(n):
            hint(None, global_merge_point=True)
            c = ll_two(n)
            return hint(c, variable=True)

        res = self.timeshift(ll_function, [4], [], policy=P_NOVIRTUAL)
        assert res == 6
        self.check_insns(int_add=0)

    def test_two_promotions_in_call(self):
        def ll_two(n, m):
            if n < 1:
                return m
            else:
                return n

        def ll_one(n, m):
            n = ll_two(n, m)
            n = hint(n, promote=True)
            m = hint(m, promote=True)
            return hint(n + m, variable=True)

        def ll_function(n, m):
            hint(None, global_merge_point=True)
            c = ll_one(n, m)
            return c

        res = self.timeshift(ll_function, [4, 7], [], policy=P_NOVIRTUAL)
        assert res == 11
        self.check_insns(int_add=0)
