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
