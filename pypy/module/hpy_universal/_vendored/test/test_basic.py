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
            HPy_METH_NOARGS(f)
            static HPy f_impl(HPyContext ctx, HPy self)
            {
                return HPy_Dup(ctx, ctx->h_None);
            }
            @EXPORT f METH_NOARGS
            @INIT
        """)
        assert mod.f() is None

    def test_self_is_module(self):
        mod = self.make_module("""
            HPy_METH_NOARGS(f)
            static HPy f_impl(HPyContext ctx, HPy self)
            {
                return HPy_Dup(ctx, self);
            }
            @EXPORT f METH_NOARGS
            @INIT
        """)
        assert mod.f() is mod

    def test_identity_function(self):
        mod = self.make_module("""
            HPy_METH_O(f)
            static HPy f_impl(HPyContext ctx, HPy self, HPy arg)
            {
                return HPy_Dup(ctx, arg);
            }
            @EXPORT f METH_O
            @INIT
        """)
        x = object()
        assert mod.f(x) is x

    def test_long_aslong(self):
        mod = self.make_module("""
            HPy_METH_O(f)
            static HPy f_impl(HPyContext ctx, HPy self, HPy arg)
            {
                long a = HPyLong_AsLong(ctx, arg);
                return HPyLong_FromLong(ctx, a * 2);
            }
            @EXPORT f METH_O
            @INIT
        """)
        assert mod.f(45) == 90

    def test_wrong_number_of_arguments(self):
        import pytest
        mod = self.make_module("""
            HPy_METH_NOARGS(f_noargs)
            static HPy f_noargs_impl(HPyContext ctx, HPy self)
            {
                return HPy_Dup(ctx, ctx->h_None);
            }
            HPy_METH_O(f_o)
            static HPy f_o_impl(HPyContext ctx, HPy self, HPy arg)
            {
                return HPy_Dup(ctx, ctx->h_None);
            }
            @EXPORT f_noargs METH_NOARGS
            @EXPORT f_o METH_O
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
            HPy_METH_VARARGS(f)
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
            @EXPORT f METH_VARARGS
            @INIT
        """)
        assert mod.f(4, 5, 6, 7, 8) == 45678

    def test_close(self):
        mod = self.make_module("""
            HPy_METH_O(f)
            static HPy f_impl(HPyContext ctx, HPy self, HPy arg)
            {
                HPy one = HPyLong_FromLong(ctx, 1);
                if (HPy_IsNull(one))
                    return HPy_NULL;
                HPy res = HPyNumber_Add(ctx, arg, one);
                HPy_Close(ctx, one);
                return res;
            }
            @EXPORT f METH_O
            @INIT
        """)
        assert mod.f(41.5) == 42.5

    def test_string(self):
        mod = self.make_module("""
            HPy_METH_NOARGS(f)
            static HPy f_impl(HPyContext ctx, HPy self)
            {
                return HPyUnicode_FromString(ctx, "foobar");
            }
            @EXPORT f METH_NOARGS
            @INIT
        """)
        assert mod.f() == "foobar"

    def test_bool(self):
        mod = self.make_module("""
            HPy_METH_O(f)
            static HPy f_impl(HPyContext ctx, HPy self, HPy arg)
            {
                int cond = HPyLong_AsLong(ctx, arg) > 5;
                return HPy_Dup(ctx, cond ? ctx->h_True : ctx->h_False);
            }
            @EXPORT f METH_O
            @INIT
        """)
        assert mod.f(4) is False
        assert mod.f(6) is True
