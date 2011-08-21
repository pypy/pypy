from pypy.interpreter.baseobjspace import InternalSpaceCache
from pypy.jit.metainterp.test.support import LLJitMixin
from pypy.module.micronumpy import interp_ufuncs, signature
from pypy.module.micronumpy.compile import numpy_compile
from pypy.module.micronumpy.interp_dtype import W_Float64Dtype
from pypy.module.micronumpy.interp_numarray import SingleDimArray, SingleDimSlice, scalar_w
from pypy.rlib.nonconst import NonConstant
from pypy.rlib.objectmodel import specialize
from pypy.rpython.test.test_llinterp import interpret


class FakeSpace(object):
    w_ValueError = None

    def __init__(self):
        self.fromcache = InternalSpaceCache(self).getorbuild

    def issequence_w(self, w_obj):
        return True

    @specialize.argtype(1)
    def wrap(self, w_obj):
        return w_obj

    def float(self, w_obj):
        return float(w_obj)

    def float_w(self, w_obj):
        return float(w_obj)

class TestNumpyJIt(LLJitMixin):
    def setup_class(cls):
        cls.space = FakeSpace()
        cls.float64_dtype = W_Float64Dtype(cls.space)

    def test_add(self):
        def f(i):
            ar = SingleDimArray(i, dtype=self.float64_dtype)
            v = interp_ufuncs.add(self.space, ar, ar)
            concrete = v.get_concrete()
            return concrete.dtype.getitem(concrete.storage, 3).val

        result = self.meta_interp(f, [5], listops=True, backendopt=True)
        self.check_loops({'getarrayitem_raw': 2, 'float_add': 1,
                          'setarrayitem_raw': 1, 'int_add': 1,
                          'int_lt': 1, 'guard_true': 1, 'jump': 1})
        assert result == f(5)

    def test_floatadd(self):
        def f(i):
            ar = SingleDimArray(i, dtype=self.float64_dtype)
            v = interp_ufuncs.add(self.space, ar, scalar_w(self.space, W_Float64Dtype, 4.5))
            return v.dtype.getitem(v.get_concrete().storage, 3)

        result = self.meta_interp(f, [5], listops=True, backendopt=True)
        self.check_loops({"getarrayitem_raw": 1, "float_add": 1,
                          "setarrayitem_raw": 1, "int_add": 1,
                          "int_lt": 1, "guard_true": 1, "jump": 1})
        assert result == f(5)

    def test_sum(self):
        space = self.space

        def f(i):
            ar = SingleDimArray(i, dtype=self.float64_dtype)
            return ar.descr_add(space, ar).descr_sum(space)

        result = self.meta_interp(f, [5], listops=True, backendopt=True)
        self.check_loops({"getarrayitem_raw": 2, "float_add": 2,
                          "int_add": 1,
                          "int_lt": 1, "guard_true": 1, "jump": 1})
        assert result == f(5)

    def test_prod(self):
        space = self.space

        def f(i):
            ar = SingleDimArray(i, dtype=self.float64_dtype)
            return ar.descr_add(space, ar).descr_prod(space)

        result = self.meta_interp(f, [5], listops=True, backendopt=True)
        self.check_loops({"getarrayitem_raw": 2, "float_add": 1,
                          "float_mul": 1, "int_add": 1,
                          "int_lt": 1, "guard_true": 1, "jump": 1})
        assert result == f(5)

    def test_max(self):
        space = self.space

        def f(i):
            ar = SingleDimArray(i, dtype=self.float64_dtype)
            j = 0
            while j < i:
                ar.get_concrete().storage[j] = float(j)
                j += 1
            return ar.descr_add(space, ar).descr_max(space)

        result = self.meta_interp(f, [5], listops=True, backendopt=True)
        self.check_loops({"getarrayitem_raw": 2, "float_add": 1,
                          "float_gt": 1, "int_add": 1,
                          "int_lt": 1, "guard_true": 1,
                          "guard_false": 1, "jump": 1})
        assert result == f(5)

    def test_min(self):
        space = self.space

        def f(i):
            ar = SingleDimArray(i, dtype=self.float64_dtype)
            j = 0
            while j < i:
                ar.get_concrete().storage[j] = float(j)
                j += 1
            return ar.descr_add(space, ar).descr_min(space)

        result = self.meta_interp(f, [5], listops=True, backendopt=True)
        self.check_loops({"getarrayitem_raw": 2, "float_add": 1,
                           "float_lt": 1, "int_add": 1,
                           "int_lt": 1, "guard_true": 2,
                           "jump": 1})
        assert result == f(5)

    def test_argmin(self):
        space = self.space

        def f(i):
            ar = SingleDimArray(i, dtype=self.float64_dtype)
            j = 0
            while j < i:
                ar.get_concrete().storage[j] = float(j)
                j += 1
            return ar.descr_add(space, ar).descr_argmin(space)

        result = self.meta_interp(f, [5], listops=True, backendopt=True)
        self.check_loops({"getarrayitem_raw": 2, "float_add": 1,
                           "float_lt": 1, "int_add": 1,
                           "int_lt": 1, "guard_true": 2,
                           "jump": 1})
        assert result == f(5)

    def test_all(self):
        space = self.space

        def f(i):
            ar = SingleDimArray(i, dtype=self.float64_dtype)
            j = 0
            while j < i:
                ar.get_concrete().storage[j] = 1.0
                j += 1
            return ar.descr_add(space, ar).descr_all(space)
        result = self.meta_interp(f, [5], listops=True, backendopt=True)
        self.check_loops({"getarrayitem_raw": 2, "float_add": 1,
                          "int_add": 1, "float_ne": 1,
                          "int_lt": 1, "guard_true": 2, "jump": 1})
        assert result == f(5)

    def test_any(self):
        space = self.space

        def f(i):
            ar = SingleDimArray(i, dtype=self.float64_dtype)
            return ar.descr_add(space, ar).descr_any(space)

        result = self.meta_interp(f, [5], listops=True, backendopt=True)
        self.check_loops({"getarrayitem_raw": 2, "float_add": 1,
                          "int_add": 1, "float_ne": 1, "guard_false": 1,
                          "int_lt": 1, "guard_true": 1, "jump": 1})
        assert result == f(5)

    def test_already_forced(self):
        def f(i):
            ar = SingleDimArray(i, dtype=self.float64_dtype)
            v1 = interp_ufuncs.add(self.space, ar, scalar_w(self.space, W_Float64Dtype, 4.5))
            v2 = interp_ufuncs.mul(self.space, v1, scalar_w(self.space, W_Float64Dtype, 4.5))
            v1.force_if_needed()
            return v2.get_concrete().storage[3]

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
            return v2.get_concrete().storage[3]

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
                v1 = interp_ufuncs.mul(space, ar, ar)
                v2 = negative(space, v1)
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
            return v.get_concrete().storage[3]

        result = self.meta_interp(f, [5], listops=True, backendopt=True)
        self.check_loops({'int_mul': 1, 'getarrayitem_raw': 2, 'float_add': 1,
                          'setarrayitem_raw': 1, 'int_add': 1,
                          'int_lt': 1, 'guard_true': 1, 'jump': 1})
        assert result == f(5)

    def test_slice2(self):
        def f(i):
            step1 = 2
            step2 = 3
            ar = SingleDimArray(step2*i)
            s1 = SingleDimSlice(0, step1*i, step1, i, ar, ar.signature.transition(SingleDimSlice.static_signature))
            s2 = SingleDimSlice(0, step2*i, step2, i, ar, ar.signature.transition(SingleDimSlice.static_signature))
            v = Call2(add, s1, s2, Signature())
            return v.get_concrete().storage[3]

        result = self.meta_interp(f, [5], listops=True, backendopt=True)
        self.check_loops({'int_mul': 2, 'getarrayitem_raw': 2, 'float_add': 1,
                          'setarrayitem_raw': 1, 'int_add': 1,
                          'int_lt': 1, 'guard_true': 1, 'jump': 1})
        assert result == f(5)

    def test_setslice(self):
        space = self.space

        def f(i):
            step = NonConstant(3)
            ar = SingleDimArray(step*i, dtype=self.float64_dtype)
            ar2 = SingleDimArray(i, dtype=self.float64_dtype)
            ar2.storage[1] = 5.5
            if NonConstant(False):
                arg = ar2
            else:
                arg = ar2.descr_add(space, ar2)
            ar.setslice(space, 0, step*i, step, i, arg)
            return ar.get_concrete().storage[3]

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
        assert x.storage[0] == 0
        assert x.storage[1] == ((1 + 1) * 1.2) / 1.2 - 1

    def test_translation(self):
        # we import main to check if the target compiles
        from pypy.translator.goal.targetnumpystandalone import main
        from pypy.rpython.annlowlevel import llstr

        interpret(main, [llstr('af+'), 100])
