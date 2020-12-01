from .support import HPyTest

class TestErr(HPyTest):

    def test_NoMemory(self):
        import pytest
        mod = self.make_module("""
            HPyDef_METH(f, "f", f_impl, HPyFunc_NOARGS)
            static HPy f_impl(HPyContext ctx, HPy self)
            {
                return HPyErr_NoMemory(ctx);
            }
            @EXPORT(f)
            @INIT
        """)
        with pytest.raises(MemoryError):
            mod.f()

    def test_FatalError(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", f_impl, HPyFunc_NOARGS)
            static HPy f_impl(HPyContext ctx, HPy self)
            {
                HPy_FatalError(ctx, "boom!");
                // note: no 'return' statement.  This also tests that
                // the call above is known to never return---otherwise,
                // we get a warning from the missing 'return' and it is
                // turned into an error.
            }
            @EXPORT(f)
            @INIT
        """)
        # Calling mod.f() gives a fatal error, ending in abort().
        # How to check that?  For now we just check that the above compiles

    def test_errorval_returned_by_api_functions(self):
        import pytest
        mod = self.make_module("""
            HPyDef_METH(f, "f", f_impl, HPyFunc_VARARGS)
            static HPy f_impl(HPyContext ctx, HPy self, HPy *args, HPy_ssize_t nargs)
            {
                HPy a = HPy_NULL;
                HPy b = HPy_NULL;
                HPy res;
                if (!HPyArg_Parse(ctx, args, nargs, "OO", &a, &b))
                    return HPy_NULL;
                res = HPy_TrueDivide(ctx, a, b);

                // the point of the test is to check that in case of error
                // HPy_Div returns HPy_NULL
                if (HPy_IsNull(res)) {
                    HPyErr_Clear(ctx);
                    return HPyLong_FromLong(ctx, -42);
                }

                HPy_Close(ctx, b);
                return res;
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f(21, 3) == 7
        assert mod.f(21, 0) == -42
