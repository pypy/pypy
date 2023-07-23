from .support import HPyTest, DefaultExtensionTemplate

class HPyLongTemplate(DefaultExtensionTemplate):
    def DEFINE_Long_From(self, type, api_suffix, val):
        self.EXPORT("from_{type}_{val}".format(type=type, val=val))
        return """
            HPyDef_METH(from_{type}_{val}, "from_{type}_{val}", HPyFunc_NOARGS)
            static HPy from_{type}_{val}_impl(HPyContext *ctx, HPy self)
            {{
                {type} a = {val};
                return HPyLong_From{api_suffix}(ctx, a);
            }}
        """.format(type=type, val=val, api_suffix=api_suffix)

    def DEFINE_Long_As(self, type, api_suffix, from_suffix=None):
        self.EXPORT("as_{api_suffix}".format(api_suffix=api_suffix))
        if not from_suffix:
            from_suffix = api_suffix
        return """
            HPyDef_METH(as_{api_suffix}, "as_{api_suffix}", HPyFunc_O)
            static HPy as_{api_suffix}_impl(HPyContext *ctx, HPy self, HPy arg)
            {{
                {type} a = HPyLong_As{api_suffix}(ctx, arg);
                if (a == (({type})-1) && HPyErr_Occurred(ctx))
                    return HPy_NULL;
                return HPyLong_From{from_suffix}(ctx, a * 2);
            }}
        """.format(type=type, api_suffix=api_suffix, from_suffix=from_suffix)

