from .support import HPyTest

class TestDict(HPyTest):

    def test_New(self):
        mod = self.make_module("""
            HPy_DEF_METH_NOARGS(f)
            static HPy f_impl(HPyContext ctx, HPy self)
            {
                return HPyDict_New(ctx);
            }
            @EXPORT f HPy_METH_NOARGS
            @INIT
        """)
        assert mod.f() == {}

    def test_SetItem(self):
        mod = self.make_module("""
            HPy_DEF_METH_O(f)
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
            @EXPORT f HPy_METH_O
            @INIT
        """)
        assert mod.f('hello') == {'hello': 1234}
