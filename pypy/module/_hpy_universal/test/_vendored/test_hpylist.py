from .support import HPyTest

class TestList(HPyTest):

    def test_New(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", f_impl, HPyFunc_NOARGS)
            static HPy f_impl(HPyContext ctx, HPy self)
            {
                return HPyList_New(ctx, 0);
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f() == []

    def test_Append(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", f_impl, HPyFunc_O)
            static HPy f_impl(HPyContext ctx, HPy self, HPy arg)
            {
                HPy list = HPyList_New(ctx, 0);
                if (HPy_IsNull(list))
                    return HPy_NULL;
                if (HPyList_Append(ctx, list, arg) == -1)
                    return HPy_NULL;
                if (HPyList_Append(ctx, list, arg) == -1)
                    return HPy_NULL;
                return list;
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f(42) == [42, 42]
