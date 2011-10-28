from pypy.jit.metainterp.test.support import LLJitMixin
from pypy.module.micronumpy import interp_ufuncs, signature
from pypy.module.micronumpy.compile import (FakeSpace,
    FloatObject, IntObject, numpy_compile)
from pypy.module.micronumpy.interp_numarray import (BaseArray, SingleDimArray,
    SingleDimSlice, scalar_w)
from pypy.rlib.nonconst import NonConstant
from pypy.rpython.annlowlevel import llstr, hlstr
from pypy.rpython.test.test_llinterp import interpret
from pypy.jit.metainterp.warmspot import reset_stats

import py


class TestNumpyJIt(LLJitMixin):
    graph = None
    interp = None
        
    def run(self, code):
        space = FakeSpace()
        
        def f(code):
            interp = numpy_compile(hlstr(code))
            interp.run(space)
            res = interp.results[0]
            return interp.space.float_w(res.eval(0).wrap(interp.space))

        if self.graph is None:
            interp, graph = self.meta_interp(f, [llstr(code)],
                                             listops=True,
                                             backendopt=True,
                                             graph_and_interp_only=True)
            self.__class__.interp = interp
            self.__class__.graph = graph

        reset_stats()
        return self.interp.eval_graph(self.graph, [llstr(code)])

    def test_add(self):
        result = self.run("""
        a = |30|
        b = a + a
        b -> 3
        """)
        self.check_loops({'getarrayitem_raw': 2, 'float_add': 1,
                          'setarrayitem_raw': 1, 'int_add': 1,
                          'int_lt': 1, 'guard_true': 1, 'jump': 1})
        assert result == 3 + 3

    def test_floatadd(self):
        result = self.run("""
        a = |30| + 3
        a -> 3
        """)
        assert result == 3 + 3
        self.check_loops({"getarrayitem_raw": 1, "float_add": 1,
                          "setarrayitem_raw": 1, "int_add": 1,
                          "int_lt": 1, "guard_true": 1, "jump": 1})

    def test_sum(self):
        result = self.run("""
        a = |30|
        b = a + a
        sum(b)
        """)
        assert result == 2 * sum(range(30))
        self.check_loops({"getarrayitem_raw": 2, "float_add": 2,
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
        self.check_loops({"getarrayitem_raw": 2, "float_add": 1,
                          "float_mul": 1, "int_add": 1,
                          "int_lt": 1, "guard_true": 1, "jump": 1})

    def test_max(self):
        result = self.run("""
        a = |30|
        a[13] = 128
        b = a + a
        max(b)
        """)
        assert result == 256
        self.check_loops({"getarrayitem_raw": 2, "float_add": 1,
                          "float_mul": 1, "int_add": 1,
                          "int_lt": 1, "guard_true": 1, "jump": 1})

    def test_min(self):
        result = self.run("""
        a = |30|
        a[15] = -12
        b = a + a
        min(b)
        """)
        assert result == -24
        self.check_loops({"getarrayitem_raw": 2, "float_add": 1,
                          "float_mul": 1, "int_add": 1,
                          "int_lt": 1, "guard_true": 1, "jump": 1})

class DisabledTestNumpy(object):

    def test_argmin(self):
        space = self.space
        float64_dtype = self.float64_dtype

        def f(i):
            ar = SingleDimArray(i, dtype=NonConstant(float64_dtype))
            j = 0
            while j < i:
                ar.get_concrete().setitem(j, float64_dtype.box(float(j)))
                j += 1
            return ar.descr_add(space, ar).descr_argmin(space).intval

        result = self.meta_interp(f, [5], listops=True, backendopt=True)
        self.check_loops({"getarrayitem_raw": 2, "float_add": 1,
                           "float_lt": 1, "int_add": 1,
                           "int_lt": 1, "guard_true": 2,
                           "jump": 1})
        assert result == f(5)

    def test_all(self):
        space = self.space
        float64_dtype = self.float64_dtype

        def f(i):
            ar = SingleDimArray(i, dtype=NonConstant(float64_dtype))
            j = 0
            while j < i:
                ar.get_concrete().setitem(j, float64_dtype.box(1.0))
                j += 1
            return ar.descr_add(space, ar).descr_all(space).boolval

        result = self.meta_interp(f, [5], listops=True, backendopt=True)
        self.check_loops({"getarrayitem_raw": 2, "float_add": 1,
                          "int_add": 1, "float_ne": 1,
                          "int_lt": 1, "guard_true": 2, "jump": 1})
        assert result == f(5)

    def test_any(self):
        space = self.space
        float64_dtype = self.float64_dtype

        def f(i):
            ar = SingleDimArray(i, dtype=NonConstant(float64_dtype))
            return ar.descr_add(space, ar).descr_any(space).boolval

        result = self.meta_interp(f, [5], listops=True, backendopt=True)
        self.check_loops({"getarrayitem_raw": 2, "float_add": 1,
                          "int_add": 1, "float_ne": 1, "guard_false": 1,
                          "int_lt": 1, "guard_true": 1, "jump": 1})
        assert result == f(5)

    def test_already_forced(self):
        space = self.space

        def f(i):
            ar = SingleDimArray(i, dtype=self.float64_dtype)
            v1 = interp_ufuncs.get(self.space).add.call(space, [ar, scalar_w(space, self.float64_dtype, space.wrap(4.5))])
            assert isinstance(v1, BaseArray)
            v2 = interp_ufuncs.get(self.space).multiply.call(space, [v1, scalar_w(space, self.float64_dtype, space.wrap(4.5))])
            v1.force_if_needed()
            assert isinstance(v2, BaseArray)
            return v2.get_concrete().eval(3).val

        result = self.meta_interp(f, [5], listops=True, backendopt=True)
        # This is the sum of the ops for both loops, however if you remove the
        # optimization then you end up with 2 float_adds, so we can still be
        # sure it was optimized correctly.
        self.check_loops({"getarrayitem_raw": 2, "float_mul": 1, "float_add": 1,
                           "setarrayitem_raw": 2, "int_add": 2,
                           "int_lt": 2, "guard_true": 2, "jump": 2})
        assert result == f(5)

    def test_ufunc(self):
        space = self.space
        def f(i):
            ar = SingleDimArray(i, dtype=self.float64_dtype)
            v1 = interp_ufuncs.get(self.space).add.call(space, [ar, ar])
            v2 = interp_ufuncs.get(self.space).negative.call(space, [v1])
            return v2.get_concrete().eval(3).val

        result = self.meta_interp(f, [5], listops=True, backendopt=True)
        self.check_loops({"getarrayitem_raw": 2, "float_add": 1, "float_neg": 1,
                          "setarrayitem_raw": 1, "int_add": 1,
                          "int_lt": 1, "guard_true": 1, "jump": 1,
        })
        assert result == f(5)

    def test_appropriate_specialization(self):
        space = self.space
        def f(i):
            ar = SingleDimArray(i, dtype=self.float64_dtype)

            v1 = interp_ufuncs.get(self.space).add.call(space, [ar, ar])
            v2 = interp_ufuncs.get(self.space).negative.call(space, [v1])
            v2.get_concrete()

            for i in xrange(5):
                v1 = interp_ufuncs.get(self.space).multiply.call(space, [ar, ar])
                v2 = interp_ufuncs.get(self.space).negative.call(space, [v1])
                v2.get_concrete()

        self.meta_interp(f, [5], listops=True, backendopt=True)
        # This is 3, not 2 because there is a bridge for the exit.
        self.check_loop_count(3)

    def test_slice(self):
        def f(i):
            step = 3
            ar = SingleDimArray(step*i, dtype=self.float64_dtype)
            new_sig = signature.Signature.find_sig([
                SingleDimSlice.signature, ar.signature
            ])
            s = SingleDimSlice(0, step*i, step, i, ar, new_sig)
            v = interp_ufuncs.get(self.space).add.call(self.space, [s, s])
            return v.get_concrete().eval(3).val

        result = self.meta_interp(f, [5], listops=True, backendopt=True)
        self.check_loops({'int_mul': 1, 'getarrayitem_raw': 2, 'float_add': 1,
                          'setarrayitem_raw': 1, 'int_add': 1,
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
            return v.get_concrete().eval(3).val

        result = self.meta_interp(f, [5], listops=True, backendopt=True)
        self.check_loops({'int_mul': 2, 'getarrayitem_raw': 2, 'float_add': 1,
                          'setarrayitem_raw': 1, 'int_add': 1,
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
            return ar.get_concrete().eval(3).val

        result = self.meta_interp(f, [5], listops=True, backendopt=True)
        self.check_loops({'getarrayitem_raw': 2,
                          'float_add' : 1,
                          'setarrayitem_raw': 1, 'int_add': 2,
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

