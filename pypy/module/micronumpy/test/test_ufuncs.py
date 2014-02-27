from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest
from pypy.module.micronumpy.ufuncs import (find_binop_result_dtype,
        find_unaryop_result_dtype)
from pypy.module.micronumpy.descriptor import get_dtype_cache


class TestUfuncCoercion(object):
    def test_binops(self, space):
        bool_dtype = get_dtype_cache(space).w_booldtype
        int8_dtype = get_dtype_cache(space).w_int8dtype
        int32_dtype = get_dtype_cache(space).w_int32dtype
        float64_dtype = get_dtype_cache(space).w_float64dtype
        c64_dtype = get_dtype_cache(space).w_complex64dtype
        c128_dtype = get_dtype_cache(space).w_complex128dtype
        cld_dtype = get_dtype_cache(space).w_complexlongdtype
        fld_dtype = get_dtype_cache(space).w_floatlongdtype

        # Basic pairing
        assert find_binop_result_dtype(space, bool_dtype, bool_dtype) is bool_dtype
        assert find_binop_result_dtype(space, bool_dtype, float64_dtype) is float64_dtype
        assert find_binop_result_dtype(space, float64_dtype, bool_dtype) is float64_dtype
        assert find_binop_result_dtype(space, int32_dtype, int8_dtype) is int32_dtype
        assert find_binop_result_dtype(space, int32_dtype, bool_dtype) is int32_dtype
        assert find_binop_result_dtype(space, c64_dtype, float64_dtype) is c128_dtype
        assert find_binop_result_dtype(space, c64_dtype, fld_dtype) is cld_dtype
        assert find_binop_result_dtype(space, c128_dtype, fld_dtype) is cld_dtype

        # With promote bool (happens on div), the result is that the op should
        # promote bools to int8
        assert find_binop_result_dtype(space, bool_dtype, bool_dtype, promote_bools=True) is int8_dtype
        assert find_binop_result_dtype(space, bool_dtype, float64_dtype, promote_bools=True) is float64_dtype

        # Coerce to floats
        assert find_binop_result_dtype(space, bool_dtype, float64_dtype, promote_to_float=True) is float64_dtype

    def test_unaryops(self, space):
        bool_dtype = get_dtype_cache(space).w_booldtype
        int8_dtype = get_dtype_cache(space).w_int8dtype
        uint8_dtype = get_dtype_cache(space).w_uint8dtype
        int16_dtype = get_dtype_cache(space).w_int16dtype
        uint16_dtype = get_dtype_cache(space).w_uint16dtype
        int32_dtype = get_dtype_cache(space).w_int32dtype
        uint32_dtype = get_dtype_cache(space).w_uint32dtype
        long_dtype = get_dtype_cache(space).w_longdtype
        ulong_dtype = get_dtype_cache(space).w_ulongdtype
        int64_dtype = get_dtype_cache(space).w_int64dtype
        uint64_dtype = get_dtype_cache(space).w_uint64dtype
        float16_dtype = get_dtype_cache(space).w_float16dtype
        float32_dtype = get_dtype_cache(space).w_float32dtype
        float64_dtype = get_dtype_cache(space).w_float64dtype

        # Normal rules, everything returns itself
        assert find_unaryop_result_dtype(space, bool_dtype) is bool_dtype
        assert find_unaryop_result_dtype(space, int8_dtype) is int8_dtype
        assert find_unaryop_result_dtype(space, uint8_dtype) is uint8_dtype
        assert find_unaryop_result_dtype(space, int16_dtype) is int16_dtype
        assert find_unaryop_result_dtype(space, uint16_dtype) is uint16_dtype
        assert find_unaryop_result_dtype(space, int32_dtype) is int32_dtype
        assert find_unaryop_result_dtype(space, uint32_dtype) is uint32_dtype
        assert find_unaryop_result_dtype(space, long_dtype) is long_dtype
        assert find_unaryop_result_dtype(space, ulong_dtype) is ulong_dtype
        assert find_unaryop_result_dtype(space, int64_dtype) is int64_dtype
        assert find_unaryop_result_dtype(space, uint64_dtype) is uint64_dtype
        assert find_unaryop_result_dtype(space, float32_dtype) is float32_dtype
        assert find_unaryop_result_dtype(space, float64_dtype) is float64_dtype

        # Coerce to floats, some of these will eventually be float16, or
        # whatever our smallest float type is.
        assert find_unaryop_result_dtype(space, bool_dtype, promote_to_float=True) is float16_dtype
        assert find_unaryop_result_dtype(space, int8_dtype, promote_to_float=True) is float16_dtype
        assert find_unaryop_result_dtype(space, uint8_dtype, promote_to_float=True) is float16_dtype
        assert find_unaryop_result_dtype(space, int16_dtype, promote_to_float=True) is float32_dtype
        assert find_unaryop_result_dtype(space, uint16_dtype, promote_to_float=True) is float32_dtype
        assert find_unaryop_result_dtype(space, int32_dtype, promote_to_float=True) is float64_dtype
        assert find_unaryop_result_dtype(space, uint32_dtype, promote_to_float=True) is float64_dtype
        assert find_unaryop_result_dtype(space, int64_dtype, promote_to_float=True) is float64_dtype
        assert find_unaryop_result_dtype(space, uint64_dtype, promote_to_float=True) is float64_dtype
        assert find_unaryop_result_dtype(space, float32_dtype, promote_to_float=True) is float32_dtype
        assert find_unaryop_result_dtype(space, float64_dtype, promote_to_float=True) is float64_dtype

        # promote bools, happens with sign ufunc
        assert find_unaryop_result_dtype(space, bool_dtype, promote_bools=True) is int8_dtype


