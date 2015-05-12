from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest
from pypy.module.micronumpy.descriptor import get_dtype_cache
from pypy.module.micronumpy.casting import (
    find_unaryop_result_dtype, find_binop_result_dtype, can_cast_type)


class AppTestNumSupport(BaseNumpyAppTest):
    def test_result_type(self):
        import numpy as np
        exc = raises(ValueError, np.result_type)
        assert str(exc.value) == "at least one array or dtype is required"
        exc = raises(TypeError, np.result_type, a=2)
        assert str(exc.value) == "result_type() takes no keyword arguments"
        assert np.result_type(True) is np.dtype('bool')
        assert np.result_type(1) is np.dtype('int')
        assert np.result_type(1.) is np.dtype('float64')
        assert np.result_type(1+2j) is np.dtype('complex128')
        assert np.result_type(1, 1.) is np.dtype('float64')
        assert np.result_type(np.array([1, 2])) is np.dtype('int')
        assert np.result_type(np.array([1, 2]), 1, 1+2j) is np.dtype('complex128')
        assert np.result_type(np.array([1, 2]), 1, 'float64') is np.dtype('float64')
        assert np.result_type(np.array([1, 2]), 1, None) is np.dtype('float64')

    def test_can_cast(self):
        import numpy as np

        assert np.can_cast(np.int32, np.int64)
        assert np.can_cast(np.float64, complex)
        assert not np.can_cast(np.complex64, float)
        assert np.can_cast(np.bool_, np.bool_)

        assert np.can_cast('i8', 'f8')
        assert not np.can_cast('i8', 'f4')
        assert np.can_cast('i4', 'S11')

        assert np.can_cast('i8', 'i8', 'no')
        assert not np.can_cast('<i8', '>i8', 'no')

        assert np.can_cast('<i8', '>i8', 'equiv')
        assert not np.can_cast('<i4', '>i8', 'equiv')

        assert np.can_cast('<i4', '>i8', 'safe')
        assert not np.can_cast('<i8', '>i4', 'safe')

        assert np.can_cast('<i8', '>i4', 'same_kind')
        assert not np.can_cast('<i8', '>u4', 'same_kind')

        assert np.can_cast('<i8', '>u4', 'unsafe')

        assert np.can_cast('bool', 'S5')
        assert not np.can_cast('bool', 'S4')

        assert np.can_cast('b', 'S4')
        assert not np.can_cast('b', 'S3')

        assert np.can_cast('u1', 'S3')
        assert not np.can_cast('u1', 'S2')
        assert np.can_cast('u2', 'S5')
        assert not np.can_cast('u2', 'S4')
        assert np.can_cast('u4', 'S10')
        assert not np.can_cast('u4', 'S9')
        assert np.can_cast('u8', 'S20')
        assert not np.can_cast('u8', 'S19')

        assert np.can_cast('i1', 'S4')
        assert not np.can_cast('i1', 'S3')
        assert np.can_cast('i2', 'S6')
        assert not np.can_cast('i2', 'S5')
        assert np.can_cast('i4', 'S11')
        assert not np.can_cast('i4', 'S10')
        assert np.can_cast('i8', 'S21')
        assert not np.can_cast('i8', 'S20')

        assert np.can_cast('bool', 'S5')
        assert not np.can_cast('bool', 'S4')

        assert np.can_cast('b', 'U4')
        assert not np.can_cast('b', 'U3')

        assert np.can_cast('u1', 'U3')
        assert not np.can_cast('u1', 'U2')
        assert np.can_cast('u2', 'U5')
        assert not np.can_cast('u2', 'U4')
        assert np.can_cast('u4', 'U10')
        assert not np.can_cast('u4', 'U9')
        assert np.can_cast('u8', 'U20')
        assert not np.can_cast('u8', 'U19')

        assert np.can_cast('i1', 'U4')
        assert not np.can_cast('i1', 'U3')
        assert np.can_cast('i2', 'U6')
        assert not np.can_cast('i2', 'U5')
        assert np.can_cast('i4', 'U11')
        assert not np.can_cast('i4', 'U10')
        assert np.can_cast('i8', 'U21')
        assert not np.can_cast('i8', 'U20')

        raises(TypeError, np.can_cast, 'i4', None)
        raises(TypeError, np.can_cast, None, 'i4')

    def test_can_cast_scalar(self):
        import numpy as np
        assert np.can_cast(True, np.bool_)
        assert np.can_cast(True, np.int8)
        assert not np.can_cast(0, np.bool_)
        assert np.can_cast(127, np.int8)
        assert not np.can_cast(128, np.int8)
        assert np.can_cast(128, np.int16)

        assert np.can_cast(np.float32('inf'), np.float32)
        assert np.can_cast(float('inf'), np.float32)  # XXX: False in CNumPy?!
        assert np.can_cast(3.3e38, np.float32)
        assert not np.can_cast(3.4e38, np.float32)

        assert np.can_cast(1 + 2j, np.complex64)
        assert not np.can_cast(1 + 1e50j, np.complex64)
        assert np.can_cast(1., np.complex64)
        assert not np.can_cast(1e50, np.complex64)

    def test_min_scalar_type(self):
        import numpy as np
        assert np.min_scalar_type(2**8 - 1) == np.dtype('uint8')
        assert np.min_scalar_type(2**64 - 1) == np.dtype('uint64')
        # XXX: np.asarray(2**64) fails with OverflowError
        # assert np.min_scalar_type(2**64) == np.dtype('O')

def test_can_cast_same_type(space):
    dt_bool = get_dtype_cache(space).w_booldtype
    assert can_cast_type(space, dt_bool, dt_bool, 'no')
    assert can_cast_type(space, dt_bool, dt_bool, 'equiv')
    assert can_cast_type(space, dt_bool, dt_bool, 'safe')
    assert can_cast_type(space, dt_bool, dt_bool, 'same_kind')
    assert can_cast_type(space, dt_bool, dt_bool, 'unsafe')


class TestCoercion(object):
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
