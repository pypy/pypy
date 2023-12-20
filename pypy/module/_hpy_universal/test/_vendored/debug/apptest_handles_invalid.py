# spaceconfig = {"usemodules":["_hpy_universal"], "objspace.hpy_cpyext_API":false}

import pytest
from hpy.debug.leakdetector import LeakDetector

@pytest.fixture
def hpy_abi():
    with LeakDetector():
        yield "debug"


def test_cant_use_closed_handle(compiler):  # , hpy_debug_capture):
    mod = compiler.make_module("""
        HPyDef_METH(f, "f", HPyFunc_O, .doc="double close")
        static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
        {
            HPy h = HPy_Dup(ctx, arg);
            HPy_Close(ctx, h);
            HPy_Close(ctx, h); // double close
            return HPy_Dup(ctx, ctx->h_None);
        }

        HPyDef_METH(g, "g", HPyFunc_O, .doc="use after close")
        static HPy g_impl(HPyContext *ctx, HPy self, HPy arg)
        {
            HPy h = HPy_Dup(ctx, arg);
            HPy_Close(ctx, h);
            return HPy_Repr(ctx, h);
        }

        HPyDef_METH(h, "h", HPyFunc_O, .doc="closing argument")
        static HPy h_impl(HPyContext *ctx, HPy self, HPy arg)
        {
            // Argument is implicitly closed by the caller
            HPy_Close(ctx, arg);
            return HPy_Dup(ctx, ctx->h_None);
        }

        HPyDef_METH(f_noargs, "f_noargs", HPyFunc_NOARGS, .doc="returns arg w/o dupping it")
        static HPy f_noargs_impl(HPyContext *ctx, HPy self)
        {
            // should be: return HPy_Dup(ctx, self);
            return self;
        }

        HPyDef_METH(f0, "f0", HPyFunc_O, .doc="returns arg w/o dupping it")
        static HPy f0_impl(HPyContext *ctx, HPy self, HPy arg)
        {
            // should be: return HPy_Dup(ctx, arg);
            return arg;
        }

        HPyDef_METH(f_varargs, "f_varargs", HPyFunc_VARARGS, .doc="returns arg w/o dupping it")
        static HPy f_varargs_impl(HPyContext *ctx, HPy self, const HPy *args, size_t nargs)
        {
            // should be: return HPy_Dup(ctx, args[0]);
            return args[0];
        }

        @EXPORT(f)
        @EXPORT(g)
        @EXPORT(f0)
        @EXPORT(f_noargs)
        @EXPORT(f_varargs)
        @EXPORT(h)
        @INIT
    """)
    from hpy.universal import _debug
    invalid_builders_count = [0]
    invalid_handles_count = [0]

    def increment_builders_counter():
        invalid_builders_count[0] += 1

    def increment_handles_counter():
        invalid_handles_count[0] += 1

    _debug.set_on_invalid_handle(increment_handles_counter)
    _debug.set_on_invalid_builder_handle(increment_builders_counter)
    try:
        mod.f('foo')   # double close
        assert invalid_handles_count[0] == 1
        mod.g('bar')   # use-after-close
        assert invalid_handles_count[0] == 2
        mod.f0('foo')
        assert invalid_handles_count[0] == 3
        mod.f_noargs()
        assert invalid_handles_count[0] == 4
        mod.f_varargs('foo', 'bar')
        assert invalid_handles_count[0] == 5
        mod.h('baz')
        assert invalid_handles_count[0] == 6
    finally:
        _debug.set_on_invalid_handle(None)
        _debug.set_on_invalid_builder_handle(None)
