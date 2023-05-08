"""
NOTE: this tests are also meant to be run as PyPy "applevel" tests.

This means that global imports will NOT be visible inside the test
functions. In particular, you have to "import pytest" inside the test in order
to be able to use e.g. pytest.raises (which on PyPy will be implemented by a
"fake pytest module")
"""
from .support import HPyTest


class TestHPyContextVar(HPyTest):

    def test_basics(self):
        mod = self.make_module("""
            HPyDef_METH(new_ctxv, "new_ctxv", HPyFunc_NOARGS)
            static HPy new_ctxv_impl(HPyContext *ctx, HPy self)
            {
                return HPyContextVar_New(ctx, "test_contextvar", HPy_NULL);
            }

            HPyDef_METH(set_ctxv, "set_ctxv", HPyFunc_VARARGS)
            static HPy set_ctxv_impl(HPyContext *ctx, HPy self, const HPy *args, size_t nargs)
            {
                HPy obj, val;
                if (!HPyArg_Parse(ctx, NULL, args, nargs, "OO", &obj, &val))
                    return HPy_NULL;
                return HPyContextVar_Set(ctx, obj, val);
            }
            HPyDef_METH(get_ctxv, "get_ctxv", HPyFunc_VARARGS)
            static HPy get_ctxv_impl(HPyContext *ctx, HPy self, const HPy *args, size_t nargs)
            {
                HPy obj, def=HPy_NULL, val;
                if (!HPyArg_Parse(ctx, NULL, args, nargs, "O|O", &obj, &def))
                    return HPy_NULL;
                if (HPyContextVar_Get(ctx, obj, def, &val) < 0) {
                    return HPy_NULL;
                }
                return val;
            }


            @EXPORT(new_ctxv)
            @EXPORT(get_ctxv)
            @EXPORT(set_ctxv)
            @INIT
        """)
        var = mod.new_ctxv()
        tok = mod.set_ctxv(var, 4)
        assert tok.var is var
        four = mod.get_ctxv(var)
        assert four == 4
