from .support import HPyTest

class TestModule(HPyTest):
    def test_HPyModule_Create(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", f_impl, HPyFunc_NOARGS)
            static HPy f_impl(HPyContext *ctx, HPy self)
            {
                HPyModuleDef def = {
                    .name = "foo",
                    .doc = "Some doc",
                    .size = -1,
                };
                return HPyModule_Create(ctx, &def);
            }
            @EXPORT(f)
            @INIT
        """)
        m = mod.f()
        assert m.__name__ == "foo"
        assert m.__doc__ == "Some doc"
        assert m.__package__ is None
        assert m.__loader__ is None
        assert m.__spec__ is None
        assert set(vars(m).keys()) == {
            '__name__', '__doc__', '__package__', '__loader__', '__spec__'}
