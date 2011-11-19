from pypy.jit.metainterp.test.support import LLJitMixin
from pypy.module.micronumpy import interp_boxes, interp_ufuncs, signature
from pypy.module.micronumpy.compile import (FakeSpace,
    FloatObject, IntObject, numpy_compile, BoolObject)
from pypy.module.micronumpy.interp_numarray import (BaseArray, SingleDimArray,
    SingleDimSlice)
from pypy.rlib.nonconst import NonConstant
from pypy.rpython.annlowlevel import llstr, hlstr
from pypy.jit.metainterp.warmspot import reset_stats
from pypy.jit.metainterp import pyjitpl

import py


class TestNumpyJIt(LLJitMixin):
    graph = None
    interp = None

    def run(self, code):
        space = FakeSpace()

        def f(code):
            interp = numpy_compile(hlstr(code))
            interp.run(space)
            res = interp.results[-1]
            assert isinstance(res, BaseArray)
            w_res = res.eval(0)
            if isinstance(w_res, interp_boxes.W_BoolBox):
                return float(w_res.value)
            elif isinstance(w_res, interp_boxes.W_Float64Box):
                return w_res.value
            elif isinstance(w_res, interp_boxes.W_LongBox):
                return w_res.value
            else:
                return -42.

        if self.graph is None:
            interp, graph = self.meta_interp(f, [llstr(code)],
                                             listops=True,
                                             backendopt=True,
                                             graph_and_interp_only=True)
            self.__class__.interp = interp
            self.__class__.graph = graph

        reset_stats()
        pyjitpl._warmrunnerdesc.memory_manager.alive_loops.clear()
        return self.interp.eval_graph(self.graph, [llstr(code)])

    def test_add(self):
        result = self.run("""
        a = |30|
        b = a + a
        b -> 3
        """)
        self.check_loops({'getinteriorfield_raw': 2, 'float_add': 1,
                          'setinteriorfield_raw': 1, 'int_add': 1,
                          'int_lt': 1, 'guard_true': 1, 'jump': 1})
        assert result == 3 + 3

    def test_floatadd(self):
        result = self.run("""
        a = |30| + 3
        a -> 3
        """)
        assert result == 3 + 3
        self.check_loops({"getinteriorfield_raw": 1, "float_add": 1,
                          "setinteriorfield_raw": 1, "int_add": 1,
                          "int_lt": 1, "guard_true": 1, "jump": 1})

    def test_sum(self):
        result = self.run("""
        a = |30|
        b = a + a
        sum(b)
        """)
        assert result == 2 * sum(range(30))
        self.check_loops({"getinteriorfield_raw": 2, "float_add": 2,
                          "int_add": 1,
                          "int_lt": 1, "guard_true": 1, "jump": 1})

    def test_prod(self):
        result = self.run("""
        a = |30|
        b = a + a
        prod(b)
        """)
        expected = 1
        for i in range(30):
            expected *= i * 2
        assert result == expected
        self.check_loops({"getinteriorfield_raw": 2, "float_add": 1,
                          "float_mul": 1, "int_add": 1,
                          "int_lt": 1, "guard_true": 1, "jump": 1})

    def test_max(self):
        py.test.skip("broken, investigate")
        result = self.run("""
        a = |30|
        a[13] = 128
        b = a + a
        max(b)
        """)
        assert result == 256
        self.check_loops({"getinteriorfield_raw": 2, "float_add": 1,
                          "float_mul": 1, "int_add": 1,
                          "int_lt": 1, "guard_true": 1, "jump": 1})

    def test_min(self):
        py.test.skip("broken, investigate")
        result = self.run("""
        a = |30|
        a[15] = -12
        b = a + a
        min(b)
        """)
        assert result == -24
        self.check_loops({"getinteriorfield_raw": 2, "float_add": 1,
                          "float_mul": 1, "int_add": 1,
                          "int_lt": 1, "guard_true": 1, "jump": 1})

    def test_any(self):
        result = self.run("""
        a = [0,0,0,0,0,0,0,0,0,0,0]
        a[8] = -12
        b = a + a
        any(b)
        """)
        assert result == 1
        self.check_loops({"getinteriorfield_raw": 2, "float_add": 1,
                          "float_ne": 1, "int_add": 1,
                          "int_lt": 1, "guard_true": 1, "jump": 1,
                          "guard_false": 1})

    def test_already_forced(self):
        result = self.run("""
        a = |30|
        b = a + 4.5
        b -> 5 # forces
        c = b * 8
        c -> 5
        """)
        assert result == (5 + 4.5) * 8
        # This is the sum of the ops for both loops, however if you remove the
        # optimization then you end up with 2 float_adds, so we can still be
        # sure it was optimized correctly.
        self.check_loops({"getinteriorfield_raw": 2, "float_mul": 1, "float_add": 1,
                          "setinteriorfield_raw": 2, "int_add": 2,
                          "int_lt": 2, "guard_true": 2, "jump": 2})

    def test_ufunc(self):
        result = self.run("""
        a = |30|
        b = a + a
        c = unegative(b)
        c -> 3
        """)
        assert result == -6
        self.check_loops({"getinteriorfield_raw": 2, "float_add": 1, "float_neg": 1,
                          "setinteriorfield_raw": 1, "int_add": 1,
                          "int_lt": 1, "guard_true": 1, "jump": 1,
        })

    def test_specialization(self):
        self.run("""
        a = |30|
        b = a + a
        c = unegative(b)
        c -> 3
        d = a * a
        unegative(d)
        d -> 3
        d = a * a
        unegative(d)
        d -> 3
        d = a * a
        unegative(d)
        d -> 3
        d = a * a
        unegative(d)
        d -> 3
        """)
        # This is 3, not 2 because there is a bridge for the exit.
        self.check_loop_count(3)


