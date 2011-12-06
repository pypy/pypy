import py, sys
from pypy.jit.metainterp.test.support import LLJitMixin, OOJitMixin
from pypy.rlib.jit import JitDriver, dont_look_inside
from pypy.rlib.rarithmetic import ovfcheck, LONG_BIT, intmask
from pypy.jit.codewriter.policy import StopAtXPolicy


class ExceptionTests:

    def test_simple(self):
        def g(n):
            if n <= 0:
                raise MyError(n)
            return n - 1
        def f(n):
            try:
                return g(n)
            except MyError, e:
                return e.n + 10
        res = self.interp_operations(f, [9])
        assert res == 8
        res = self.interp_operations(f, [-99])
        assert res == -89

    def test_no_exception(self):
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        class X:
            pass
        def f(n):
            while n > 0:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                X()
                n -= 1
            return n
        res = self.meta_interp(f, [10])
        assert res == 0
        self.check_resops({'jump': 2, 'guard_true': 2,
                           'int_gt': 2, 'int_sub': 2})

    def test_bridge_from_guard_exception(self):
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        def check(n):
            if n % 2:
                raise ValueError
        
        def f(n):
            while n > 0:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                try:
                    check(n)
                    n -= 1
                except ValueError:
                    n -= 3
            return n

        res = self.meta_interp(f, [20], policy=StopAtXPolicy(check))
        assert res == f(20)
        res = self.meta_interp(f, [21], policy=StopAtXPolicy(check))
        assert res == f(21)

    def test_bridge_from_guard_no_exception(self):
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        def check(n):
            if n % 2 == 0:
                raise ValueError
        
        def f(n):
            while n > 0:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                try:
                    check(n)
                    n -= 1
                except ValueError:
                    n -= 3
            return n

        res = self.meta_interp(f, [20], policy=StopAtXPolicy(check))
        assert res == f(20)

    def test_loop(self):
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        def check(n):
            if n < 0:
                raise IndexError
        def f(n):
            try:
                while True:
                    myjitdriver.can_enter_jit(n=n)
                    myjitdriver.jit_merge_point(n=n)
                    check(n)
                    n = n - 10
            except IndexError:
                return n
        res = self.meta_interp(f, [54])
        assert res == -6

    def test_four_levels_checks(self):
        def d(n):
            if n < 0:
                raise MyError(n * 10)
        def c(n):
            d(n)
        def b(n):
            try:
                c(n)
            except IndexError:
                pass
        def a(n):
            try:
                b(n)
                return 0
            except MyError, e:
                return e.n
        def f(n):
            return a(n)
        
        res = self.interp_operations(f, [-4])
        assert res == -40

    def test_exception_from_outside(self):
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        def check(n, mode):
            if mode == 0 and n > -100:
                raise MyError(n)
            return n - 5
        def f(n):
            while n > 0:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                try:
                    check(n, 0)
                except MyError, e:
                    n = check(e.n, 1)
            return n
        assert f(53) == -2
        res = self.meta_interp(f, [53], policy=StopAtXPolicy(check))
        assert res == -2

    def test_exception_from_outside_2(self):
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        def check(n):
            if n > -100:
                raise IndexError
        def g(n):
            check(n)
        def f(n):
            while n > 0:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                try:
                    g(n)
                except IndexError:
                    n = n - 5
            return n
        res = self.meta_interp(f, [53], policy=StopAtXPolicy(check))
        assert res == -2

    def test_exception_two_cases(self):
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        class Error1(Exception): pass
        class Error2(Exception): pass
        class Error3(Exception): pass
        class Error4(Exception): pass
        def check(n):
            if n > 0:
                raise Error3
            else:
                raise Error2
        def f(n):
            while True:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                try:
                    check(n)
                except Error1:
                    pass
                except Error2:
                    break
                except Error3:
                    n = n - 5
                except Error4:
                    pass
            return n
        res = self.meta_interp(f, [53], policy=StopAtXPolicy(check))
        assert res == -2

    def test_exception_two_cases_2(self):
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        class Error1(Exception): pass
        class Error2(Exception): pass
        class Error3(Exception): pass
        class Error4(Exception): pass
        def check(n):
            if n > 0:
                raise Error3
            else:
                raise Error2
        def g(n):
            check(n)
        def f(n):
            while True:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                try:
                    g(n)
                except Error1:
                    pass
                except Error2:
                    break
                except Error3:
                    n = n - 5
                except Error4:
                    pass
            return n
        res = self.meta_interp(f, [53], policy=StopAtXPolicy(check))
        assert res == -2

    def test_exception_four_cases(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'm'])
        class Error1(Exception): pass
        class Error2(Exception): pass
        class Error3(Exception): pass
        class Error4(Exception): pass
        def check(n):
            if n % 4 == 0: raise Error1
            if n % 4 == 1: raise Error2
            if n % 4 == 2: raise Error3
            else:          raise Error4
        def f(n):
            m = 1
            while n > 0:
                myjitdriver.can_enter_jit(n=n, m=m)
                myjitdriver.jit_merge_point(n=n, m=m)
                try:
                    check(n)
                except Error1:
                    m = intmask(m * 3 + 1)
                except Error2:
                    m = intmask(m * 5 + 1)
                except Error3:
                    m = intmask(m * 7 + 1)
                except Error4:
                    m = intmask(m * 11 + 1)
                n -= 1
            return m
        res = self.meta_interp(f, [99], policy=StopAtXPolicy(check))
        assert res == f(99)

    def test_exception_later(self):
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        def check(n):
            if n < 0:
                raise MyError(n)
            return 5
        def f(n):
            try:
                while True:
                    myjitdriver.can_enter_jit(n=n)
                    myjitdriver.jit_merge_point(n=n)
                    n = n - check(n)
            except MyError, e:
                return e.n
        assert f(53) == -2
        res = self.meta_interp(f, [53], policy=StopAtXPolicy(check))
        assert res == -2

    def test_exception_and_then_no_exception(self):
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        def check(n):
            if n > 0:
                raise ValueError
            return n + 100
        def f(n):
            while True:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                try:
                    n = check(n)
                    break
                except ValueError:
                    n = n - 5
            return n
        assert f(53) == 98
        res = self.meta_interp(f, [53], policy=StopAtXPolicy(check))
        assert res == 98

    def test_raise(self):
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        def f(n):
            while True:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                if n < 0:
                    raise ValueError
                n = n - 1
        def main(n):
            try:
                f(n)
            except ValueError:
                return 132
        res = self.meta_interp(main, [13])
        assert res == 132

    def test_raise_through(self):
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        def check(n):
            if n < 0:
                raise ValueError
            return 1
        def f(n):
            while True:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                n -= check(n)
        def main(n):
            try:
                f(n)
            except ValueError:
                return 132
        res = self.meta_interp(main, [13], policy=StopAtXPolicy(check))
        assert res == 132

    def test_raise_through_wrong_exc(self):
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        def check(n):
            if n < 0:
                raise ValueError
            return 1
        def f(n):
            while True:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                try:
                    n -= check(n)
                except IndexError:
                    pass
        def main(n):
            try:
                f(n)
            except ValueError:
                return 132
        res = self.meta_interp(main, [13], policy=StopAtXPolicy(check))
        assert res == 132

    def test_raise_through_wrong_exc_2(self):
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        def check(n):
            if n < 0:
                raise ValueError
            else:
                raise IndexError
        def f(n):
            while True:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                try:
                    check(n)
                except IndexError:
                    n -= 1
        def main(n):
            try:
                f(n)
            except ValueError:
                return 132
        res = self.meta_interp(main, [13], policy=StopAtXPolicy(check))
        assert res == 132

    def test_int_ovf(self):
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        def f(n):
            try:
                while 1:
                    myjitdriver.can_enter_jit(n=n)
                    myjitdriver.jit_merge_point(n=n)
                    n = ovfcheck(n * -3)
            except OverflowError:
                return n
        expected = f(1)
        res = self.meta_interp(f, [1])
        assert res == expected


    def test_div_ovf(self):
        def f(x, y):
            try:
                return ovfcheck(x/y)
            except OverflowError:
                return 42

        res = self.interp_operations(f, [-sys.maxint-1, -1])
        assert res == 42

    def test_int_ovf_common(self):
        import sys
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        def f(n):
            while 1:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                try:
                    n = ovfcheck(n + sys.maxint)
                except OverflowError:
                    n -= 1
                else:
                    return n - 2000
        res = self.meta_interp(f, [10], repeat=7)
        assert res == sys.maxint - 2000

    def test_int_mod_ovf_zer(self):
        myjitdriver = JitDriver(greens = [], reds = ['i', 'x', 'y'])
        def f(x, y):
            i = 0
            while i < 10:
                myjitdriver.can_enter_jit(x=x, y=y, i=i)
                myjitdriver.jit_merge_point(x=x, y=y, i=i)
                try:
                    ovfcheck(i%x)
                    i += 1
                except ZeroDivisionError:
                    i += 1
                except OverflowError:
                    i += 2
            return 0

        self.meta_interp(f, [0, 0])
        self.meta_interp(f, [1, 0])

    def test_int_lshift_ovf(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'x', 'y', 'm'])
        def f(x, y, n):
            m = 0
            while n < 100:
                myjitdriver.can_enter_jit(n=n, x=x, y=y, m=m)
                myjitdriver.jit_merge_point(n=n, x=x, y=y, m=m)
                y += 1
                y &= (LONG_BIT-1)
                try:
                    ovfcheck(x<<y)
                except OverflowError:
                    m += 1
                n += 1
            return m

        res = self.meta_interp(f, [1, 1, 0], enable_opts='')
        assert res == f(1, 1, 0)
        res = self.meta_interp(f, [809644098, 16, 0],
                               enable_opts='')
        assert res == f(809644098, 16, 0)

    def test_int_neg_ovf(self):
        import sys
        myjitdriver = JitDriver(greens = [], reds = ['n', 'y', 'm'])
        def f(y, n):
            m = 0
            while n < 115:
                myjitdriver.can_enter_jit(n=n, y=y, m=m)
                myjitdriver.jit_merge_point(n=n, y=y, m=m)
                y -= 1
                try:
                    ovfcheck(-y)
                except OverflowError:
                    m += 1
                    y += 1
                n += 1
            return m

        res = self.meta_interp(f, [-sys.maxint-1+100, 0],
                               enable_opts='')
        assert res == 16

    def test_reraise_through_portal(self):
        jitdriver = JitDriver(greens = [], reds = ['n'])

        class SomeException(Exception):
            pass
        
        def portal(n):
            while n > 0:
                jitdriver.can_enter_jit(n=n)
                jitdriver.jit_merge_point(n=n)
                if n == 10:
                    raise SomeException
                n -= 1

        def f(n):
            try:
                portal(n)
            except SomeException, e:
                return 3
            return 2

        res = self.meta_interp(f, [100])
        assert res == 3

    def test_bridge_from_interpreter_exc(self):
        mydriver = JitDriver(reds = ['n'], greens = [])

        def f(n):
            while n > 0:
                mydriver.can_enter_jit(n=n)
                mydriver.jit_merge_point(n=n)
                n -= 2
            raise MyError(n)
        def main(n):
            try:
                f(n)
            except MyError, e:
                return e.n

        res = self.meta_interp(main, [41], repeat=7)
        assert res == -1
        self.check_tree_loop_count(2)      # the loop and the entry path
        # we get:
        #    ENTER    - compile the new loop and the entry bridge
        #    ENTER    - compile the leaving path (raising MyError)
        self.check_enter_count(2)


    def test_bridge_from_interpreter_exc_2(self):
        mydriver = JitDriver(reds = ['n'], greens = [])

        def x(n):
            if n == 1:
                raise MyError(n)
        
        def f(n):
            try:
                while n > 0:
                    mydriver.can_enter_jit(n=n)
                    mydriver.jit_merge_point(n=n)
                    x(n)
                    n -= 1
            except MyError:
                z()
        
        def z():
            raise ValueError

        def main(n):
            try:
                f(n)
                return 3
            except MyError, e:
                return e.n
            except ValueError:
                return 8

        res = self.meta_interp(main, [41], repeat=7, policy=StopAtXPolicy(x),
                               enable_opts='')
        assert res == 8

    def test_overflowerror_escapes(self):
        def g(x):
            return ovfcheck(x + 1)
        def f(x):
            try:
                return g(x)
            except Exception, e:
                if isinstance(e, OverflowError):
                    return -42
                raise
        res = self.interp_operations(f, [sys.maxint])
        assert res == -42

    def test_bug_1(self):
        def h(i):
            if i > 10:
                raise ValueError
            if i > 5:
                raise KeyError
            return 5
        def g(i):
            try:
                return h(i)
            except ValueError:
                return 21
        def f(i):
            try:
                return g(i)
            except KeyError:
                return 42
        res = self.interp_operations(f, [99])
        assert res == 21

    def test_bug_exc1_noexc_exc2(self):
        myjitdriver = JitDriver(greens=[], reds=['i'])
        @dont_look_inside
        def rescall(i):
            if i < 10:
                raise KeyError
            if i < 20:
                return None
            raise ValueError
        def f(i):
            while i < 30:
                myjitdriver.can_enter_jit(i=i)
                myjitdriver.jit_merge_point(i=i)
                try:
                    rescall(i)
                except KeyError:
                    assert i < 10
                except ValueError:
                    assert i >= 20
                else:
                    assert 10 <= i < 20
                i += 1
            return i
        res = self.meta_interp(f, [0], inline=True)
        assert res == 30


class MyError(Exception):
    def __init__(self, n):
        self.n = n


class TestOOtype(ExceptionTests, OOJitMixin):
    pass

class TestLLtype(ExceptionTests, LLJitMixin):
    pass
