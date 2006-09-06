import py
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.llinterp import LLException
from pypy.jit.timeshifter.test.test_timeshift import TimeshiftingTests
from pypy.jit.timeshifter.test.test_timeshift import P_NOVIRTUAL


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
        res = self.timeshift(ll_function, [0], [], policy=P_NOVIRTUAL)
        assert res == -1
        assert s.flag == 0

        s.flag = 0
        res = self.timeshift(ll_function, [0], [0], policy=P_NOVIRTUAL)
        assert res == -1
        assert s.flag == 0

        s.flag = 0
        res = self.timeshift(ll_function, [17], [0], policy=P_NOVIRTUAL)
        assert res == 24
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
