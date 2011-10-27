from pypy.conftest import gettestobjspace
from pypy.module.micronumpy import interp_dtype
from pypy.module.micronumpy.interp_numarray import NDimArray, Scalar
from pypy.module.micronumpy.interp_ufuncs import (find_binop_result_dtype,
        find_unaryop_result_dtype)


class BaseNumpyAppTest(object):
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['micronumpy'])

class TestSignature(object):
    def test_binop_signature(self, space):
        float64_dtype = space.fromcache(interp_dtype.W_Float64Dtype)

        ar = NDimArray(10, [10], dtype=float64_dtype)
        v1 = ar.descr_add(space, ar)
        v2 = ar.descr_add(space, Scalar(float64_dtype, 2.0))
        assert v1.signature is not v2.signature
        v3 = ar.descr_add(space, Scalar(float64_dtype, 1.0))
        assert v2.signature is v3.signature
        v4 = ar.descr_add(space, ar)
        assert v1.signature is v4.signature

        bool_ar = NDimArray(10, [10], dtype=space.fromcache(interp_dtype.W_BoolDtype))
        v5 = ar.descr_add(space, bool_ar)
        assert v5.signature is not v1.signature
        assert v5.signature is not v2.signature
        v6 = ar.descr_add(space, bool_ar)
        assert v5.signature is v6.signature

    def test_slice_signature(self, space):
        ar = NDimArray(10, [10], dtype=space.fromcache(interp_dtype.W_Float64Dtype))
        v1 = ar.descr_getitem(space, space.wrap(slice(1, 5, 1)))
        v2 = ar.descr_getitem(space, space.wrap(slice(4, 6, 1)))
        assert v1.signature is v2.signature

        v3 = ar.descr_add(space, v1)
        v4 = ar.descr_add(space, v2)
        assert v3.signature is v4.signature

class TestUfuncCoerscion(object):
    def test_binops(self, space):
        bool_dtype = space.fromcache(interp_dtype.W_BoolDtype)
        int8_dtype = space.fromcache(interp_dtype.W_Int8Dtype)
        int32_dtype = space.fromcache(interp_dtype.W_Int32Dtype)
        float64_dtype = space.fromcache(interp_dtype.W_Float64Dtype)

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
        bool_dtype = space.fromcache(interp_dtype.W_BoolDtype)
        int8_dtype = space.fromcache(interp_dtype.W_Int8Dtype)
        uint8_dtype = space.fromcache(interp_dtype.W_UInt8Dtype)
        int16_dtype = space.fromcache(interp_dtype.W_Int16Dtype)
        uint16_dtype = space.fromcache(interp_dtype.W_UInt16Dtype)
        int32_dtype = space.fromcache(interp_dtype.W_Int32Dtype)
        uint32_dtype = space.fromcache(interp_dtype.W_UInt32Dtype)
        long_dtype = space.fromcache(interp_dtype.W_LongDtype)
        ulong_dtype = space.fromcache(interp_dtype.W_ULongDtype)
        int64_dtype = space.fromcache(interp_dtype.W_Int64Dtype)
        uint64_dtype = space.fromcache(interp_dtype.W_UInt64Dtype)
        float32_dtype = space.fromcache(interp_dtype.W_Float32Dtype)
        float64_dtype = space.fromcache(interp_dtype.W_Float64Dtype)

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