class AppTestUfuncs(BaseNumpyAppTest):
    def test_constants(self):
        import numpy as np
        assert np.FLOATING_POINT_SUPPORT == 1

    def test_ufunc_instance(self):
        from numpypy import add, ufunc

        assert isinstance(add, ufunc)
        assert repr(add) == "<ufunc 'add'>"
        assert repr(ufunc) == "<type 'numpy.ufunc'>"
        assert add.__name__ == 'add'

    def test_ufunc_attrs(self):
        from numpypy import add, multiply, sin

        assert add.identity == 0
        assert multiply.identity == 1
        assert sin.identity is None

        assert add.nin == 2
        assert multiply.nin == 2
        assert sin.nin == 1

    def test_wrong_arguments(self):
        from numpypy import add, sin

        raises(ValueError, add, 1)
        raises(TypeError, add, 1, 2, 3)
        raises(TypeError, sin, 1, 2)
        raises(ValueError, sin)

    def test_single_item(self):
        from numpypy import negative, sign, minimum

        assert negative(5.0) == -5.0
        assert sign(-0.0) == 0.0
        assert minimum(2.0, 3.0) == 2.0

    def test_sequence(self):
        from numpypy import array, ndarray, negative, minimum
        a = array(range(3))
        b = [2.0, 1.0, 0.0]
        c = 1.0
        b_neg = negative(b)
        assert isinstance(b_neg, ndarray)
        for i in range(3):
            assert b_neg[i] == -b[i]
        min_a_b = minimum(a, b)
        assert isinstance(min_a_b, ndarray)
        for i in range(3):
            assert min_a_b[i] == min(a[i], b[i])
        min_b_a = minimum(b, a)
        assert isinstance(min_b_a, ndarray)
        for i in range(3):
            assert min_b_a[i] == min(a[i], b[i])
        min_a_c = minimum(a, c)
        assert isinstance(min_a_c, ndarray)
        for i in range(3):
            assert min_a_c[i] == min(a[i], c)
        min_c_a = minimum(c, a)
        assert isinstance(min_c_a, ndarray)
        for i in range(3):
            assert min_c_a[i] == min(a[i], c)
        min_b_c = minimum(b, c)
        assert isinstance(min_b_c, ndarray)
        for i in range(3):
            assert min_b_c[i] == min(b[i], c)
        min_c_b = minimum(c, b)
        assert isinstance(min_c_b, ndarray)
        for i in range(3):
            assert min_c_b[i] == min(b[i], c)

    def test_scalar(self):
        # tests that by calling all available ufuncs on scalars, none will
        # raise uncaught interp-level exceptions, (and crash the test)
        # and those that are uncallable can be accounted for.
        # test on the four base-class dtypes: int, bool, float, complex
        # We need this test since they have no common base class.
        import numpypy as np
        def find_uncallable_ufuncs(dtype):
            uncallable = set()
            array = np.array(1, dtype)
            for s in dir(np):
                u = getattr(np, s)
                if isinstance(u, np.ufunc):
                    try:
                        u(* [array] * u.nin)
                    except TypeError:
                        assert s not in uncallable
                        uncallable.add(s)
            return uncallable
        assert find_uncallable_ufuncs('int') == set()
        assert find_uncallable_ufuncs('bool') == set(['sign'])
        assert find_uncallable_ufuncs('float') == set(
                ['bitwise_and', 'bitwise_not', 'bitwise_or', 'bitwise_xor',
                 'left_shift', 'right_shift', 'invert'])
        assert find_uncallable_ufuncs('complex') == set(
                ['bitwise_and', 'bitwise_not', 'bitwise_or', 'bitwise_xor',
                 'arctan2', 'deg2rad', 'degrees', 'rad2deg', 'radians',
                 'fabs', 'fmod', 'invert', 'mod',
                 'logaddexp', 'logaddexp2', 'left_shift', 'right_shift',
                 'copysign', 'signbit', 'ceil', 'floor', 'trunc'])

    def test_int_only(self):
        from numpypy import bitwise_and, array
        a = array(1.0)
        raises(TypeError, bitwise_and, a, a)

    def test_negative(self):
        from numpypy import array, negative

        a = array([-5.0, 0.0, 1.0])
        b = negative(a)
        for i in range(3):
            assert b[i] == -a[i]

        a = array([-5.0, 1.0])
        b = negative(a)
        a[0] = 5.0
        assert b[0] == 5.0
        a = array(range(30))
        assert negative(a + a)[3] == -6

        a = array([[1, 2], [3, 4]])
        b = negative(a + a)
        assert (b == [[-2, -4], [-6, -8]]).all()

    def test_abs(self):
        from numpypy import array, absolute

        a = array([-5.0, -0.0, 1.0])
        b = absolute(a)
        for i in range(3):
            assert b[i] == abs(a[i])

    def test_add(self):
        from numpypy import array, add

        a = array([-5.0, -0.0, 1.0])
        b = array([ 3.0, -2.0,-3.0])
        c = add(a, b)
        for i in range(3):
            assert c[i] == a[i] + b[i]

    def test_divide(self):
        from numpypy import array, divide

        a = array([-5.0, -0.0, 1.0])
        b = array([ 3.0, -2.0,-3.0])
        c = divide(a, b)
        for i in range(3):
            assert c[i] == a[i] / b[i]

        assert (divide(array([-10]), array([2])) == array([-5])).all()

    def test_true_divide(self):
        import math
        from numpypy import array, true_divide
        import math

        a = array([0, 1, 2, 3, 4, 1, -1])
        b = array([4, 4, 4, 4, 4, 0,  0])
        c = true_divide(a, b)
        assert (c == [0.0, 0.25, 0.5, 0.75, 1.0, float('inf'), float('-inf')]).all()

        assert math.isnan(true_divide(0, 0))

    def test_fabs(self):
        from numpypy import array, fabs
        from math import fabs as math_fabs, isnan

        a = array([-5.0, -0.0, 1.0])
        b = fabs(a)
        for i in range(3):
            assert b[i] == math_fabs(a[i])
        assert fabs(float('inf')) == float('inf')
        assert fabs(float('-inf')) == float('inf')
        assert isnan(fabs(float('nan')))

    def test_fmax(self):
        from numpypy import fmax, array
        import math

        nnan, nan, inf, ninf = float('-nan'), float('nan'), float('inf'), float('-inf')

        a = [ninf, -5, 0, 5, inf]
        assert (fmax(a, [ninf]*5) == a).all()
        assert (fmax(a, [inf]*5) == [inf]*5).all()
        assert (fmax(a, [1]*5) == [1, 1, 1, 5, inf]).all()
        assert fmax(nan, 0) == 0
        assert fmax(0, nan) == 0
        assert math.isnan(fmax(nan, nan))
        # The numpy docs specify that the FIRST NaN should be used if both are NaN
        # Since comparisons with nnan and nan all return false,
        # use copysign on both sides to sidestep bug in nan representaion
        # on Microsoft win32
        assert math.copysign(1., fmax(nnan, nan)) == math.copysign(1., nnan)

    def test_fmin(self):
        from numpypy import fmin, array
        import math

        nnan, nan, inf, ninf = float('-nan'), float('nan'), float('inf'), float('-inf')

        a = [ninf, -5, 0, 5, inf]
        assert (fmin(a, [ninf]*5) == [ninf]*5).all()
        assert (fmin(a, [inf]*5) == a).all()
        assert (fmin(a, [1]*5) == [ninf, -5, 0, 1, 1]).all()
        assert fmin(nan, 0) == 0
        assert fmin(0, nan) == 0
        assert math.isnan(fmin(nan, nan))
        # The numpy docs specify that the FIRST NaN should be used if both are NaN
        # use copysign on both sides to sidestep bug in nan representaion
        # on Microsoft win32
        assert math.copysign(1., fmin(nnan, nan)) == math.copysign(1., nnan)

    def test_fmod(self):
        from numpypy import fmod
        import math

        assert fmod(-1e-100, 1e100) == -1e-100
        assert fmod(3, float('inf')) == 3
        assert (fmod([-3, -2, -1, 1, 2, 3], 2) == [-1,  0, -1,  1,  0,  1]).all()
        for v in [float('inf'), float('-inf'), float('nan'), float('-nan')]:
            assert math.isnan(fmod(v, 2))

    def test_minimum(self):
        from numpypy import array, minimum

        a = array([-5.0, -0.0, 1.0])
        b = array([ 3.0, -2.0,-3.0])
        c = minimum(a, b)
        for i in range(3):
            assert c[i] == min(a[i], b[i])

    def test_maximum(self):
        from numpypy import array, maximum

        a = array([-5.0, -0.0, 1.0])
        b = array([ 3.0, -2.0,-3.0])
        c = maximum(a, b)
        for i in range(3):
            assert c[i] == max(a[i], b[i])

        x = maximum(2, 3)
        assert x == 3
        assert isinstance(x, (int, long))

    def test_complex_nan_extrema(self):
        import math
        import numpy as np
        cnan = complex(0, np.nan)

        b = np.minimum(1, cnan)
        assert b.real == 0
        assert math.isnan(b.imag)

        b = np.maximum(1, cnan)
        assert b.real == 0
        assert math.isnan(b.imag)

        b = np.fmin(1, cnan)
        assert b.real == 1
        assert b.imag == 0

        b = np.fmax(1, cnan)
        assert b.real == 1
        assert b.imag == 0

    def test_multiply(self):
        from numpypy import array, multiply, arange

        a = array([-5.0, -0.0, 1.0])
        b = array([ 3.0, -2.0,-3.0])
        c = multiply(a, b)
        for i in range(3):
            assert c[i] == a[i] * b[i]

        a = arange(15).reshape(5, 3)
        assert(multiply.reduce(a) == array([0, 3640, 12320])).all()

    def test_rint(self):
        from numpypy import array, dtype, rint, isnan
        import sys

        nnan, nan, inf, ninf = float('-nan'), float('nan'), float('inf'), float('-inf')

        reference = array([ninf, -2., -1., -0., 0., 0., 0., 1., 2., inf])
        a = array([ninf, -1.5, -1., -0.5, -0., 0., 0.5, 1., 1.5, inf])
        b = rint(a)
        for i in range(len(a)):
            assert b[i] == reference[i]
        assert isnan(rint(nan))
        assert isnan(rint(nnan))

        assert rint(complex(inf, 1.5)) == complex(inf, 2.)
        assert rint(complex(0.5, inf)) == complex(0., inf)

        assert rint(sys.maxint) > 0.0

    def test_sign(self):
        from numpypy import array, sign, dtype

        reference = [-1.0, 0.0, 0.0, 1.0]
        a = array([-5.0, -0.0, 0.0, 6.0])
        b = sign(a)
        for i in range(4):
            assert b[i] == reference[i]

        a = sign(array(range(-5, 5)))
        ref = [-1, -1, -1, -1, -1, 0, 1, 1, 1, 1]
        for i in range(10):
            assert a[i] == ref[i]

        a = sign(array([10+10j, -10+10j, 0+10j, 0-10j, 0+0j, 0-0j], dtype=complex))
        ref = [1, -1, 1, -1, 0, 0]
        assert (a == ref).all()

    def test_signbit(self):
        from numpy import signbit, add, copysign, nan
        assert signbit(add.identity) == False
        assert (signbit([0, 0.0, 1, 1.0, float('inf')]) ==
                [False, False, False, False, False]).all()
        assert (signbit([-0, -0.0, -1, -1.0, float('-inf')]) ==
                [False,  True,  True,  True,  True]).all()
        assert (signbit([copysign(nan, 1), copysign(nan, -1)]) ==
                [False, True]).all()

    def test_reciprocal(self):
        from numpy import array, reciprocal
        inf = float('inf')
        nan = float('nan')
        reference = [-0.2, inf, -inf, 2.0, nan]
        a = array([-5.0, 0.0, -0.0, 0.5, nan])
        b = reciprocal(a)
        for i in range(4):
            assert b[i] == reference[i]

        for dtype in 'bBhHiIlLqQ':
            a = array([-2, -1, 0, 1, 2], dtype)
            reference = [0, -1, 0, 1, 0]
            dtype = a.dtype.name
            if dtype[0] == 'u':
                reference[1] = 0
            elif dtype == 'int32':
                    reference[2] = -2147483648
            elif dtype == 'int64':
                    reference[2] = -9223372036854775808
            b = reciprocal(a)
            assert (b == reference).all()

    def test_subtract(self):
        from numpypy import array, subtract

        a = array([-5.0, -0.0, 1.0])
        b = array([ 3.0, -2.0,-3.0])
        c = subtract(a, b)
        for i in range(3):
            assert c[i] == a[i] - b[i]

    def test_floorceiltrunc(self):
        from numpypy import array, floor, ceil, trunc
        import math
        ninf, inf = float("-inf"), float("inf")
        a = array([ninf, -1.4, -1.5, -1.0, 0.0, 1.0, 1.4, 0.5, inf])
        assert ([ninf, -2.0, -2.0, -1.0, 0.0, 1.0, 1.0, 0.0, inf] == floor(a)).all()
        assert ([ninf, -1.0, -1.0, -1.0, 0.0, 1.0, 2.0, 1.0, inf] == ceil(a)).all()
        assert ([ninf, -1.0, -1.0, -1.0, 0.0, 1.0, 1.0, 0.0, inf] == trunc(a)).all()
        assert all([math.isnan(f(float("nan"))) for f in floor, ceil, trunc])
        assert all([math.copysign(1, f(abs(float("nan")))) == 1 for f in floor, ceil, trunc])
        assert all([math.copysign(1, f(-abs(float("nan")))) == -1 for f in floor, ceil, trunc])

    def test_round(self):
        from numpypy import array, dtype
        ninf, inf = float("-inf"), float("inf")
        a = array([ninf, -1.4, -1.5, -1.0, 0.0, 1.0, 1.4, 0.5, inf])
        assert ([ninf, -1.0, -2.0, -1.0, 0.0, 1.0, 1.0, 0.0, inf] == a.round()).all()
        i = array([-1000, -100, -1, 0, 1, 111, 1111, 11111], dtype=int)
        assert (i == i.round()).all()
        assert (i.round(decimals=4) == i).all()
        assert (i.round(decimals=-4) == [0, 0, 0, 0, 0, 0, 0, 10000]).all()
        b = array([True, False], dtype=bool)
        bround = b.round()
        assert (bround == [1., 0.]).all()
        assert bround.dtype is dtype('float16')
        c = array([10.5+11.5j, -15.2-100.3456j, 0.2343+11.123456j])
        assert (c.round(0) == [10.+12.j, -15-100j, 0+11j]).all()

    def test_copysign(self):
        from numpypy import array, copysign

        reference = [5.0, -0.0, 0.0, -6.0]
        a = array([-5.0, 0.0, 0.0, 6.0])
        b = array([5.0, -0.0, 3.0, -6.0])
        c = copysign(a, b)
        for i in range(4):
            assert c[i] == reference[i]

        b = array([True, True, True, True], dtype=bool)
        c = copysign(a, b)
        for i in range(4):
            assert c[i] == abs(a[i])

    def test_exp(self):
        import math
        from numpypy import array, exp

        a = array([-5.0, -0.0, 0.0, 12345678.0, float("inf"),
                   -float('inf'), -12343424.0])
        b = exp(a)
        for i in range(len(a)):
            try:
                res = math.exp(a[i])
            except OverflowError:
                res = float('inf')
            assert b[i] == res

    def test_exp2(self):
        import math
        from numpypy import array, exp2
        inf = float('inf')
        ninf = -float('inf')
        nan = float('nan')

        a = array([-5.0, -0.0, 0.0, 2, 12345678.0, inf, ninf, -12343424.0])
        b = exp2(a)
        for i in range(len(a)):
            try:
                res = 2 ** a[i]
            except OverflowError:
                res = float('inf')
            assert b[i] == res

        assert exp2(3) == 8
        assert math.isnan(exp2(nan))

    def test_expm1(self):
        import math, cmath
        from numpypy import array, expm1
        inf = float('inf')
        ninf = -float('inf')
        nan = float('nan')

        a = array([-5.0, -0.0, 0.0, 12345678.0, float("inf"),
                   -float('inf'), -12343424.0])
        b = expm1(a)
        for i in range(4):
            try:
                res = math.exp(a[i]) - 1
            except OverflowError:
                res = float('inf')
            assert b[i] == res

        assert expm1(1e-50) == 1e-50

    def test_sin(self):
        import math
        from numpypy import array, sin

        a = array([0, 1, 2, 3, math.pi, math.pi*1.5, math.pi*2])
        b = sin(a)
        for i in range(len(a)):
            assert b[i] == math.sin(a[i])

        a = sin(array([True, False], dtype=bool))
        assert abs(a[0] - sin(1)) < 1e-3  # a[0] will be very imprecise
        assert a[1] == 0.0

    def test_cos(self):
        import math
        from numpypy import array, cos

        a = array([0, 1, 2, 3, math.pi, math.pi*1.5, math.pi*2])
        b = cos(a)
        for i in range(len(a)):
            assert b[i] == math.cos(a[i])

    def test_tan(self):
        import math
        from numpypy import array, tan

        a = array([0, 1, 2, 3, math.pi, math.pi*1.5, math.pi*2])
        b = tan(a)
        for i in range(len(a)):
            assert b[i] == math.tan(a[i])

    def test_arcsin(self):
        import math
        from numpypy import array, arcsin

        a = array([-1, -0.5, -0.33, 0, 0.33, 0.5, 1])
        b = arcsin(a)
        for i in range(len(a)):
            assert b[i] == math.asin(a[i])

        a = array([-10, -1.5, -1.01, 1.01, 1.5, 10, float('nan'), float('inf'), float('-inf')])
        b = arcsin(a)
        for f in b:
            assert math.isnan(f)

    def test_arccos(self):
        import math
        from numpypy import array, arccos

        a = array([-1, -0.5, -0.33, 0, 0.33, 0.5, 1])
        b = arccos(a)
        for i in range(len(a)):
            assert b[i] == math.acos(a[i])

        a = array([-10, -1.5, -1.01, 1.01, 1.5, 10, float('nan'), float('inf'), float('-inf')])
        b = arccos(a)
        for f in b:
            assert math.isnan(f)

    def test_arctan(self):
        import math
        from numpypy import array, arctan

        a = array([-3, -2, -1, 0, 1, 2, 3, float('inf'), float('-inf')])
        b = arctan(a)
        for i in range(len(a)):
            assert b[i] == math.atan(a[i])

        a = array([float('nan')])
        b = arctan(a)
        assert math.isnan(b[0])

    def test_arctan2(self):
        import math
        from numpypy import array, arctan2

        # From the numpy documentation
        assert (
            arctan2(
                [0.,  0.,           1.,          -1., float('inf'),  float('inf')],
                [0., -0., float('inf'), float('inf'), float('inf'), float('-inf')]) ==
            [0.,  math.pi,  0., -0.,  math.pi/4, 3*math.pi/4]).all()

        a = array([float('nan')])
        b = arctan2(a, 0)
        assert math.isnan(b[0])

    def test_sinh(self):
        import math
        from numpypy import array, sinh

        a = array([-1, 0, 1, float('inf'), float('-inf')])
        b = sinh(a)
        for i in range(len(a)):
            assert b[i] == math.sinh(a[i])

    def test_cosh(self):
        import math
        from numpypy import array, cosh

        a = array([-1, 0, 1, float('inf'), float('-inf')])
        b = cosh(a)
        for i in range(len(a)):
            assert b[i] == math.cosh(a[i])

    def test_tanh(self):
        import math
        from numpypy import array, tanh

        a = array([-1, 0, 1, float('inf'), float('-inf')])
        b = tanh(a)
        for i in range(len(a)):
            assert b[i] == math.tanh(a[i])

    def test_arcsinh(self):
        import math
        from numpypy import arcsinh

        for v in [float('inf'), float('-inf'), 1.0, math.e]:
            assert math.asinh(v) == arcsinh(v)
        assert math.isnan(arcsinh(float("nan")))

    def test_arccosh(self):
        import math
        from numpypy import arccosh

        for v in [1.0, 1.1, 2]:
            assert math.acosh(v) == arccosh(v)
        for v in [-1.0, 0, .99]:
            assert math.isnan(arccosh(v))

    def test_arctanh(self):
        import math
        from numpypy import arctanh

        for v in [.99, .5, 0, -.5, -.99]:
            assert math.atanh(v) == arctanh(v)
        for v in [2.0, -2.0]:
            assert math.isnan(arctanh(v))
        for v in [1.0, -1.0]:
            assert arctanh(v) == math.copysign(float("inf"), v)

    def test_sqrt(self):
        import math
        from numpypy import sqrt

        nan, inf = float("nan"), float("inf")
        data = [1, 2, 3, inf]
        results = [math.sqrt(1), math.sqrt(2), math.sqrt(3), inf]
        assert (sqrt(data) == results).all()
        assert math.isnan(sqrt(-1))
        assert math.isnan(sqrt(nan))

    def test_square(self):
        import math
        from numpypy import square

        nan, inf, ninf = float("nan"), float("inf"), float("-inf")

        assert math.isnan(square(nan))
        assert math.isinf(square(inf))
        assert math.isinf(square(ninf))
        assert square(ninf) > 0
        assert [square(x) for x in range(-5, 5)] == [x*x for x in range(-5, 5)]
        assert math.isinf(square(1e300))

    def test_radians(self):
        import math
        from numpypy import radians, array
        a = array([
            -181, -180, -179,
            181, 180, 179,
            359, 360, 361,
            400, -1, 0, 1,
            float('inf'), float('-inf')])
        b = radians(a)
        for i in range(len(a)):
            assert b[i] == math.radians(a[i])

    def test_deg2rad(self):
        import math
        from numpypy import deg2rad, array
        a = array([
            -181, -180, -179,
            181, 180, 179,
            359, 360, 361,
            400, -1, 0, 1,
            float('inf'), float('-inf')])
        b = deg2rad(a)
        for i in range(len(a)):
            assert b[i] == math.radians(a[i])

    def test_degrees(self):
        import math
        from numpypy import degrees, array
        a = array([
            -181, -180, -179,
            181, 180, 179,
            359, 360, 361,
            400, -1, 0, 1,
            float('inf'), float('-inf')])
        b = degrees(a)
        for i in range(len(a)):
            assert b[i] == math.degrees(a[i])

    def test_rad2deg(self):
        import math
        from numpypy import rad2deg, array
        a = array([
            -181, -180, -179,
            181, 180, 179,
            359, 360, 361,
            400, -1, 0, 1,
            float('inf'), float('-inf')])
        b = rad2deg(a)
        for i in range(len(a)):
            assert b[i] == math.degrees(a[i])

    def test_reduce_errors(self):
        from numpypy import sin, add, maximum, zeros

        raises(ValueError, sin.reduce, [1, 2, 3])
        assert add.reduce(1) == 1

        assert list(maximum.reduce(zeros((2, 0)), axis=0)) == []
        raises(ValueError, maximum.reduce, zeros((2, 0)), axis=None)
        raises(ValueError, maximum.reduce, zeros((2, 0)), axis=1)

    def test_reduce_1d(self):
        from numpypy import array, add, maximum, less, float16, complex64

        assert less.reduce([5, 4, 3, 2, 1])
        assert add.reduce([1, 2, 3]) == 6
        assert maximum.reduce([1]) == 1
        assert maximum.reduce([1, 2, 3]) == 3
        raises(ValueError, maximum.reduce, [])

        assert add.reduce(array([True, False] * 200)) == 200
        assert add.reduce(array([True, False] * 200, dtype='int8')) == 200
        assert add.reduce(array([True, False] * 200), dtype='int8') == -56
        assert type(add.reduce(array([True, False] * 200, dtype='float16'))) is float16
        assert type(add.reduce(array([True, False] * 200, dtype='complex64'))) is complex64

    def test_reduceND(self):
        from numpypy import add, arange
        a = arange(12).reshape(3, 4)
        assert (add.reduce(a, 0) == [12, 15, 18, 21]).all()
        assert (add.reduce(a, 1) == [6.0, 22.0, 38.0]).all()
        raises(ValueError, add.reduce, a, 2)

    def test_reduce_keepdims(self):
        from numpypy import add, arange
        a = arange(12).reshape(3, 4)
        b = add.reduce(a, 0, keepdims=True)
        assert b.shape == (1, 4)
        assert (add.reduce(a, 0, keepdims=True) == [12, 15, 18, 21]).all()

    def test_bitwise(self):
        from numpypy import bitwise_and, bitwise_or, bitwise_xor, arange, array
        a = arange(6).reshape(2, 3)
        assert (a & 1 == [[0, 1, 0], [1, 0, 1]]).all()
        assert (a & 1 == bitwise_and(a, 1)).all()
        assert (a | 1 == [[1, 1, 3], [3, 5, 5]]).all()
        assert (a | 1 == bitwise_or(a, 1)).all()
        assert (a ^ 3 == bitwise_xor(a, 3)).all()
        raises(TypeError, 'array([1.0]) & 1')

    def test_unary_bitops(self):
        from numpypy import bitwise_not, invert, array
        a = array([1, 2, 3, 4])
        assert (~a == [-2, -3, -4, -5]).all()
        assert (bitwise_not(a) == ~a).all()
        assert (invert(a) == ~a).all()
        assert invert(True) == False
        assert invert(False) == True

    def test_shift(self):
        from numpypy import left_shift, right_shift, dtype

        assert (left_shift([5, 1], [2, 13]) == [20, 2**13]).all()
        assert (right_shift(10, range(5)) == [10, 5, 2, 1, 0]).all()
        bool_ = dtype('bool').type
        assert left_shift(bool(1), 3) == left_shift(1, 3)
        assert right_shift(bool(1), 3) == right_shift(1, 3)

    def test_comparisons(self):
        import operator
        from numpypy import (equal, not_equal, less, less_equal, greater,
                            greater_equal, arange)

        for ufunc, func in [
            (equal, operator.eq),
            (not_equal, operator.ne),
            (less, operator.lt),
            (less_equal, operator.le),
            (greater, operator.gt),
            (greater_equal, operator.ge),
        ]:
            for a, b in [
                (3, 3),
                (3, 4),
                (4, 3),
                (3.0, 3.0),
                (3.0, 3.5),
                (3.5, 3.0),
                (3.0, 3),
                (3, 3.0),
                (3.5, 3),
                (3, 3.5),
            ]:
                assert ufunc(a, b) == func(a, b)
        c = arange(10)
        val = c == 'abcdefg'
        assert val == False

    def test_count_nonzero(self):
        from numpypy import count_nonzero
        assert count_nonzero(0) == 0
        assert count_nonzero(1) == 1
        assert count_nonzero([]) == 0
        assert count_nonzero([1, 2, 0]) == 2
        assert count_nonzero([[1, 2, 0], [1, 0, 2]]) == 4

    def test_true_divide_2(self):
        from numpypy import arange, array, true_divide
        assert (true_divide(arange(3), array([2, 2, 2])) == array([0, 0.5, 1])).all()

    def test_isnan_isinf(self):
        from numpypy import isnan, isinf, array, dtype
        assert isnan(float('nan'))
        assert not isnan(3)
        assert not isinf(3)
        assert isnan(dtype('float64').type(float('nan')))
        assert not isnan(3)
        assert isinf(float('inf'))
        assert not isnan(3.5)
        assert not isinf(3.5)
        assert not isnan(float('inf'))
        assert not isinf(float('nan'))
        assert (isnan(array([0.2, float('inf'), float('nan')])) == [False, False, True]).all()
        assert (isinf(array([0.2, float('inf'), float('nan')])) == [False, True, False]).all()
        assert isinf(array([0.2])).dtype.kind == 'b'

    def test_logical_ops(self):
        from numpypy import logical_and, logical_or, logical_xor, logical_not

        assert (logical_and([True, False , True, True], [1, 1, 3, 0])
                == [True, False, True, False]).all()
        assert (logical_or([True, False, True, False], [1, 2, 0, 0])
                == [True, True, True, False]).all()
        assert (logical_xor([True, False, True, False], [1, 2, 0, 0])
                == [False, True, True, False]).all()
        assert (logical_not([True, False]) == [False, True]).all()

    def test_logn(self):
        import math
        from numpypy import log, log2, log10

        for log_func, base in [(log, math.e), (log2, 2), (log10, 10)]:
            for v in [float('-nan'), float('-inf'), -1, float('nan')]:
                assert math.isnan(log_func(v))
            for v in [-0.0, 0.0]:
                assert log_func(v) == float("-inf")
            assert log_func(float('inf')) == float('inf')
            assert (log_func([1, base]) == [0, 1]).all()

    def test_log1p(self):
        import math
        from numpypy import log1p

        for v in [float('-nan'), float('-inf'), -2, float('nan')]:
            assert math.isnan(log1p(v))
        for v in [-1]:
            assert log1p(v) == float("-inf")
        assert log1p(float('inf')) == float('inf')
        assert (log1p([0, 1e-50, math.e - 1]) == [0, 1e-50, 1]).all()

    def test_power_float(self):
        import math
        from numpypy import power, array
        a = array([1., 2., 3.])
        b = power(a, 3)
        for i in range(len(a)):
            assert b[i] == a[i] ** 3

        a = array([1., 2., 3.])
        b = array([1., 2., 3.])
        c = power(a, b)
        for i in range(len(a)):
            assert c[i] == a[i] ** b[i]

        assert power(2, float('inf')) == float('inf')
        assert power(float('inf'), float('inf')) == float('inf')
        assert power(12345.0, 12345.0) == float('inf')
        assert power(-12345.0, 12345.0) == float('-inf')
        assert power(-12345.0, 12346.0) == float('inf')
        assert math.isnan(power(-1, 1.1))
        assert math.isnan(power(-1, -1.1))
        assert power(-2.0, -1) == -0.5
        assert power(-2.0, -2) == 0.25
        assert power(12345.0, -12345.0) == 0
        assert power(float('-inf'), 2) == float('inf')
        assert power(float('-inf'), 2.5) == float('inf')
        assert power(float('-inf'), 3) == float('-inf')

    def test_power_int(self):
        import math
        from numpypy import power, array
        a = array([1, 2, 3])
        b = power(a, 3)
        for i in range(len(a)):
            assert b[i] == a[i] ** 3

        a = array([1, 2, 3])
        b = array([1, 2, 3])
        c = power(a, b)
        for i in range(len(a)):
            assert c[i] == a[i] ** b[i]

        # assert power(12345, 12345) == -9223372036854775808
        # assert power(-12345, 12345) == -9223372036854775808
        # assert power(-12345, 12346) == -9223372036854775808
        assert power(2, 0) == 1
        assert power(2, -1) == 0
        assert power(2, -2) == 0
        assert power(-2, -1) == 0
        assert power(-2, -2) == 0
        assert power(12345, -12345) == 0

    def test_floordiv(self):
        from numpypy import floor_divide, array
        import math
        a = array([1., 2., 3., 4., 5., 6., 6.01])
        b = floor_divide(a, 2.5)
        for i in range(len(a)):
            assert b[i] == a[i] // 2.5

        a = array([10+10j, -15-100j, 0+10j], dtype=complex)
        b = floor_divide(a, 2.5)
        for i in range(len(a)):
            assert b[i] == a[i] // 2.5
        b = floor_divide(a, 2.5+3j)
        #numpy returns (a.real*b.real + a.imag*b.imag) / abs(b)**2
        expect = [3., -23., 1.]
        for i in range(len(a)):
            assert b[i] == expect[i]
        b = floor_divide(a[0], 0.)
        assert math.isnan(b.real)
        assert b.imag == 0.

    def test_logaddexp(self):
        import math
        import sys
        float_max, float_min = sys.float_info.max, sys.float_info.min
        from numpypy import logaddexp

        # From the numpy documentation
        prob1 = math.log(1e-50)
        prob2 = math.log(2.5e-50)
        prob12 = logaddexp(prob1, prob2)
        assert math.fabs(-113.87649168120691 - prob12) < 0.000000000001

        assert logaddexp(0, 0) == math.log(2)
        assert logaddexp(float('-inf'), 0) == 0
        assert logaddexp(float_max, float_max) == float_max
        assert logaddexp(float_min, float_min) == math.log(2)

        assert math.isnan(logaddexp(float('nan'), 1))
        assert math.isnan(logaddexp(1, float('nan')))
        assert math.isnan(logaddexp(float('nan'), float('inf')))
        assert math.isnan(logaddexp(float('inf'), float('nan')))
        assert logaddexp(float('-inf'), float('-inf')) == float('-inf')
        assert logaddexp(float('-inf'), float('inf')) == float('inf')
        assert logaddexp(float('inf'), float('-inf')) == float('inf')
        assert logaddexp(float('inf'), float('inf')) == float('inf')

    def test_logaddexp2(self):
        import math
        import sys
        float_max, float_min = sys.float_info.max, sys.float_info.min
        from numpypy import logaddexp2
        log2 = math.log(2)

        # From the numpy documentation
        prob1 = math.log(1e-50) / log2
        prob2 = math.log(2.5e-50) / log2
        prob12 = logaddexp2(prob1, prob2)
        assert math.fabs(-164.28904982231052 - prob12) < 0.000000000001

        assert logaddexp2(0, 0) == 1
        assert logaddexp2(float('-inf'), 0) == 0
        assert logaddexp2(float_max, float_max) == float_max
        assert logaddexp2(float_min, float_min) == 1.0

        assert math.isnan(logaddexp2(float('nan'), 1))
        assert math.isnan(logaddexp2(1, float('nan')))
        assert math.isnan(logaddexp2(float('nan'), float('inf')))
        assert math.isnan(logaddexp2(float('inf'), float('nan')))
        assert logaddexp2(float('-inf'), float('-inf')) == float('-inf')
        assert logaddexp2(float('-inf'), float('inf')) == float('inf')
        assert logaddexp2(float('inf'), float('-inf')) == float('inf')
        assert logaddexp2(float('inf'), float('inf')) == float('inf')

    def test_accumulate(self):
        from numpypy import add, subtract, multiply, divide, arange, dtype
        assert (add.accumulate([2, 3, 5]) == [2, 5, 10]).all()
        assert (multiply.accumulate([2, 3, 5]) == [2, 6, 30]).all()
        a = arange(4).reshape(2,2)
        b = add.accumulate(a, axis=0)
        assert (b == [[0, 1], [2, 4]]).all()
        b = add.accumulate(a, 1)
        assert (b == [[0, 1], [2, 5]]).all()
        b = add.accumulate(a) #default axis is 0
        assert (b == [[0, 1], [2, 4]]).all()
        # dtype
        a = arange(0, 3, 0.5).reshape(2, 3)
        b = add.accumulate(a, dtype=int, axis=1)
        print b
        assert (b == [[0, 0, 1], [1, 3, 5]]).all()
        assert b.dtype == int
        assert add.accumulate([True]*200)[-1] == 200
        assert add.accumulate([True]*200).dtype == dtype('int')
        assert subtract.accumulate([True]*200).dtype == dtype('bool')
        assert divide.accumulate([True]*200).dtype == dtype('int8')

    def test_noncommutative_reduce_accumulate(self):
        import numpypy as np
        tosubtract = np.arange(5)
        todivide = np.array([2.0, 0.5, 0.25])
        assert np.subtract.reduce(tosubtract) == -10
        assert np.divide.reduce(todivide) == 16.0
        assert (np.subtract.accumulate(tosubtract) ==
                np.array([0, -1, -3, -6, -10])).all()
        assert (np.divide.accumulate(todivide) ==
                np.array([2., 4., 16.])).all()

    def test_outer(self):
        import numpy as np
        from numpypy import absolute
        exc = raises(ValueError, np.absolute.outer, [-1, -2])
        assert exc.value[0] == 'outer product only supported for binary functions'

    def test_promotion(self):
        import numpy as np
        assert np.add(np.float16(0), np.int16(0)).dtype == np.float32
        assert np.add(np.float16(0), np.int32(0)).dtype == np.float64
        assert np.add(np.float16(0), np.int64(0)).dtype == np.float64
        assert np.add(np.float16(0), np.float32(0)).dtype == np.float32
        assert np.add(np.float16(0), np.float64(0)).dtype == np.float64
        assert np.add(np.float16(0), np.longdouble(0)).dtype == np.longdouble
        assert np.add(np.float16(0), np.complex64(0)).dtype == np.complex64
        assert np.add(np.float16(0), np.complex128(0)).dtype == np.complex128
