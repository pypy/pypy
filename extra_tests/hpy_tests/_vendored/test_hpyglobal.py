"""
NOTE: this tests are also meant to be run as PyPy "applevel" tests.

This means that global imports will NOT be visible inside the test
functions. In particular, you have to "import pytest" inside the test in order
to be able to use e.g. pytest.raises (which on PyPy will be implemented by a
"fake pytest module")
"""
from .support import HPyTest


class TestHPyGlobal(HPyTest):

    def test_basics(self):
        mod = self.make_module("""
            HPyGlobal myglobal;

            HPyDef_METH(setg, "setg", HPyFunc_O)
            static HPy setg_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                HPyGlobal_Store(ctx, &myglobal, arg);
                return HPy_Dup(ctx, ctx->h_None);
            }

            HPyDef_METH(getg, "getg", HPyFunc_NOARGS)
            static HPy getg_impl(HPyContext *ctx, HPy self)
            {
                return HPyGlobal_Load(ctx, myglobal);
            }

            @EXPORT(setg)
            @EXPORT(getg)
            @EXPORT_GLOBAL(myglobal)
            @INIT
        """)
        obj = {'hello': 'world'}
        assert mod.setg(obj) is None
        assert mod.getg() is obj
