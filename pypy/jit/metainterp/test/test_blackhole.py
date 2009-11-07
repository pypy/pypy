from pypy.rlib.jit import JitDriver
from pypy.jit.metainterp.test.test_basic import LLJitMixin, OOJitMixin
from pypy.jit.metainterp import pyjitpl


class BlackholeTests(object):

    def meta_interp(self, *args):
        def counting_init(frame, metainterp, jitcode, greenkey=None):
            previnit(frame, metainterp, jitcode, greenkey)
            self.seen_frames.append(jitcode.name)
        #
        previnit = pyjitpl.MIFrame.__init__.im_func
        try:
            self.seen_frames = []
            pyjitpl.MIFrame.__init__ = counting_init
            return super(BlackholeTests, self).meta_interp(*args)
        finally:
            pyjitpl.MIFrame.__init__ = previnit

    def test_calls_not_followed(self):
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        def h():
            return 42
        def g():
            return h()
        def f(n):
            while n > 0:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                n -= 1
            return g()
        res = self.meta_interp(f, [7])
        assert res == 42
        assert self.seen_frames == ['f', 'f']

    def test_indirect_calls_not_followed(self):
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        def h():
            return 42
        def g():
            return h()
        def f(n):
            while n > 0:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                n -= 1
            if n < 0:
                call = h
            else:
                call = g
            return call()
        res = self.meta_interp(f, [7])
        assert res == 42
        assert self.seen_frames == ['f', 'f']

    def test_oosends_not_followed(self):
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        class A:
            def meth(self):
                return 42
        class B(A):
            def meth(self):
                return 45
        class C(A):
            def meth(self):
                return 64
        def f(n):
            while n > 0:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                n -= 1
            if n < 0:
                x = B()
            else:
                x = C()
            return x.meth()
        res = self.meta_interp(f, [7])
        assert res == 64
        assert self.seen_frames == ['f', 'f']


class TestLLtype(BlackholeTests, LLJitMixin):
    pass

class TestOOtype(BlackholeTests, OOJitMixin):
    pass
