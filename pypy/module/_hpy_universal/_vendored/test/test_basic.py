"""
NOTE: this tests are also meant to be run as PyPy "applevel" tests.

This means that global imports will NOT be visible inside the test
functions. In particular, you have to "import pytest" inside the test in order
to be able to use e.g. pytest.raises (which on PyPy will be implemented by a
"fake pytest module")
"""
from .support import HPyTest


class TestBasic(HPyTest):

    def test_empty_module(self):
        import sys
        mod = self.make_module("""
            @INIT
        """)
        assert type(mod) is type(sys)

    def test_different_name(self):
        mod = self.make_module("""
            @INIT
        """, name="foo")
        assert mod.__name__ == "foo"

    def test_noop_function(self):
        mod = self.make_module("""
            HPy_DEF_METH_NOARGS(f)
            static HPy f_impl(HPyContext ctx, HPy self)
            {
                return HPy_Dup(ctx, ctx->h_None);
            }
            @EXPORT f HPy_METH_NOARGS
            @INIT
        """)
        assert mod.f() is None

    def test_self_is_module(self):
        mod = self.make_module("""
            HPy_DEF_METH_NOARGS(f)
            static HPy f_impl(HPyContext ctx, HPy self)
            {
                return HPy_Dup(ctx, self);
            }
            @EXPORT f HPy_METH_NOARGS
            @INIT
        """)
        assert mod.f() is mod

    def test_identity_function(self):
        mod = self.make_module("""
            HPy_DEF_METH_O(f)
            static HPy f_impl(HPyContext ctx, HPy self, HPy arg)
            {
                return HPy_Dup(ctx, arg);
            }
            @EXPORT f HPy_METH_O
            @INIT
        """)
        x = object()
        assert mod.f(x) is x

    def test_long_aslong(self):
        mod = self.make_module("""
            HPy_DEF_METH_O(f)
            static HPy f_impl(HPyContext ctx, HPy self, HPy arg)
            {
                long a = HPyLong_AsLong(ctx, arg);
                return HPyLong_FromLong(ctx, a * 2);
            }
            @EXPORT f HPy_METH_O
            @INIT
        """)
        assert mod.f(45) == 90

    def test_wrong_number_of_arguments(self):
        import pytest
        mod = self.make_module("""
            HPy_DEF_METH_NOARGS(f_noargs)
            static HPy f_noargs_impl(HPyContext ctx, HPy self)
            {
                return HPy_Dup(ctx, ctx->h_None);
            }
            HPy_DEF_METH_O(f_o)
            static HPy f_o_impl(HPyContext ctx, HPy self, HPy arg)
            {
                return HPy_Dup(ctx, ctx->h_None);
            }
            @EXPORT f_noargs HPy_METH_NOARGS
            @EXPORT f_o HPy_METH_O
            @INIT
        """)
        with pytest.raises(TypeError):
            mod.f_noargs(1)
        with pytest.raises(TypeError):
            mod.f_o()
        with pytest.raises(TypeError):
            mod.f_o(1, 2)

    def test_many_int_arguments(self):
        mod = self.make_module("""
            HPy_DEF_METH_VARARGS(f)
            static HPy f_impl(HPyContext ctx, HPy self,
                              HPy *args, HPy_ssize_t nargs)
            {
                long a, b, c, d, e;
                if (!HPyArg_Parse(ctx, args, nargs, "lllll",
                                  &a, &b, &c, &d, &e))
                    return HPy_NULL;
                return HPyLong_FromLong(ctx,
                    10000*a + 1000*b + 100*c + 10*d + e);
            }
            @EXPORT f HPy_METH_VARARGS
            @INIT
        """)
        assert mod.f(4, 5, 6, 7, 8) == 45678

    def test_close(self):
        mod = self.make_module("""
            HPy_DEF_METH_O(f)
            static HPy f_impl(HPyContext ctx, HPy self, HPy arg)
            {
                HPy one = HPyLong_FromLong(ctx, 1);
                if (HPy_IsNull(one))
                    return HPy_NULL;
                HPy res = HPyNumber_Add(ctx, arg, one);
                HPy_Close(ctx, one);
                return res;
            }
            @EXPORT f HPy_METH_O
            @INIT
        """)
        assert mod.f(41.5) == 42.5

    def test_bool(self):
        mod = self.make_module("""
            HPy_DEF_METH_O(f)
            static HPy f_impl(HPyContext ctx, HPy self, HPy arg)
            {
                int cond = HPyLong_AsLong(ctx, arg) > 5;
                return HPy_Dup(ctx, cond ? ctx->h_True : ctx->h_False);
            }
            @EXPORT f HPy_METH_O
            @INIT
        """)
        assert mod.f(4) is False
        assert mod.f(6) is True

    def test_exception(self):
        import pytest
        mod = self.make_module("""
            HPy_DEF_METH_O(f)
            static HPy f_impl(HPyContext ctx, HPy self, HPy arg)
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
            @EXPORT f HPy_METH_O
            @INIT
        """)
        assert mod.f(-10) == 10
        with pytest.raises(ValueError) as exc:
            mod.f(20)
        assert str(exc.value) == 'hello world'

    def test_builtin_handles(self):
        import pytest
        mod = self.make_module("""
            HPy_DEF_METH_O(f)
            static HPy f_impl(HPyContext ctx, HPy self, HPy arg)
            {
                long i = HPyLong_AsLong(ctx, arg);
                HPy h;
                switch(i) {
                    case 1: h = ctx->h_None; break;
                    case 2: h = ctx->h_False; break;
                    case 3: h = ctx->h_True; break;
                    case 4: h = ctx->h_ValueError; break;
                    case 5: h = ctx->h_TypeError; break;
                    default:
                        HPyErr_SetString(ctx, ctx->h_ValueError, "invalid choice");
                        return HPy_NULL;
                }
                return HPy_Dup(ctx, h);
            }
            @EXPORT f HPy_METH_O
            @INIT
        """)
        builtin_objs = ('<NULL>', None, False, True, ValueError, TypeError)
        for i, obj in enumerate(builtin_objs):
            if i == 0:
                continue
            assert mod.f(i) is obj

    def test_decl_meth(self):
        main = """
            HPy_DECL_METH_NOARGS(f);
            HPy_DECL_METH_O(g);
            HPy_DECL_METH_VARARGS(h);

            @EXPORT f HPy_METH_NOARGS
            @EXPORT g HPy_METH_O
            @EXPORT h HPy_METH_VARARGS
            @INIT
        """
        extra = """
            HPy_DEF_METH_NOARGS(f)
            static HPy f_impl(HPyContext ctx, HPy self)
            {
                return HPyLong_FromLong(ctx, 12345);
            }
            HPy_DEF_METH_O(g)
            static HPy g_impl(HPyContext ctx, HPy self, HPy arg)
            {
                return HPy_Dup(ctx, arg);
            }
            HPy_DEF_METH_VARARGS(h)
            static HPy h_impl(HPyContext ctx, HPy self, HPy *args, HPy_ssize_t nargs)
            {
                long a, b;
                if (!HPyArg_Parse(ctx, args, nargs, "ll", &a, &b))
                    return HPy_NULL;
                return HPyLong_FromLong(ctx, 10*a + b);
            }
        """
        mod = self.make_module(main, extra_templates=[extra])
        assert mod.f() == 12345
        assert mod.g(42) == 42
        assert mod.h(5, 6) == 56

    def test_Float_FromDouble(self):
        mod = self.make_module("""
            HPy_DEF_METH_NOARGS(f)
            static HPy f_impl(HPyContext ctx, HPy self)
            {
                return HPyFloat_FromDouble(ctx, 123.45);
            }
            @EXPORT f HPy_METH_NOARGS
            @INIT
        """)
        assert mod.f() == 123.45

    def test_Long_FromLongLong(self):
        mod = self.make_module("""
            HPy_DEF_METH_NOARGS(f)
            static HPy f_impl(HPyContext ctx, HPy self)
            {
                // take a value which doesn't fit in 32 bit
                long long val = 2147483648;
                return HPyLong_FromLongLong(ctx, val);
            }
            @EXPORT f HPy_METH_NOARGS
            @INIT
        """)
        assert mod.f() == 2147483648

    def test_Long_FromUnsignedLongLong(self):
        mod = self.make_module("""
            HPy_DEF_METH_NOARGS(f)
            static HPy f_impl(HPyContext ctx, HPy self)
            {
                // take a value which doesn't fit in unsigned 32 bit
                unsigned long long val = 4294967296;
                return HPyLong_FromUnsignedLongLong(ctx, val);
            }
            @EXPORT f HPy_METH_NOARGS
            @INIT
        """)
        assert mod.f() == 4294967296
