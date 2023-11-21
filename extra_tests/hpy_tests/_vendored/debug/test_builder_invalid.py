import pytest
from hpy.debug.leakdetector import LeakDetector

@pytest.fixture
def hpy_abi():
    with LeakDetector():
        yield "debug"


def test_correct_usage(compiler, hpy_debug_capture):
    # Basic sanity check that valid code does not trigger any error reports
    mod = compiler.make_module("""
        HPyDef_METH(build, "build", HPyFunc_VARARGS)
        static HPy build_impl(HPyContext *ctx, HPy h_self, const HPy *args, size_t nargs)
        {
            HPyTupleBuilder tbuilder = HPyTupleBuilder_New(ctx, nargs);
            HPyListBuilder lbuilder = HPyListBuilder_New(ctx, nargs);
            for (size_t i=0; i < nargs; i++) {
                HPyTupleBuilder_Set(ctx, tbuilder, i, args[i]);
                HPyListBuilder_Set(ctx, lbuilder, i, args[i]);
            }
            HPy t = HPyTupleBuilder_Build(ctx, tbuilder);
            HPy l = HPyListBuilder_Build(ctx, lbuilder);
            HPy h_result = HPyTuple_Pack(ctx, 2, t, l);
            HPy_Close(ctx, t);
            HPy_Close(ctx, l);
            return h_result;
        }
        
        HPyDef_METH(cancel, "cancel", HPyFunc_VARARGS)
        static HPy cancel_impl(HPyContext *ctx, HPy h_self, const HPy *args, size_t nargs)
        {
            HPyTupleBuilder tbuilder = HPyTupleBuilder_New(ctx, nargs);
            HPyListBuilder lbuilder = HPyListBuilder_New(ctx, nargs);
            for (size_t i=0; i < nargs; i++) {
                HPyTupleBuilder_Set(ctx, tbuilder, i, args[i]);
                HPyListBuilder_Set(ctx, lbuilder, i, args[i]);
            }
            HPyTupleBuilder_Cancel(ctx, tbuilder);
            HPyListBuilder_Cancel(ctx, lbuilder);
            return HPy_Dup(ctx, ctx->h_None);
        }
        @EXPORT(build)
        @EXPORT(cancel)
        @INIT
        """)
    assert mod.build('hello', 42, None) == (('hello', 42, None), ['hello', 42, None])
    assert mod.cancel('hello', 42, None) is None
    assert hpy_debug_capture.invalid_builders_count == 0


def test_build_twice(compiler, hpy_debug_capture):
    mod = compiler.make_module("""
        HPyDef_METH(f, "f", HPyFunc_VARARGS)
        static HPy f_impl(HPyContext *ctx, HPy h_self, const HPy *args, size_t nargs)
        {
            HPyTupleBuilder builder = HPyTupleBuilder_New(ctx, nargs);
            for (size_t i=0; i < nargs; i++)
                HPyTupleBuilder_Set(ctx, builder, i, args[i]);
            HPy h_result = HPyTupleBuilder_Build(ctx, builder);
            HPy_Close(ctx, h_result);
            return HPyTupleBuilder_Build(ctx, builder);
        }
        HPyDef_METH(g, "g", HPyFunc_VARARGS)
        static HPy g_impl(HPyContext *ctx, HPy h_self, const HPy *args, size_t nargs)
        {
            HPyListBuilder builder = HPyListBuilder_New(ctx, nargs);
            for (size_t i=0; i < nargs; i++)
                HPyListBuilder_Set(ctx, builder, i, args[i]);
            HPy h_result = HPyListBuilder_Build(ctx, builder);
            HPy_Close(ctx, h_result);
            return HPyListBuilder_Build(ctx, builder);
        }
        @EXPORT(f)
        @EXPORT(g)
        @INIT
        """)
    with pytest.raises(MemoryError):
        mod.f('hello', 42, None)
    assert hpy_debug_capture.invalid_builders_count == 1
    with pytest.raises(MemoryError):
        mod.g('hello', 42, None)
    assert hpy_debug_capture.invalid_builders_count == 2


def test_build_after_cancel(compiler, hpy_debug_capture):
    mod = compiler.make_module("""
        HPyDef_METH(f, "f", HPyFunc_VARARGS)
        static HPy f_impl(HPyContext *ctx, HPy h_self, const HPy *args, size_t nargs)
        {
            HPyTupleBuilder builder = HPyTupleBuilder_New(ctx, nargs);
            for (size_t i=0; i < nargs; i++)
                HPyTupleBuilder_Set(ctx, builder, i, args[i]);
            HPyTupleBuilder_Cancel(ctx, builder);
            return HPyTupleBuilder_Build(ctx, builder);
        }
        HPyDef_METH(g, "g", HPyFunc_VARARGS)
        static HPy g_impl(HPyContext *ctx, HPy h_self, const HPy *args, size_t nargs)
        {
            HPyListBuilder builder = HPyListBuilder_New(ctx, nargs);
            for (size_t i=0; i < nargs; i++)
                HPyListBuilder_Set(ctx, builder, i, args[i]);
            HPyListBuilder_Cancel(ctx, builder);
            return HPyListBuilder_Build(ctx, builder);
        }
        @EXPORT(f)
        @EXPORT(g)
        @INIT
        """)
    with pytest.raises(MemoryError):
        mod.f('hello', 42, None)
    assert hpy_debug_capture.invalid_builders_count == 1
    with pytest.raises(MemoryError):
        mod.g('hello', 42, None)
    assert hpy_debug_capture.invalid_builders_count == 2


def test_build_cancel_after_build(compiler, hpy_debug_capture):
    mod = compiler.make_module("""
        HPyDef_METH(f, "f", HPyFunc_VARARGS)
        static HPy f_impl(HPyContext *ctx, HPy h_self, const HPy *args, size_t nargs)
        {
            HPyTupleBuilder builder = HPyTupleBuilder_New(ctx, nargs);
            for (size_t i=0; i < nargs; i++)
                HPyTupleBuilder_Set(ctx, builder, i, args[i]);
            HPy h_result = HPyTupleBuilder_Build(ctx, builder);
            HPyTupleBuilder_Cancel(ctx, builder);
            HPy_Close(ctx, h_result);
            return HPy_Dup(ctx, ctx->h_None);
        }
        HPyDef_METH(g, "g", HPyFunc_VARARGS)
        static HPy g_impl(HPyContext *ctx, HPy h_self, const HPy *args, size_t nargs)
        {
            HPyListBuilder builder = HPyListBuilder_New(ctx, nargs);
            for (size_t i=0; i < nargs; i++)
                HPyListBuilder_Set(ctx, builder, i, args[i]);
            HPy h_result = HPyListBuilder_Build(ctx, builder);
            HPyListBuilder_Cancel(ctx, builder);
            HPy_Close(ctx, h_result);
            return HPy_Dup(ctx, ctx->h_None);
        }
        @EXPORT(f)
        @EXPORT(g)
        @INIT
        """)
    mod.f('hello', 42, None)
    mod.g('hello', 42, None)
    assert hpy_debug_capture.invalid_builders_count == 2
