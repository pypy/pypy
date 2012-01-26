from pypy.conftest import gettestobjspace
from pypy.module.micronumpy.interp_dtype import get_dtype_cache
from pypy.module.micronumpy.interp_numarray import W_NDimArray, Scalar
from pypy.module.micronumpy.interp_ufuncs import (find_binop_result_dtype,
        find_unaryop_result_dtype)
from pypy.module.micronumpy.interp_boxes import W_Float64Box
from pypy.conftest import option
import sys

class BaseNumpyAppTest(object):
    def setup_class(cls):
        if option.runappdirect:
            if '__pypy__' not in sys.builtin_module_names:
                import numpy
                sys.modules['numpypy'] = numpy
                sys.modules['_numpypy'] = numpy
        cls.space = gettestobjspace(usemodules=['micronumpy'])

class TestSignature(object):
    def test_binop_signature(self, space):
        float64_dtype = get_dtype_cache(space).w_float64dtype
        bool_dtype = get_dtype_cache(space).w_booldtype

        ar = W_NDimArray(10, [10], dtype=float64_dtype)
        ar2 = W_NDimArray(10, [10], dtype=float64_dtype)
        v1 = ar.descr_add(space, ar)
        v2 = ar.descr_add(space, Scalar(float64_dtype, W_Float64Box(2.0)))
        sig1 = v1.find_sig()
        sig2 = v2.find_sig()
        assert v1 is not v2
        assert sig1.left.iter_no == sig1.right.iter_no
        assert sig2.left.iter_no != sig2.right.iter_no
        assert sig1.left.array_no == sig1.right.array_no
        sig1b = ar2.descr_add(space, ar).find_sig()
        assert sig1b.left.array_no != sig1b.right.array_no
        assert sig1b is not sig1
        v3 = ar.descr_add(space, Scalar(float64_dtype, W_Float64Box(1.0)))
        sig3 = v3.find_sig()
        assert sig2 is sig3
        v4 = ar.descr_add(space, ar)
        assert v1.find_sig() is v4.find_sig()

        bool_ar = W_NDimArray(10, [10], dtype=bool_dtype)
        v5 = ar.descr_add(space, bool_ar)
        assert v5.find_sig() is not v1.find_sig()
        assert v5.find_sig() is not v2.find_sig()
        v6 = ar.descr_add(space, bool_ar)
        assert v5.find_sig() is v6.find_sig()
        v7 = v6.descr_add(space, v6)
        sig7 = v7.find_sig()
        assert sig7.left.left.iter_no == sig7.right.left.iter_no
        assert sig7.left.left.iter_no != sig7.right.right.iter_no
        assert sig7.left.right.iter_no == sig7.right.right.iter_no
        v1.forced_result = ar
        assert v1.find_sig() is not sig1

    def test_slice_signature(self, space):
        float64_dtype = get_dtype_cache(space).w_float64dtype

        ar = W_NDimArray(10, [10], dtype=float64_dtype)
        v1 = ar.descr_getitem(space, space.wrap(slice(1, 3, 1)))
        v2 = ar.descr_getitem(space, space.wrap(slice(4, 6, 1)))
        assert v1.find_sig() is v2.find_sig()

        v3 = v2.descr_add(space, v1)
        v4 = v1.descr_add(space, v2)
        assert v3.find_sig() is v4.find_sig()
        v5 = ar.descr_add(space, ar).descr_getitem(space, space.wrap(slice(1, 3, 1)))
        v6 = ar.descr_add(space, ar).descr_getitem(space, space.wrap(slice(1, 4, 1)))
        assert v5.find_sig() is v6.find_sig()

class TestUfuncCoerscion(object):
    def test_binops(self, space):
        bool_dtype = get_dtype_cache(space).w_booldtype
        int8_dtype = get_dtype_cache(space).w_int8dtype
        int32_dtype = get_dtype_cache(space).w_int32dtype
        float64_dtype = get_dtype_cache(space).w_float64dtype

        # Basic pairing
        assert find_binop_result_dtype(space, bool_dtype, bool_dtype) is bool_dtype
        assert find_binop_result_dtype(space, bool_dtype, float64_dtype) is float64_dtype
        assert find_binop_result_dtype(space, float64_dtype, bool_dtype) is float64_dtype
        assert find_binop_result_dtype(space, int32_dtype, int8_dtype) is int32_dtype
        assert find_binop_result_dtype(space, int32_dtype, bool_dtype) is int32_dtype

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
        assert find_unaryop_result_dtype(space, bool_dtype, promote_to_float=True) is float32_dtype # will be float16 if we ever put that in
        assert find_unaryop_result_dtype(space, int8_dtype, promote_to_float=True) is float32_dtype # will be float16 if we ever put that in
        assert find_unaryop_result_dtype(space, uint8_dtype, promote_to_float=True) is float32_dtype # will be float16 if we ever put that in
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