class TestLong(HPyTest):

    ExtensionTemplate = HPyLongTemplate

    def unsigned_long_bits(self):
        """ Return the number of bits in an unsigned long. """
        import struct
        unsigned_long_bytes = len(struct.pack('l', 0))
        return 8 * unsigned_long_bytes

    def magic_int(self, v):
        """ Return an instance of a class that implements __int__
            and returns value v.
        """
        class MagicInt(object):
            def __int__(self):
                return v
        return MagicInt()

    def magic_index(self, v):
        """ Return an instance of a class that implements __index__
            and returns value v.
        """
        class MagicIndex(object):
            def __index__(self):
                return v
        return MagicIndex()

    def python_supports_magic_index(self):
        """ Return True if the Python version is 3.8 or later and thus
            should support calling __index__ in the various HPyLong_As...
            methods.
        """
        import sys
        vi = sys.version_info
        return (vi.major > 3 or (vi.major == 3 and vi.minor >= 8))

    def python_supports_magic_int(self):
        """ Return True if the Python version is 3.9 or earlier and thus
            should support calling __int__ on non-int based types in some
            HPyLong_As... methods.
        """
        import sys
        vi = sys.version_info
        assert vi.major >= 3
        return (vi.major == 3 and vi.minor <= 9)

    def test_Long_FromFixedWidth(self):
        mod = self.make_module("""
            @DEFINE_Long_From(int32_t, Int32_t, INT32_MAX)
            @DEFINE_Long_From(int32_t, Int32_t, INT32_MIN)
            @DEFINE_Long_From(uint32_t, UInt32_t, UINT32_MAX)
            @DEFINE_Long_From(int64_t, Int64_t, INT64_MAX)
            @DEFINE_Long_From(int64_t, Int64_t, INT64_MIN)
            @DEFINE_Long_From(uint64_t, UInt64_t, UINT64_MAX)
            @INIT
        """)
        assert mod.from_int32_t_INT32_MAX() == 2147483647
        assert mod.from_int32_t_INT32_MIN() == -2147483648
        assert mod.from_uint32_t_UINT32_MAX() == 4294967295
        assert mod.from_int64_t_INT64_MAX() == 9223372036854775807
        assert mod.from_int64_t_INT64_MIN() == -9223372036854775808
        assert mod.from_uint64_t_UINT64_MAX() == 18446744073709551615

    def test_Long_FromLong(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_NOARGS)
            static HPy f_impl(HPyContext *ctx, HPy self)
            {
                long a = 500;
                return HPyLong_FromLong(ctx, a);
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f() == 500

    def test_Long_AsFixedWidth(self):
        import pytest
        mod = self.make_module("""
            @DEFINE_Long_As(int32_t, Int32_t)
            @DEFINE_Long_As(uint32_t, UInt32_t)
            @DEFINE_Long_As(uint32_t, UInt32_tMask, UInt32_t)
            @DEFINE_Long_As(int64_t, Int64_t)
            @DEFINE_Long_As(uint64_t, UInt64_t)
            @DEFINE_Long_As(uint64_t, UInt64_tMask, UInt64_t)
            @INIT
        """)

        assert mod.as_Int32_t(45) == 90
        assert mod.as_Int32_t(-45) == -90
        # doubling INT32_MAX is like a left-shift and will result in a negative value
        assert mod.as_Int32_t(2147483647) < 0
        with pytest.raises(TypeError):
            mod.as_Int32_t("this is not a number")
        if self.python_supports_magic_int():
            assert mod.as_Int32_t(self.magic_int(2)) == 4
        if self.python_supports_magic_index():
            assert mod.as_Int32_t(self.magic_index(2)) == 4

        assert mod.as_UInt32_t(45) == 90
        with pytest.raises(OverflowError):
            mod.as_UInt32_t(-45)
        assert mod.as_UInt32_t(2147483647) == 4294967294

        assert mod.as_UInt32_tMask(0xffffffffffffffff) == 0xfffffffe

        assert mod.as_Int64_t(45) == 90
        assert mod.as_Int64_t(-45) == -90
        # doubling INT32_MAX is like a left-shift and will result in a negative value
        assert mod.as_Int64_t(2147483647) == 4294967294
        assert mod.as_Int64_t(9223372036854775807) < 0
        with pytest.raises(TypeError):
            mod.as_Int64_t("this is not a number")

        assert mod.as_UInt64_t(45) == 90
        with pytest.raises(OverflowError):
            mod.as_UInt64_t(-45)
        assert mod.as_UInt64_t(9223372036854775807) == 18446744073709551614

        assert mod.as_UInt64_tMask(0xffffffffffffffffff) == 0xfffffffffffffffe

    def test_Long_AsLong(self):
        import pytest
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                long a = HPyLong_AsLong(ctx, arg);
                if (a == -1 && HPyErr_Occurred(ctx))
                    return HPy_NULL;
                return HPyLong_FromLong(ctx, a * 2);
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f(45) == 90
        with pytest.raises(TypeError):
            mod.f("this is not a number")
        if self.python_supports_magic_int():
            assert mod.f(self.magic_int(2)) == 4
        if self.python_supports_magic_index():
            assert mod.f(self.magic_index(2)) == 4

    def test_Long_FromUnsignedLong(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_NOARGS)
            static HPy f_impl(HPyContext *ctx, HPy self)
            {
                unsigned long a = 500;
                return HPyLong_FromUnsignedLong(ctx, a);
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f() == 500

    def test_Long_AsUnsignedLong(self):
        import pytest
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                unsigned long a = HPyLong_AsUnsignedLong(ctx, arg);
                if ((a == (unsigned long) -1) && HPyErr_Occurred(ctx))
                    return HPy_NULL;
                return HPyLong_FromUnsignedLong(ctx, a);
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f(45) == 45
        with pytest.raises(OverflowError):
            mod.f(-91)
        with pytest.raises(TypeError):
            mod.f("this is not a number")
        with pytest.raises(TypeError):
            mod.f(self.magic_int(2))
        with pytest.raises(TypeError):
            mod.f(self.magic_index(2))

    def test_Long_AsUnsignedLongMask(self):
        import pytest
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                unsigned long a = HPyLong_AsUnsignedLongMask(ctx, arg);
                if ((a == (unsigned long) -1) && HPyErr_Occurred(ctx))
                    return HPy_NULL;
                return HPyLong_FromUnsignedLong(ctx, a);
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f(45) == 45
        assert mod.f(-1) == 2**self.unsigned_long_bits() - 1
        with pytest.raises(TypeError):
            mod.f("this is not a number")
        if self.python_supports_magic_int():
            assert mod.f(self.magic_int(2)) == 2
        if self.python_supports_magic_index():
            assert mod.f(self.magic_index(2)) == 2

    def test_Long_FromLongLong(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_NOARGS)
            static HPy f_impl(HPyContext *ctx, HPy self)
            {
                // take a value which doesn't fit in 32 bit
                long long val = 2147483648;
                return HPyLong_FromLongLong(ctx, val);
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f() == 2147483648

    def test_Long_AsLongLong(self):
        import pytest
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                long long a = HPyLong_AsLongLong(ctx, arg);
                if ((a == (long long) -1) && HPyErr_Occurred(ctx))
                    return HPy_NULL;
                return HPyLong_FromLongLong(ctx, a);
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f(2147483648) == 2147483648
        assert mod.f(-2147483648) == -2147483648
        with pytest.raises(TypeError):
            mod.f("this is not a number")
        if self.python_supports_magic_int():
            assert mod.f(self.magic_int(2)) == 2
        if self.python_supports_magic_index():
            assert mod.f(self.magic_index(2)) == 2

    def test_Long_FromUnsignedLongLong(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_NOARGS)
            static HPy f_impl(HPyContext *ctx, HPy self)
            {
                // take a value which doesn't fit in unsigned 32 bit
                unsigned long long val = 4294967296;
                return HPyLong_FromUnsignedLongLong(ctx, val);
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f() == 4294967296

    def test_Long_AsUnsignedLongLong(self):
        import pytest
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                unsigned long long a = HPyLong_AsUnsignedLongLong(ctx, arg);
                if ((a == (unsigned long long) -1) && HPyErr_Occurred(ctx))
                    return HPy_NULL;
                return HPyLong_FromUnsignedLongLong(ctx, a);
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f(4294967296) == 4294967296
        with pytest.raises(OverflowError):
            mod.f(-4294967296)
        with pytest.raises(TypeError):
            mod.f("this is not a number")
        with pytest.raises(TypeError):
            mod.f(self.magic_int(2))
        with pytest.raises(TypeError):
            mod.f(self.magic_index(2))

    def test_Long_AsUnsignedLongLongMask(self):
        import pytest
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                unsigned long long a = HPyLong_AsUnsignedLongLongMask(ctx, arg);
                if ((a == (unsigned long long) -1) && HPyErr_Occurred(ctx))
                    return HPy_NULL;
                return HPyLong_FromUnsignedLongLong(ctx, a);
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f(45) == 45
        assert mod.f(-1) == 2**64 - 1
        with pytest.raises(TypeError):
            mod.f("this is not a number")
        if self.python_supports_magic_int():
            assert mod.f(self.magic_int(2)) == 2
        if self.python_supports_magic_index():
            assert mod.f(self.magic_index(2)) == 2

    def test_Long_FromSize_t(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_NOARGS)
            static HPy f_impl(HPyContext *ctx, HPy self)
            {
                // take a value which doesn't fit in 32 bit
                size_t a = 2147483648;
                return HPyLong_FromSize_t(ctx, a);
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f() == 2147483648

    def test_Long_AsSize_t(self):
        import pytest
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                size_t a = HPyLong_AsSize_t(ctx, arg);
                if ((a == (size_t) -1) && HPyErr_Occurred(ctx))
                    return HPy_NULL;
                return HPyLong_FromSize_t(ctx, a);
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f(2147483648) == 2147483648
        with pytest.raises(OverflowError):
            mod.f(-2147483648)
        with pytest.raises(TypeError):
            mod.f("this is not a number")
        with pytest.raises(TypeError):
            mod.f(self.magic_int(2))
        with pytest.raises(TypeError):
            mod.f(self.magic_index(2))

    def test_Long_FromSsize_t(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_NOARGS)
            static HPy f_impl(HPyContext *ctx, HPy self)
            {
                HPy_ssize_t a = -42;
                return HPyLong_FromSsize_t(ctx, a);
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f() == -42

    def test_Long_AsSsize_t(self):
        import pytest
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                HPy_ssize_t a = HPyLong_AsSsize_t(ctx, arg);
                if ((a == (HPy_ssize_t) -1) && HPyErr_Occurred(ctx))
                    return HPy_NULL;
                return HPyLong_FromSsize_t(ctx, a);
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f(41) == 41
        assert mod.f(-41) == -41
        with pytest.raises(TypeError):
            mod.f("this is not a number")
        with pytest.raises(TypeError):
            mod.f(self.magic_int(2))
        with pytest.raises(TypeError):
            mod.f(self.magic_index(2))

    def test_Long_AsVoidPtr(self):
        mod = self.make_module("""
            HPyDef_METH(f, "is_null", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy val)
            {
                void* ptr = HPyLong_AsVoidPtr(ctx, val);
                if (!ptr) {
                    return HPy_Dup(ctx, ctx->h_True);
                } else {
                    return HPy_Dup(ctx, ctx->h_False);
                }
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.is_null(0) == True
        assert mod.is_null(10) == False

    def test_Long_AsDouble(self):
        import pytest
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                double a = HPyLong_AsDouble(ctx, arg);
                if (a == -1.0 && HPyErr_Occurred(ctx))
                    return HPy_NULL;
                return HPyFloat_FromDouble(ctx, a);
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f(45) == 45.0
        with pytest.raises(TypeError):
            mod.f("this is not a number")
