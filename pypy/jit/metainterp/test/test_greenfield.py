from pypy.jit.metainterp.test.support import LLJitMixin, OOJitMixin
from pypy.rlib.jit import JitDriver


class GreenFieldsTests:

    def test_green_field_1(self):
        myjitdriver = JitDriver(greens=['ctx.x'], reds=['ctx'])
        class Ctx(object):
            _immutable_fields_ = ['x']
            def __init__(self, x, y):
                self.x = x
                self.y = y
        def f(x, y):
            ctx = Ctx(x, y)
            while 1:
                myjitdriver.can_enter_jit(ctx=ctx)
                myjitdriver.jit_merge_point(ctx=ctx)
                ctx.y -= 1
                if ctx.y < 0:
                    return ctx.y
        def g(y):
            return f(5, y) + f(6, y)
        #
        res = self.meta_interp(g, [7])
        assert res == -2
        self.check_trace_count(2)
        self.check_resops(guard_value=0)

    def test_green_field_2(self):
        myjitdriver = JitDriver(greens=['ctx.x'], reds=['ctx'])
        class Ctx(object):
            _immutable_fields_ = ['x']
            def __init__(self, x, y):
                self.x = x
                self.y = y
        def f(x, y):
            ctx = Ctx(x, y)
            while 1:
                myjitdriver.can_enter_jit(ctx=ctx)
                myjitdriver.jit_merge_point(ctx=ctx)
                ctx.y -= 1
                if ctx.y < 0:
                    pass     # to just make two paths
                if ctx.y < -10:
                    return ctx.y
        def g(y):
            return f(5, y) + f(6, y)
        #
        res = self.meta_interp(g, [7])
        assert res == -22
        self.check_trace_count(6)
        self.check_resops(guard_value=0)


class TestLLtypeGreenFieldsTests(GreenFieldsTests, LLJitMixin):
    pass

class TestOOtypeGreenFieldsTests(GreenFieldsTests, OOJitMixin):
   pass