class TestNumpyOld(LLJitMixin):
    def setup_class(cls):
        from pypy.module.micronumpy.compile import FakeSpace
        from pypy.module.micronumpy.interp_dtype import get_dtype_cache

        cls.space = FakeSpace()
        cls.float64_dtype = get_dtype_cache(cls.space).w_float64dtype

    def test_slice(self):
        def f(i):
            step = 3
            ar = SingleDimArray(step*i, dtype=self.float64_dtype)
            new_sig = signature.Signature.find_sig([
                SingleDimSlice.signature, ar.signature
            ])
            s = SingleDimSlice(0, step*i, step, i, ar, new_sig)
            v = interp_ufuncs.get(self.space).add.call(self.space, [s, s])
            v = v.get_concrete().eval(3)
            assert isinstance(v, interp_boxes.W_Float64Box)
            return v.value

        result = self.meta_interp(f, [5], listops=True, backendopt=True)
        self.check_loops({'int_mul': 1, 'getinteriorfield_raw': 2, 'float_add': 1,
                          'setinteriorfield_raw': 1, 'int_add': 1,
                          'int_lt': 1, 'guard_true': 1, 'jump': 1})
        assert result == f(5)

    def test_slice2(self):
        def f(i):
            step1 = 2
            step2 = 3
            ar = SingleDimArray(step2*i, dtype=self.float64_dtype)
            new_sig = signature.Signature.find_sig([
                SingleDimSlice.signature, ar.signature
            ])
            s1 = SingleDimSlice(0, step1*i, step1, i, ar, new_sig)
            new_sig = signature.Signature.find_sig([
                SingleDimSlice.signature, s1.signature
            ])
            s2 = SingleDimSlice(0, step2*i, step2, i, ar, new_sig)
            v = interp_ufuncs.get(self.space).add.call(self.space, [s1, s2])
            v = v.get_concrete().eval(3)
            assert isinstance(v, interp_boxes.W_Float64Box)
            return v.value

        result = self.meta_interp(f, [5], listops=True, backendopt=True)
        self.check_loops({'int_mul': 2, 'getinteriorfield_raw': 2, 'float_add': 1,
                          'setinteriorfield_raw': 1, 'int_add': 1,
                          'int_lt': 1, 'guard_true': 1, 'jump': 1})
        assert result == f(5)

    def test_setslice(self):
        space = self.space
        float64_dtype = self.float64_dtype

        def f(i):
            step = NonConstant(3)
            ar = SingleDimArray(step*i, dtype=float64_dtype)
            ar2 = SingleDimArray(i, dtype=float64_dtype)
            ar2.get_concrete().setitem(1, float64_dtype.box(5.5))
            arg = ar2.descr_add(space, ar2)
            ar.setslice(space, 0, step*i, step, i, arg)
            v = ar.get_concrete().eval(3)
            assert isinstance(v, interp_boxes.W_Float64Box)
            return v.value

        result = self.meta_interp(f, [5], listops=True, backendopt=True)
        self.check_loops({'getinteriorfield_raw': 2,
                          'float_add' : 1,
                          'setinteriorfield_raw': 1, 'int_add': 2,
                          'int_lt': 1, 'guard_true': 1, 'jump': 1})
        assert result == 11.0

    def test_int32_sum(self):
        py.test.skip("pypy/jit/backend/llimpl.py needs to be changed to "
                     "deal correctly with int dtypes for this test to "
                     "work. skip for now until someone feels up to the task")
        space = self.space
        float64_dtype = self.float64_dtype
        int32_dtype = self.int32_dtype

        def f(n):
            if NonConstant(False):
                dtype = float64_dtype
            else:
                dtype = int32_dtype
            ar = SingleDimArray(n, dtype=dtype)
            i = 0
            while i < n:
                ar.get_concrete().setitem(i, int32_dtype.box(7))
                i += 1
            v = ar.descr_add(space, ar).descr_sum(space)
            assert isinstance(v, IntObject)
            return v.intval

        result = self.meta_interp(f, [5], listops=True, backendopt=True)
        assert result == f(5)

