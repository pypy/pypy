from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest


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
