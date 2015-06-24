import pypy.module._cffi_backend.misc    # side-effects


class AppTestUnsafeOp:
    spaceconfig = dict(usemodules=['pypystm', '_cffi_backend'])

    def test_unsafe_write_char(self):
        import pypystm, _cffi_backend
        BChar = _cffi_backend.new_primitive_type('char')
        BCharP = _cffi_backend.new_pointer_type(BChar)
        x = _cffi_backend.newp(_cffi_backend.new_array_type(BCharP, 2))
        pypystm.unsafe_write(x, 0, 'A')
        pypystm.unsafe_write(x, 1, '\xAA')
        assert x[0] == 'A'
        assert x[1] == '\xAA'
        assert pypystm.unsafe_read(x, 1) == '\xAA'

    def test_unsafe_write_int32(self):
        import pypystm, _cffi_backend
        BInt32 = _cffi_backend.new_primitive_type('int32_t')
        BInt32P = _cffi_backend.new_pointer_type(BInt32)
        x = _cffi_backend.newp(_cffi_backend.new_array_type(BInt32P, 2))
        pypystm.unsafe_write(x, 0, -0x01020304)
        pypystm.unsafe_write(x, 1, -0x05060708)
        assert x[0] == -0x01020304
        assert x[1] == -0x05060708
        assert pypystm.unsafe_read(x, 1) == -0x05060708

    def test_unsafe_write_uint64(self):
        import pypystm, _cffi_backend
        BUInt64 = _cffi_backend.new_primitive_type('uint64_t')
        BUInt64P = _cffi_backend.new_pointer_type(BUInt64)
        x = _cffi_backend.newp(_cffi_backend.new_array_type(BUInt64P, 2))
        pypystm.unsafe_write(x, 0, 0x0102030411223344)
        pypystm.unsafe_write(x, 1, 0xF506070855667788)
        assert x[0] == 0x0102030411223344
        assert x[1] == 0xF506070855667788
        assert pypystm.unsafe_read(x, 1) == 0xF506070855667788

    def test_unsafe_write_unsupported_case(self):
        import pypystm, _cffi_backend
        BUniChar = _cffi_backend.new_primitive_type('wchar_t')
        BUniCharP = _cffi_backend.new_pointer_type(BUniChar)
        x = _cffi_backend.newp(_cffi_backend.new_array_type(BUniCharP, 2))
        raises(TypeError, pypystm.unsafe_write, x, 0, u'X')
        raises(TypeError, pypystm.unsafe_read, x, 1)

    def test_unsafe_write_float(self):
        import pypystm, _cffi_backend
        BFloat = _cffi_backend.new_primitive_type('float')
        BFloatP = _cffi_backend.new_pointer_type(BFloat)
        x = _cffi_backend.newp(_cffi_backend.new_array_type(BFloatP, 2))
        pypystm.unsafe_write(x, 0, 12.25)
        pypystm.unsafe_write(x, 1, -42.0)
        assert x[0] == 12.25
        assert x[1] == -42.0
        assert pypystm.unsafe_read(x, 1) == -42.0

    def test_unsafe_write_double(self):
        import pypystm, _cffi_backend
        BDouble = _cffi_backend.new_primitive_type('double')
        BDoubleP = _cffi_backend.new_pointer_type(BDouble)
        x = _cffi_backend.newp(_cffi_backend.new_array_type(BDoubleP, 2))
        pypystm.unsafe_write(x, 0, 12.25)
        pypystm.unsafe_write(x, 1, -42.0)
        assert x[0] == 12.25
        assert x[1] == -42.0
        assert pypystm.unsafe_read(x, 1) == -42.0
