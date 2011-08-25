from pypy.jit.metainterp.test.support import LLJitMixin
from pypy.module.micronumpy import interp_ufuncs, signature
from pypy.module.micronumpy.compile import (numpy_compile, FakeSpace,
    FloatObject)
from pypy.module.micronumpy.interp_dtype import W_Float64Dtype, W_Int64Dtype
from pypy.module.micronumpy.interp_numarray import (BaseArray, SingleDimArray,
    SingleDimSlice, scalar_w)
from pypy.rlib.nonconst import NonConstant
from pypy.rpython.annlowlevel import llstr
from pypy.rpython.test.test_llinterp import interpret


class TestNumpyJIt(LLJitMixin):
    def setup_class(cls):
        cls.space = FakeSpace()
        cls.float64_dtype = cls.space.fromcache(W_Float64Dtype)
        cls.int64_dtype = cls.space.fromcache(W_Int64Dtype)

    def test_add(self):
        def f(i):
            ar = SingleDimArray(i, dtype=self.float64_dtype)
            v = interp_ufuncs.add(self.space, ar, ar)
            return v.get_concrete().eval(3).val

        result = self.meta_interp(f, [5], listops=True, backendopt=True)
        self.check_loops({'getarrayitem_raw': 2, 'float_add': 1,
                          'setarrayitem_raw': 1, 'int_add': 1,
                          'int_lt': 1, 'guard_true': 1, 'jump': 1})
        assert result == f(5)

    def test_floatadd(self):
        def f(i):
            ar = SingleDimArray(i, dtype=self.float64_dtype)
            v = interp_ufuncs.add(self.space,
                ar,
                scalar_w(self.space, self.float64_dtype, self.space.wrap(4.5))
            )
            assert isinstance(v, BaseArray)
            return v.get_concrete().eval(3).val

        result = self.meta_interp(f, [5], listops=True, backendopt=True)
        self.check_loops({"getarrayitem_raw": 1, "float_add": 1,
                          "setarrayitem_raw": 1, "int_add": 1,
                          "int_lt": 1, "guard_true": 1, "jump": 1})
        assert result == f(5)

    def test_sum(self):
        space = self.space
        float64_dtype = self.float64_dtype
        int64_dtype = self.int64_dtype

        def f(i):
            if NonConstant(False):
                dtype = int64_dtype
            else:
                dtype = float64_dtype
            ar = SingleDimArray(i, dtype=dtype)
            v = ar.descr_add(space, ar).descr_sum(space)
            assert isinstance(v, FloatObject)
            return v.floatval

        result = self.meta_interp(f, [5], listops=True, backendopt=True)
        self.check_loops({"getarrayitem_raw": 2, "float_add": 2,
                          "int_add": 1,
                          "int_lt": 1, "guard_true": 1, "jump": 1})
        assert result == f(5)

    def test_prod(self):
        space = self.space
        float64_dtype = self.float64_dtype
        int64_dtype = self.int64_dtype

        def f(i):
            if NonConstant(False):
                dtype = int64_dtype
            else:
                dtype = float64_dtype
            ar = SingleDimArray(i, dtype=dtype)
            v = ar.descr_add(space, ar).descr_prod(space)
            assert isinstance(v, FloatObject)
            return v.floatval

        result = self.meta_interp(f, [5], listops=True, backendopt=True)
        self.check_loops({"getarrayitem_raw": 2, "float_add": 1,
                          "float_mul": 1, "int_add": 1,
                          "int_lt": 1, "guard_true": 1, "jump": 1})
        assert result == f(5)

    def test_max(self):
        space = self.space
        float64_dtype = self.float64_dtype

        def f(i):
            ar = SingleDimArray(i, dtype=NonConstant(float64_dtype))
            j = 0
            while j < i:
                ar.get_concrete().setitem(j, float64_dtype.box(float(j)))
                j += 1
            return ar.descr_add(space, ar).descr_max(space).floatval

        result = self.meta_interp(f, [5], listops=True, backendopt=True)
        self.check_loops({"getarrayitem_raw": 2, "float_add": 1,
                          "float_gt": 1, "int_add": 1,
                          "int_lt": 1, "guard_true": 1,
                          "guard_false": 1, "jump": 1})
        assert result == f(5)

    def test_min(self):
        space = self.space
        float64_dtype = self.float64_dtype

        def f(i):
            ar = SingleDimArray(i, dtype=NonConstant(float64_dtype))
            j = 0
            while j < i:
                ar.get_concrete().setitem(j, float64_dtype.box(float(j)))
                j += 1
            return ar.descr_add(space, ar).descr_min(space).floatval

        result = self.meta_interp(f, [5], listops=True, backendopt=True)
        self.check_loops({"getarrayitem_raw": 2, "float_add": 1,
                           "float_lt": 1, "int_add": 1,
                           "int_lt": 1, "guard_true": 2,
                           "jump": 1})
        assert result == f(5)

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
            v1 = interp_ufuncs.add(space, ar, scalar_w(space, self.float64_dtype, space.wrap(4.5)))
            assert isinstance(v1, BaseArray)
            v2 = interp_ufuncs.multiply(space, v1, scalar_w(space, self.float64_dtype, space.wrap(4.5)))
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
            v1 = interp_ufuncs.add(space, ar, ar)
            v2 = interp_ufuncs.negative(space, v1)
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

            v1 = interp_ufuncs.add(space, ar, ar)
            v2 = interp_ufuncs.negative(space, v1)
            v2.get_concrete()

            for i in xrange(5):
                v1 = interp_ufuncs.multiply(space, ar, ar)
                v2 = interp_ufuncs.negative(space, v1)
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
            v = interp_ufuncs.add(self.space, s, s)
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
            v = interp_ufuncs.add(self.space, s1, s2)
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

class TestTranslation(object):
    def test_compile(self):
        x = numpy_compile('aa+f*f/a-', 10)
        x = x.compute()
        assert isinstance(x, SingleDimArray)
        assert x.size == 10
        assert x.eval(0).val == 0
        assert x.eval(1).val == ((1 + 1) * 1.2) / 1.2 - 1

    def test_translation(self):
        # we import main to check if the target compiles
        from pypy.translator.goal.targetnumpystandalone import main

        interpret(main, [llstr('af+'), 100])
