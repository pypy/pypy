import py
from pypy.rlib.jit import JitDriver
from pypy.jit.codewriter.policy import StopAtXPolicy
from pypy.rpython.ootypesystem import ootype
from pypy.jit.metainterp.test.test_basic import LLJitMixin, OOJitMixin


class StringTests:
    def test_eq_residual(self):
        jitdriver = JitDriver(greens = [], reds = ['n', 'i', 's'])
        global_s = "hello"
        def f(n, b, s):
            if b:
                s += "ello"
            else:
                s += "allo"
            i = 0
            while n > 0:
                jitdriver.can_enter_jit(s=s, n=n, i=i)
                jitdriver.jit_merge_point(s=s, n=n, i=i)
                n -= 1 + (s == global_s)
                i += 1
            return i
        res = self.meta_interp(f, [10, True, 'h'], listops=True)
        assert res == 5
        self.check_loops(**{self.CALL: 1, self.CALL_PURE: 0})

    def test_eq_folded(self):
        jitdriver = JitDriver(greens = ['s'], reds = ['n', 'i'])
        global_s = "hello"
        def f(n, b, s):
            if b:
                s += "ello"
            else:
                s += "allo"
            i = 0
            while n > 0:
                jitdriver.can_enter_jit(s=s, n=n, i=i)
                jitdriver.jit_merge_point(s=s, n=n, i=i)
                n -= 1 + (s == global_s)
                i += 1
            return i
        res = self.meta_interp(f, [10, True, 'h'], listops=True)
        assert res == 5
        self.check_loops(**{self.CALL: 0, self.CALL_PURE: 0})

    def test_newstr(self):
        jitdriver = JitDriver(greens = [], reds = ['n', 'm'])
        def f(n, m):
            while True:
                jitdriver.can_enter_jit(m=m, n=n)
                jitdriver.jit_merge_point(m=m, n=n)
                bytecode = 'adlfkj' + chr(n)
                res = bytecode[n]
                m -= 1
                if m < 0:
                    return ord(res)
        res = self.meta_interp(f, [6, 10])
        assert res == 6

    def test_newunicode(self):
        jitdriver = JitDriver(greens = [], reds = ['n', 'm'])
        def f(n, m):
            while True:
                jitdriver.can_enter_jit(m=m, n=n)
                jitdriver.jit_merge_point(m=m, n=n)
                bytecode = u'adlfkj' + unichr(n)
                res = bytecode[n]
                m -= 1
                if m < 0:
                    return ord(res)
        res = self.meta_interp(f, [6, 10])
        assert res == 6

class TestOOtype(StringTests, OOJitMixin):
    CALL = "oosend"
    CALL_PURE = "oosend_pure"

class TestLLtype(StringTests, LLJitMixin):
    CALL = "call"
    CALL_PURE = "call_pure"
