from .support import HPyTest

class AppTestBasic(HPyTest):
    spaceconfig = {'usemodules': ['hpy_universal']}
    def test_import(self):
        import hpy_universal

    def test_empty_module(self):
        import sys
        mod = self.make_module("""
            @INIT
        """)
        assert type(mod) is type(sys)

    def test_empty_module_initialization(self):
        skip("FIXME")
        import sys
        mod = self.make_module("""
            @INIT
        """)
        assert type(mod) is type(sys)
        assert mod.__loader__.name == 'mytest'
        assert mod.__spec__.loader is mod.__loader__
        assert mod.__file__

    def test_different_name(self):
        mod = self.make_module("""
            @INIT
        """, name="foo")
        assert mod.__name__ == "foo"

    def test_noop_function(self):
        mod = self.make_module("""
            HPy_FUNCTION(f)
            static HPy f_impl(HPyContext ctx, HPy self, HPy args)
            {
                return HPyNone_Get(ctx);
            }
            @EXPORT f METH_NOARGS
            @INIT
        """)
        assert mod.f() is None

    def test_self_is_module(self):
        mod = self.make_module("""
            HPy_FUNCTION(f)
            static HPy f_impl(HPyContext ctx, HPy self, HPy args)
            {
                return HPy_Dup(ctx, self);
            }
            @EXPORT f METH_NOARGS
            @INIT
        """)
        assert mod.f() is mod

    def test_identity_function(self):
        mod = self.make_module("""
            HPy_FUNCTION(f)
            static HPy f_impl(HPyContext ctx, HPy self, HPy arg)
            {
                return HPy_Dup(ctx, arg);
            }
            @EXPORT f METH_O
            @INIT
        """)
        x = object()
        assert mod.f(x) is x

    def test_wrong_number_of_arguments(self):
        # XXX: this test was manually modified to turn pytest.raises into raises :(
        mod = self.make_module("""
            HPy_FUNCTION(f_noargs)
            static HPy f_noargs_impl(HPyContext ctx, HPy self, HPy args)
            {
                return HPyNone_Get(ctx);
            }
            HPy_FUNCTION(f_o)
            static HPy f_o_impl(HPyContext ctx, HPy self, HPy args)
            {
                return HPyNone_Get(ctx);
            }
            @EXPORT f_noargs METH_NOARGS
            @EXPORT f_o METH_O
            @INIT
        """)
        with raises(TypeError):
            mod.f_noargs(1)
        with raises(TypeError):
            mod.f_o()
        with raises(TypeError):
            mod.f_o(1, 2)
