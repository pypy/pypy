"""
NOTE: this tests are also meant to be run as PyPy "applevel" tests.

This means that global imports will NOT be visible inside the test
functions. In particular, you have to "import pytest" inside the test in order
to be able to use e.g. pytest.raises (which on PyPy will be implemented by a
"fake pytest module")
"""
from .support import HPyTest
from hpy.devel.abitag import HPY_ABI_VERSION, HPY_ABI_VERSION_MINOR
import shutil


class TestBasic(HPyTest):

    def test_get_version(self):
        if self.compiler.hpy_abi != 'universal':
            return
        import hpy.universal
        version, gitrev = hpy.universal.get_version()
        # it's a bit hard to test the CONTENT of these values. Let's just
        # check that they are strings...
        assert isinstance(version, str)
        assert isinstance(gitrev, str)

    def test_empty_module(self):
        import sys
        mod = self.make_module("""
            @INIT
        """)
        assert type(mod) is type(sys)

    def test_abi_version_check(self):
        if self.compiler.hpy_abi != 'universal':
            return
        try:
            self.make_module("""
                // hack: we redefine the version
                #undef HPY_ABI_VERSION
                #define HPY_ABI_VERSION 999
                @INIT
            """)
        except RuntimeError as ex:
            assert str(ex) == "HPy extension module 'mytest' requires unsupported " \
                              "version of the HPy runtime. Requested version: 999.0. " \
                              "Current HPy version: {}.{}.".format(HPY_ABI_VERSION, HPY_ABI_VERSION_MINOR)
        else:
            assert False, "Expected exception"

    def test_abi_tag_check(self):
        if self.compiler.hpy_abi != 'universal':
            return

        from hpy.universal import MODE_UNIVERSAL
        def assert_load_raises(filename, message):
            try:
                self.compiler.load_universal_module('mytest', filename, mode=MODE_UNIVERSAL)
            except RuntimeError as ex:
                assert str(ex) == message
            else:
                assert False, "Expected exception"

        module = self.compile_module("@INIT")
        filename = module.so_filename
        hpy_tag = ".hpy{}".format(HPY_ABI_VERSION)

        filename_wrong_tag = filename.replace(hpy_tag, ".hpy999")
        shutil.move(filename, filename_wrong_tag)
        assert_load_raises(filename_wrong_tag,
                           "HPy extension module 'mytest' at path '{}': mismatch "
                           "between the HPy ABI tag encoded in the filename and "
                           "the major version requested by the HPy extension itself. "
                           "Major version tag parsed from filename: 999. "
                           "Requested version: {}.{}.".format(filename_wrong_tag, HPY_ABI_VERSION, HPY_ABI_VERSION_MINOR))

        filename_no_tag = filename.replace(hpy_tag, "")
        shutil.move(filename_wrong_tag, filename_no_tag)
        assert_load_raises(filename_no_tag,
                           "HPy extension module 'mytest' at path '{}': "
                           "could not find HPy ABI tag encoded in the filename. "
                           "The extension claims to be compiled with HPy ABI version: "
                           "{}.{}.".format(filename_no_tag, HPY_ABI_VERSION, HPY_ABI_VERSION_MINOR))

    def test_different_name(self):
        mod = self.make_module("""
            @INIT
        """, name="foo")
        assert mod.__name__ == "foo"

    def test_noop_function(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_NOARGS, .doc="hello world")
            static HPy f_impl(HPyContext *ctx, HPy self)
            {
                return HPy_Dup(ctx, ctx->h_None);
            }

            @EXPORT(f)
            @INIT
        """)
        assert mod.f() is None
        assert mod.f.__doc__ == 'hello world'

    def test_self_is_module(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_NOARGS)
            static HPy f_impl(HPyContext *ctx, HPy self)
            {
                return HPy_Dup(ctx, self);
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f() is mod

    def test_identity_function(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                return HPy_Dup(ctx, arg);
            }
            @EXPORT(f)
            @INIT
        """)
        x = object()
        assert mod.f(x) is x

    def test_float_asdouble(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                double a = HPyFloat_AsDouble(ctx, arg);
                return HPyFloat_FromDouble(ctx, a * 2.);
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f(1.) == 2.

    def test_wrong_number_of_arguments(self):
        import pytest
        mod = self.make_module("""
            HPyDef_METH(f_noargs, "f_noargs", HPyFunc_NOARGS)
            static HPy f_noargs_impl(HPyContext *ctx, HPy self)
            {
                return HPy_Dup(ctx, ctx->h_None);
            }
            HPyDef_METH(f_o, "f_o", HPyFunc_O)
            static HPy f_o_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                return HPy_Dup(ctx, ctx->h_None);
            }
            @EXPORT(f_noargs)
            @EXPORT(f_o)
            @INIT
        """)
        with pytest.raises(TypeError):
            mod.f_noargs(1)
        with pytest.raises(TypeError):
            mod.f_o()
        with pytest.raises(TypeError):
            mod.f_o(1, 2)

    def test_close(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                HPy one = HPyLong_FromLong(ctx, 1);
                if (HPy_IsNull(one))
                    return HPy_NULL;
                HPy res = HPy_Add(ctx, arg, one);
                HPy_Close(ctx, one);
                return res;
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f(41.5) == 42.5

    def test_bool(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                int cond = HPyLong_AsLong(ctx, arg) > 5;
                return HPy_Dup(ctx, cond ? ctx->h_True : ctx->h_False);
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f(4) is False
        assert mod.f(6) is True

    def test_exception(self):
        import pytest
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                long x = HPyLong_AsLong(ctx, arg);
                if (x < 5) {
                    return HPyLong_FromLong(ctx, -x);
                }
                else {
                    HPyErr_SetString(ctx, ctx->h_ValueError, "hello world");
                    return HPy_NULL;
                }
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f(-10) == 10
        with pytest.raises(ValueError) as exc:
            mod.f(20)
        assert str(exc.value) == 'hello world'

    def test_varargs(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_VARARGS)
            static HPy f_impl(HPyContext *ctx, HPy self, const HPy *args, size_t nargs)
            {
                long a, b;
                if (!HPyArg_Parse(ctx, NULL, args, nargs, "ll", &a, &b))
                    return HPy_NULL;
                return HPyLong_FromLong(ctx, 10*a + b);
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f(4, 5) == 45

    def test_builtin_handles(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                long i = HPyLong_AsLong(ctx, arg);
                HPy h;
                switch(i) {
                    case 1: h = ctx->h_None; break;
                    case 2: h = ctx->h_False; break;
                    case 3: h = ctx->h_True; break;
                    case 4: h = ctx->h_ValueError; break;
                    case 5: h = ctx->h_TypeError; break;
                    case 6: h = ctx->h_IndexError; break;
                    case 7: h = ctx->h_SystemError; break;
                    case 8: h = ctx->h_BaseObjectType; break;
                    case 9: h = ctx->h_TypeType; break;
                    case 10: h = ctx->h_BoolType; break;
                    case 11: h = ctx->h_LongType; break;
                    case 12: h = ctx->h_FloatType; break;
                    case 13: h = ctx->h_UnicodeType; break;
                    case 14: h = ctx->h_TupleType; break;
                    case 15: h = ctx->h_ListType; break;
                    case 16: h = ctx->h_NotImplemented; break;
                    case 17: h = ctx->h_Ellipsis; break;
                    case 18: h = ctx->h_ComplexType; break;
                    case 19: h = ctx->h_BytesType; break;
                    case 20: h = ctx->h_MemoryViewType; break;
                    case 21: h = ctx->h_SliceType; break;
                    case 22: h = ctx->h_Builtins; break;
                    case 2048: h = ctx->h_CapsuleType; break;
                    default:
                        HPyErr_SetString(ctx, ctx->h_ValueError, "invalid choice");
                        return HPy_NULL;
                }
                return HPy_Dup(ctx, h);
            }
            @EXPORT(f)
            @INIT
        """)
        import builtins

        builtin_objs = (
            '<NULL>', None, False, True, ValueError, TypeError, IndexError,
            SystemError, object, type, bool, int, float, str, tuple, list,
            NotImplemented, Ellipsis, complex, bytes, memoryview, slice,
            builtins.__dict__
        )
        for i, obj in enumerate(builtin_objs):
            if i == 0:
                continue
            assert mod.f(i) is obj

        # we cannot be sure if 'datetime_CAPI' is available
        import datetime
        if hasattr(datetime, "datetime_CAPI"):
            assert mod.f(2048) is type(datetime.datetime_CAPI)

    def test_extern_def(self):
        import pytest
        main = """
            extern HPyDef f;
            extern HPyDef g;
            extern HPyDef h;
            extern HPyDef i;

            @EXPORT(f)
            @EXPORT(g)
            @EXPORT(h)
            @EXPORT(i)
            @INIT
        """
        extra = """
            HPyDef_METH(f, "f", HPyFunc_NOARGS)
            static HPy f_impl(HPyContext *ctx, HPy self)
            {
                return HPyLong_FromLong(ctx, 12345);
            }
            HPyDef_METH(g, "g", HPyFunc_O)
            static HPy g_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                return HPy_Dup(ctx, arg);
            }
            HPyDef_METH(h, "h", HPyFunc_VARARGS)
            static HPy h_impl(HPyContext *ctx, HPy self, const HPy *args, size_t nargs)
            {
                long a, b;
                if (!HPyArg_Parse(ctx, NULL, args, nargs, "ll", &a, &b))
                    return HPy_NULL;
                return HPyLong_FromLong(ctx, 10*a + b);
            }
            HPyDef_METH(i, "i", HPyFunc_KEYWORDS)
            static HPy i_impl(HPyContext *ctx, HPy self, const HPy *args, size_t nargs,
                              HPy kwnames)
            {
                long a, b;
                static const char *kwlist[] = { "a", "b", NULL };
                if (!HPyArg_ParseKeywords(ctx, NULL, args, nargs, kwnames, "ll", kwlist, &a, &b))
                    return HPy_NULL;
                return HPyLong_FromLong(ctx, 10*a + b);
            }
        """
        mod = self.make_module(main, extra_sources=[extra])
        assert mod.f() == 12345
        assert mod.g(42) == 42
        assert mod.h(5, 6) == 56
        assert mod.i(4, 3) == 43
        assert mod.i(a=2, b=5) == 25
        with pytest.raises(TypeError):
            mod.h("not an integer", "not an integer either")

    def test_Float_FromDouble(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_NOARGS)
            static HPy f_impl(HPyContext *ctx, HPy self)
            {
                return HPyFloat_FromDouble(ctx, 123.45);
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f() == 123.45

    def test_unsupported_signature(self):
        import pytest
        with pytest.raises(ValueError) as exc:
            self.make_module("""
                HPyDef f = {
                    .kind = HPyDef_Kind_Meth,
                    .meth = {
                        .name = "f",
                        .signature = (HPyFunc_Signature)1234,
                    }
                };
                @EXPORT(f)
                @INIT
            """)
        assert str(exc.value) == 'Unsupported HPyMeth signature'

    def test_repr_str_ascii_bytes(self):
        mod = self.make_module("""
            HPyDef_METH(f1, "f1", HPyFunc_O)
            static HPy f1_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                return HPy_Repr(ctx, arg);
            }
            HPyDef_METH(f2, "f2", HPyFunc_O)
            static HPy f2_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                return HPy_Str(ctx, arg);
            }
            HPyDef_METH(f3, "f3", HPyFunc_O)
            static HPy f3_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                return HPy_ASCII(ctx, arg);
            }
            HPyDef_METH(f4, "f4", HPyFunc_O)
            static HPy f4_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                return HPy_Bytes(ctx, arg);
            }
            @EXPORT(f1)
            @EXPORT(f2)
            @EXPORT(f3)
            @EXPORT(f4)
            @INIT
        """)
        assert mod.f1("\u1234") == "'\u1234'"
        assert mod.f2(42) == "42"
        assert mod.f3("\u1234") == "'\\u1234'"
        assert mod.f4(bytearray(b"foo")) == b"foo"

    def test_is_true(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                int cond = HPy_IsTrue(ctx, arg);
                return HPy_Dup(ctx, cond ? ctx->h_True : ctx->h_False);
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f("1234") is True
        assert mod.f("") is False

    def test_richcompare(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                HPy arg2 = HPyLong_FromLong(ctx, 100);
                HPy result = HPy_RichCompare(ctx, arg, arg2, HPy_GT);
                HPy_Close(ctx, arg2);
                return result;
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f(100) is False
        assert mod.f(150) is True

    def test_richcomparebool(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                HPy arg2 = HPyLong_FromLong(ctx, 100);
                int result = HPy_RichCompareBool(ctx, arg, arg2, HPy_GE);
                HPy_Close(ctx, arg2);
                return HPyLong_FromLong(ctx, -result);
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f(50) == 0
        assert mod.f(100) == -1

    def test_hash(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                HPy_hash_t hash = HPy_Hash(ctx, arg);
                return HPyLong_FromSsize_t(ctx, hash);
            }
            @EXPORT(f)
            @INIT
        """)
        x = object()
        assert mod.f(x) == hash(x)

    def test_ctx_name(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_NOARGS)
            static HPy f_impl(HPyContext *ctx, HPy self)
            {
                return HPyUnicode_FromString(ctx, ctx->name);
            }

            @EXPORT(f)
            @INIT
        """)
        ctx_name = mod.f()
        hpy_abi = self.compiler.hpy_abi
        if hpy_abi == 'cpython':
            assert ctx_name == 'HPy CPython ABI'
        elif hpy_abi == 'universal':
            # this can be "HPy Universal ABI (CPython backend)" or
            # "... (PyPy backend)", etc.
            assert ctx_name.startswith('HPy Universal ABI')
        elif hpy_abi == 'debug':
            assert ctx_name.startswith('HPy Debug Mode ABI')
        elif hpy_abi == 'trace':
            assert ctx_name.startswith('HPy Trace Mode ABI')
        else:
            assert False, 'unexpected hpy_abi: %s' % hpy_abi

    def test_abi_version(self):
        """
        Check that all the various ABI version info that we have around match.
        """
        from hpy.devel import abitag
        mod = self.make_module(
        """
            HPyDef_METH(get_ABI_VERSION, "get_ABI_VERSION", HPyFunc_NOARGS)
            static HPy get_ABI_VERSION_impl(HPyContext *ctx, HPy self)
            {
                return HPyLong_FromLong(ctx, HPY_ABI_VERSION);
            }

            HPyDef_METH(get_ABI_TAG, "get_ABI_TAG", HPyFunc_NOARGS)
            static HPy get_ABI_TAG_impl(HPyContext *ctx, HPy self)
            {
                return HPyUnicode_FromString(ctx, HPY_ABI_TAG);
            }

            HPyDef_METH(get_ctx_version, "get_ctx_version", HPyFunc_NOARGS)
            static HPy get_ctx_version_impl(HPyContext *ctx, HPy self)
            {
                return HPyLong_FromLong(ctx, ctx->abi_version);
            }

            @EXPORT(get_ABI_VERSION)
            @EXPORT(get_ABI_TAG)
            @EXPORT(get_ctx_version)
            @INIT
        """)
        c_HPY_ABI_VERSION = mod.get_ABI_VERSION()
        c_HPY_ABI_TAG = mod.get_ABI_TAG()
        ctx_version = mod.get_ctx_version()
        assert c_HPY_ABI_VERSION == ctx_version == abitag.HPY_ABI_VERSION
        assert c_HPY_ABI_TAG == abitag.HPY_ABI_TAG

    def test_FromVoidP_AsVoidP(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                void *p = HPy_AsVoidP(arg);
                HPy h = HPy_FromVoidP(p);
                return HPy_Dup(ctx, h);
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f(42) == 42

    def test_leave_python(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                HPy_ssize_t data_len;
                const char* data = HPyUnicode_AsUTF8AndSize(ctx, arg, &data_len);
                HPy_ssize_t acount = 0;
                HPy_BEGIN_LEAVE_PYTHON(ctx);
                for (HPy_ssize_t i = 0; i < data_len; ++i) {
                    if (data[i] == 'a')
                        acount++;
                }
                HPy_END_LEAVE_PYTHON(ctx);
                return HPyLong_FromSize_t(ctx, acount);
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f("abraka") == 3
