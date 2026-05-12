from rpython.rlib.jit import JitDriver, set_param
from rpython.jit.metainterp.test.support import LLJitMixin


class NumericThresholdTests:

    def test_all_int_reds_compile_at_numeric_threshold(self):
        # Loop with only integer reds should compile after numeric_threshold
        # iterations even when n < the normal threshold.
        myjitdriver = JitDriver(greens=[], reds=['n', 'i', 'x'])

        def f(n):
            set_param(None, 'threshold', 1039)
            set_param(None, 'numeric_threshold', 100)
            i = 0
            x = 0
            while i < n:
                myjitdriver.can_enter_jit(n=n, i=i, x=x)
                myjitdriver.jit_merge_point(n=n, i=i, x=x)
                x += i
                i += 1
            return x

        # 200 is above numeric_threshold (100) but below normal threshold (1039)
        res = self.meta_interp(f, [200])
        assert res == sum(range(200))
        self.check_trace_count(1)

    def test_all_int_reds_below_numeric_threshold_no_compile(self):
        # n < numeric_threshold: the loop should NOT compile.
        myjitdriver = JitDriver(greens=[], reds=['n', 'i', 'x'])

        def f(n):
            set_param(None, 'threshold', 1039)
            set_param(None, 'numeric_threshold', 100)
            i = 0
            x = 0
            while i < n:
                myjitdriver.can_enter_jit(n=n, i=i, x=x)
                myjitdriver.jit_merge_point(n=n, i=i, x=x)
                x += i
                i += 1
            return x

        # 50 < numeric_threshold (100): no compilation expected
        res = self.meta_interp(f, [50])
        assert res == sum(range(50))
        self.check_trace_count(0)

    def test_ref_red_disqualifies_numeric_threshold(self):
        # A JitDriver that has any GC-ref red should NOT use numeric_threshold;
        # the normal threshold applies instead.
        myjitdriver = JitDriver(greens=[], reds=['n', 'i', 'obj'])

        class Obj(object):
            def __init__(self):
                self.v = 0

        def f(n):
            set_param(None, 'threshold', 1039)
            set_param(None, 'numeric_threshold', 100)
            i = 0
            obj = Obj()
            while i < n:
                myjitdriver.can_enter_jit(n=n, i=i, obj=obj)
                myjitdriver.jit_merge_point(n=n, i=i, obj=obj)
                obj.v += i
                i += 1
            return obj.v

        # 200 is above numeric_threshold but below normal threshold.
        # 'obj' is a ref red so numeric_threshold must not apply.
        res = self.meta_interp(f, [200])
        assert res == sum(range(200))
        self.check_trace_count(0)

    def test_numeric_threshold_zero_disables_feature(self):
        # numeric_threshold=0 means disabled: only normal threshold applies.
        myjitdriver = JitDriver(greens=[], reds=['n', 'i', 'x'])

        def f(n):
            set_param(None, 'threshold', 1039)
            set_param(None, 'numeric_threshold', 0)
            i = 0
            x = 0
            while i < n:
                myjitdriver.can_enter_jit(n=n, i=i, x=x)
                myjitdriver.jit_merge_point(n=n, i=i, x=x)
                x += i
                i += 1
            return x

        # 200 < 1039 and feature disabled: no compilation
        res = self.meta_interp(f, [200])
        assert res == sum(range(200))
        self.check_trace_count(0)

    def test_float_reds_also_qualify(self):
        # All-float reds are also numeric; they should benefit from
        # numeric_threshold.
        myjitdriver = JitDriver(greens=[], reds=['n', 'i', 'acc'])

        def f(n):
            set_param(None, 'threshold', 1039)
            set_param(None, 'numeric_threshold', 100)
            i = 0
            acc = 0.0
            while i < n:
                myjitdriver.can_enter_jit(n=n, i=i, acc=acc)
                myjitdriver.jit_merge_point(n=n, i=i, acc=acc)
                acc += float(i)
                i += 1
            return int(acc)

        # 200 > numeric_threshold (100): should compile
        res = self.meta_interp(f, [200])
        assert res == sum(range(200))
        self.check_trace_count(1)


class TestLLtype(NumericThresholdTests, LLJitMixin):
    pass
