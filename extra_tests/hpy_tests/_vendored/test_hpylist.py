from .support import HPyTest

class TestList(HPyTest):

    def test_Check(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                if (HPyList_Check(ctx, arg))
                    return HPy_Dup(ctx, ctx->h_True);
                return HPy_Dup(ctx, ctx->h_False);
            }
            @EXPORT(f)
            @INIT
        """)
        class MyList(list):
            pass

        assert mod.f([]) is True
        assert mod.f('hello') is False
        assert mod.f(MyList()) is True

    def test_New(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_NOARGS)
            static HPy f_impl(HPyContext *ctx, HPy self)
            {
                return HPyList_New(ctx, 0);
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f() == []

    def test_Append(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
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

    def test_ListBuilder(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy h_self, HPy h_arg)
            {
                HPyListBuilder builder = HPyListBuilder_New(ctx, 3);
                HPyListBuilder_Set(ctx, builder, 0, h_arg);
                HPyListBuilder_Set(ctx, builder, 1, ctx->h_True);
                HPy h_num = HPyLong_FromLong(ctx, -42);
                if (HPy_IsNull(h_num))
                {
                    HPyListBuilder_Cancel(ctx, builder);
                    return HPy_NULL;
                }
                HPyListBuilder_Set(ctx, builder, 2, h_num);
                HPy_Close(ctx, h_num);
                HPy h_list = HPyListBuilder_Build(ctx, builder);
                return h_list;
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f("xy") == ["xy", True, -42]

    def test_Insert(self):
        import pytest
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_VARARGS)
            static HPy f_impl(HPyContext *ctx, HPy self, const HPy *args, size_t nargs)
            {
                HPy_ssize_t index;
                if (nargs != 3) {
                    HPyErr_SetString(ctx, ctx->h_ValueError, "expected exactly three arguments");
                    return HPy_NULL;
                }
                index = HPyLong_AsSsize_t(ctx, args[1]);
                if (index == -1 && HPyErr_Occurred(ctx)) {
                    return HPy_NULL;
                }
                if (HPyList_Insert(ctx, args[0], index, args[2]) == -1)
                    return HPy_NULL;
                return HPy_Dup(ctx, args[0]);
            }
            @EXPORT(f)
            @INIT
        """)
        l = []
        assert mod.f(l, 0, 0) == [0]
        l = []
        assert mod.f(l, -1, 0) == [0]
        l = [1, 2, 4]
        assert mod.f(l, 0, 0) == [0, 1, 2, 4]
        assert mod.f(l, -1, 3) == [0, 1, 2, 3, 4]
        assert mod.f(l, -3, 1.5) == [0, 1, 1.5, 2, 3, 4]
        assert mod.f(l, 1000, 5) == [0, 1, 1.5, 2, 3, 4, 5]
        assert mod.f(l, -1000, -1) == [-1, 0, 1, 1.5, 2, 3, 4, 5]
        with pytest.raises(SystemError):
            mod.f(None, 0, 0)
