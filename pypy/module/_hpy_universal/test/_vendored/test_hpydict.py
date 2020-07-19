from .support import HPyTest

class TestDict(HPyTest):

    def test_New(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", f_impl, HPyFunc_NOARGS)
            static HPy f_impl(HPyContext ctx, HPy self)
            {
                return HPyDict_New(ctx);
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f() == {}

    def test_SetItem(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", f_impl, HPyFunc_O)
            static HPy f_impl(HPyContext ctx, HPy self, HPy arg)
            {
                HPy dict = HPyDict_New(ctx);
                if (HPy_IsNull(dict))
                    return HPy_NULL;
                HPy val = HPyLong_FromLong(ctx, 1234);
                if (HPyDict_SetItem(ctx, dict, arg, val) == -1)
                    return HPy_NULL;
                return dict;
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f('hello') == {'hello': 1234}

    def test_GetItem(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", f_impl, HPyFunc_O)
            static HPy f_impl(HPyContext ctx, HPy self, HPy arg)
            {
                HPy key = HPyUnicode_FromString(ctx, "hello");
                if (HPy_IsNull(key))
                    return HPy_NULL;
                HPy val = HPyDict_GetItem(ctx, arg, key);
                if (HPy_IsNull(val))
                    return HPy_Dup(ctx, ctx->h_None);
                return val;
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f({'hello': 1}) == 1
        assert mod.f({}) is None
