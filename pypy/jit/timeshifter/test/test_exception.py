import py
from pypy.rpython.lltypesystem import lltype
from pypy.jit.timeshifter.test.test_timeshift import TimeshiftingTests
from pypy.jit.timeshifter.test.test_timeshift import P_NOVIRTUAL
from pypy.jit.timeshifter.test.test_vlist import P_OOPSPEC


class TestException(TimeshiftingTests):

    def test_exception_check_melts_away(self):
        def ll_two(x):
            if x == 0:
                raise ValueError
            return x-1
        def ll_function(y):
            return ll_two(y) + 40

        res = self.timeshift(ll_function, [3], [0], policy=P_NOVIRTUAL)
        assert res == 42
        self.check_insns({})

    def test_propagate_exception(self):
        S = lltype.Struct('S', ('flag', lltype.Signed))
        s = lltype.malloc(S, immortal=True)
        def ll_two(x):
            if x == 0:
                raise ValueError
            return x+7
        def ll_function(y):
            res = ll_two(y)
            s.flag = 1
            return res

        s.flag = 0
        self.timeshift_raises(ValueError,
                              ll_function, [0], [], policy=P_NOVIRTUAL)
        assert s.flag == 0

        s.flag = 0
        self.timeshift_raises(ValueError,
                              ll_function, [0], [0], policy=P_NOVIRTUAL)
        assert s.flag == 0

        s.flag = 0
        res = self.timeshift(ll_function, [17], [0], policy=P_NOVIRTUAL)
        assert res == 24
        if self.__class__ is TestException:   # no chance to work with genc
            assert s.flag == 1
        self.check_insns({'setfield': 1})

    def test_catch(self):
        def ll_two(x):
            if x == 0:
                raise ValueError
            return x+7
        def ll_function(y):
            try:
                return ll_two(y)
            except ValueError:
                return 42

        res = self.timeshift(ll_function, [0], [], policy=P_NOVIRTUAL)
        assert res == 42

        res = self.timeshift(ll_function, [0], [0], policy=P_NOVIRTUAL)
        assert res == 42

        res = self.timeshift(ll_function, [17], [0], policy=P_NOVIRTUAL)
        assert res == 24
        self.check_insns({})

    def test_catch_from_outside(self):
        def ll_function(x):
            lst = [5]
            if x:
                lst.append(x)
            # 'lst' is forced at this point
            try:
                return lst[1] * 2   # direct_call to ll_getitem
            except IndexError:
                return -11

        res = self.timeshift(ll_function, [0], [], policy=P_OOPSPEC)
        assert res == -11

        res = self.timeshift(ll_function, [0], [0], policy=P_OOPSPEC)
        assert res == -11

        res = self.timeshift(ll_function, [17], [0], policy=P_OOPSPEC)
        assert res == 34

    def test_exception_from_virtual(self):
        def ll_function(n):
            lst = []
            lst.append(5)
            try:
                return lst[n]   # direct_call to ll_getitem
            except IndexError:
                return -11

        res = self.timeshift(ll_function, [2], [0], policy=P_OOPSPEC)
        assert res == -11

        res = self.timeshift(ll_function, [0], [0], policy=P_OOPSPEC)
        assert res == 5

        # the next case degenerates anyway
        res = self.timeshift(ll_function, [2], [], policy=P_OOPSPEC)
        assert res == -11

    def test_exception_escapes(self):
        def ll_function(n):
            if n < 0:
                raise ValueError
            return n * 3

        res = self.timeshift(ll_function, [2], [], policy=P_OOPSPEC)
        assert res == 6

        self.timeshift_raises(ValueError,
                              ll_function, [-3], [], policy=P_OOPSPEC)

        self.timeshift_raises(ValueError,
                              ll_function, [-3], [0], policy=P_OOPSPEC)

    def test_raise_or_return_virtual(self):
        class A:
            def __init__(self, n):
                self.n = n
        def g(x):
            if x < 3:
                raise ValueError
            return A(x)
        def ll_function(n):
            a = g(n)
            return a.n

        res = self.timeshift(ll_function, [5], [], policy=P_NOVIRTUAL)
        assert res == 5
        self.check_insns(malloc=0)

    def test_not_segregated_malloc_exception_path(self):
        def help(l, x):
            l.append("x is %s" % chr(x))

        def ll_function(x):
            l = []
            help(l, x)
            return len(l)+x

        res = self.timeshift(ll_function, [5], [], policy=P_OOPSPEC)
        res == 6
        self.check_oops(newlist=0)
