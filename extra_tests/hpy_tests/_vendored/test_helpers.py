"""
NOTE: this tests are also meant to be run as PyPy "applevel" tests.

This means that global imports will NOT be visible inside the test
functions. In particular, you have to "import pytest" inside the test in order
to be able to use e.g. pytest.raises (which on PyPy will be implemented by a
"fake pytest module")
"""
from .support import HPyTest


class TestHPyModuleAddType(HPyTest):
    def test_with_spec_only(self):
        mod = self.make_module("""
            static HPyType_Spec dummy_spec = {
                .name = "mytest.Dummy",
            };

            HPyDef_METH(f, "f", HPyFunc_NOARGS)
            static HPy f_impl(HPyContext *ctx, HPy self)
            {
                if (!HPyHelpers_AddType(ctx, self, "Dummy", &dummy_spec, NULL))
                {
                    return HPy_NULL;
                }
                return HPy_Dup(ctx, ctx->h_None);
            }

            @EXPORT(f)
            @INIT
        """)
        assert not hasattr(mod, "Dummy")
        mod.f()
        assert isinstance(mod.Dummy, type)
        assert mod.Dummy.__name__ == "Dummy"
        assert isinstance(mod.Dummy(), mod.Dummy)

    def test_with_spec_and_params(self):
        mod = self.make_module("""
            static HPyType_Spec dummy_spec = {
                .name = "mytest.Dummy",
            };

            HPyDef_METH(f, "f", HPyFunc_NOARGS)
            static HPy f_impl(HPyContext *ctx, HPy self)
            {
                HPyType_SpecParam param[] = {
                    { HPyType_SpecParam_Base, ctx->h_LongType },
                    { (HPyType_SpecParam_Kind)0 }
                };
                if (!HPyHelpers_AddType(ctx, self, "Dummy", &dummy_spec, param))
                {
                    return HPy_NULL;
                }
                return HPy_Dup(ctx, ctx->h_None);
            }

            @EXPORT(f)
            @INIT
        """)
        assert not hasattr(mod, "Dummy")
        mod.f()
        assert isinstance(mod.Dummy, type)
        assert mod.Dummy.__name__ == "Dummy"
        assert isinstance(mod.Dummy(), mod.Dummy)
        assert isinstance(mod.Dummy(), int)
        assert mod.Dummy() == 0
        assert mod.Dummy(3) == 3

    def test_pack_args_and_keywords(self):
        import pytest
        mod = self.make_module("""
            HPyDef_METH(pack, "pack", HPyFunc_KEYWORDS)
            static HPy pack_impl(HPyContext *ctx, HPy self, const HPy *args,
                                 size_t nargs, HPy kwnames)
            {
                HPy out[] = { HPy_NULL, HPy_NULL };
                HPy result;
                if (!HPyHelpers_PackArgsAndKeywords(ctx, args, nargs, kwnames,
                         &out[0], &out[1])) {
                    return HPy_NULL;
                }
                for (int i=0; i < 2; i++) {
                    if (HPy_IsNull(out[i])) {
                        out[i] = HPy_Dup(ctx, ctx->h_None);
                    }
                }
                result = HPyTuple_FromArray(ctx, out, 2);
                for (int i=0; i < 2; i++) {
                    HPy_Close(ctx, out[i]);
                }
                return result;
            }

            HPyDef_METH(pack_error, "pack_error", HPyFunc_O)
            static HPy pack_error_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                int success;
                HPy t = HPy_NULL;
                HPy d = HPy_NULL;
                const HPy args[] = { ctx->h_None, ctx->h_True, ctx->h_False };
                size_t nargs = sizeof(args);
                uint64_t mode = HPyLong_AsUInt64_t(ctx, arg);
                switch (mode) {
                case 0:
                    success = HPyHelpers_PackArgsAndKeywords(ctx, args, nargs,
                                  HPy_NULL, NULL, &d);
                    break;
                case 1:
                    success = HPyHelpers_PackArgsAndKeywords(ctx, args, nargs,
                                  HPy_NULL, &t, NULL);
                    break;
                case 2:
                    success = HPyHelpers_PackArgsAndKeywords(ctx, args, nargs,
                                  HPy_NULL, NULL, NULL);
                    break;
                case 3:
                    success = HPyHelpers_PackArgsAndKeywords(ctx, args, nargs,
                                  ctx->h_None, &t, &d);
                    break;
                default:
                    success = 0;
                    HPyErr_SetString(ctx, ctx->h_ValueError,
                        "unknown test mode");
                    break;
                }
                if (success)
                    return HPy_Dup(ctx, ctx->h_None);
                return HPy_NULL;
            }

            @EXPORT(pack)
            @EXPORT(pack_error)
            @INIT
        """)
        assert mod.pack() == (None, None)
        assert mod.pack(1, '2', b'3') == ((1, '2', b'3'), None)
        assert mod.pack(1, '2', b'3', a='b', c='d') == ((1, '2', b'3'), dict(a='b', c='d'))
        assert mod.pack(a='b', c='d') == (None, dict(a='b', c='d'))
        for mode in range(3):
            with pytest.raises(SystemError):
                mod.pack_error(mode)
        with pytest.raises(TypeError):
            mod.pack_error(3)
