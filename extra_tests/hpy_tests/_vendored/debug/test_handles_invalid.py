import pytest
from hpy.debug.leakdetector import LeakDetector
from test.support import SUPPORTS_SYS_EXECUTABLE, IS_PYTHON_DEBUG_BUILD
from test.conftest import IS_VALGRIND_RUN

@pytest.fixture
def hpy_abi():
    with LeakDetector():
        yield "debug"


def test_no_invalid_handle(compiler, hpy_debug_capture):
    # Basic sanity check that valid code does not trigger any error reports
    mod = compiler.make_module("""
        HPyDef_METH(f, "f", f_impl, HPyFunc_O)
        static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
        {
            HPy x = HPyLong_FromLong(ctx, 42);
            HPy y = HPyLong_FromLong(ctx, 2);
            HPy arg_dup = HPy_Dup(ctx, arg);
            HPy_Close(ctx, y);
            HPy b = HPy_Dup(ctx, x);
            HPy_Close(ctx, x);
            HPy_Close(ctx, arg_dup);
            return b;
        }

        @EXPORT(f)
        @INIT
    """)
    assert mod.f("hello") == 42
    assert mod.f("world") == 42
    assert hpy_debug_capture.invalid_handles_count == 0


def test_cant_use_closed_handle(compiler, hpy_debug_capture):
    mod = compiler.make_module("""
        HPyDef_METH(f, "f", f_impl, HPyFunc_O, .doc="double close")
        static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
        {
            HPy h = HPy_Dup(ctx, arg);
            HPy_Close(ctx, h);
            HPy_Close(ctx, h); // double close
            return HPy_Dup(ctx, ctx->h_None);
        }

        HPyDef_METH(g, "g", g_impl, HPyFunc_O, .doc="use after close")
        static HPy g_impl(HPyContext *ctx, HPy self, HPy arg)
        {
            HPy h = HPy_Dup(ctx, arg);
            HPy_Close(ctx, h);
            return HPy_Repr(ctx, h);
        }

        HPyDef_METH(h, "h", h_impl, HPyFunc_O, .doc="closing argument")
        static HPy h_impl(HPyContext *ctx, HPy self, HPy arg)
        {
            // Argument is implicitly closed by the caller
            HPy_Close(ctx, arg);
            return HPy_Dup(ctx, ctx->h_None);
        }

        HPyDef_METH(f_noargs, "f_noargs", f_noargs_impl, HPyFunc_NOARGS, .doc="returns arg w/o dupping it")
        static HPy f_noargs_impl(HPyContext *ctx, HPy self)
        {
            // should be: return HPy_Dup(ctx, self);
            return self;
        }

        HPyDef_METH(f0, "f0", f0_impl, HPyFunc_O, .doc="returns arg w/o dupping it")
        static HPy f0_impl(HPyContext *ctx, HPy self, HPy arg)
        {
            // should be: return HPy_Dup(ctx, arg);
            return arg;
        }

        HPyDef_METH(f_varargs, "f_varargs", f_varargs_impl, HPyFunc_VARARGS, .doc="returns arg w/o dupping it")
        static HPy f_varargs_impl(HPyContext *ctx, HPy self, HPy *args, HPy_ssize_t nargs)
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
    mod.f('foo')   # double close
    assert hpy_debug_capture.invalid_handles_count == 1
    mod.g('bar')   # use-after-close
    assert hpy_debug_capture.invalid_handles_count == 2
    if not IS_PYTHON_DEBUG_BUILD and not IS_VALGRIND_RUN:
        # CPython debug build can also catch these errors, so we cannot trigger
        # them when running on debug builds
        mod.f0('foo')
        assert hpy_debug_capture.invalid_handles_count == 3
        mod.f_noargs()
        assert hpy_debug_capture.invalid_handles_count == 4
        mod.f_varargs('foo', 'bar')
        assert hpy_debug_capture.invalid_handles_count == 5
        mod.h('baz')
        assert hpy_debug_capture.invalid_handles_count == 6


def test_keeping_and_reusing_argument_handle(compiler, hpy_debug_capture):
    mod = compiler.make_module("""
        HPy keep;

        HPyDef_METH(f, "f", f_impl, HPyFunc_O)
        static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
        {
            keep = arg;
            return HPy_Dup(ctx, ctx->h_None);
        }

        HPyDef_METH(g, "g", g_impl, HPyFunc_NOARGS)
        static HPy g_impl(HPyContext *ctx, HPy self)
        {
            HPy_ssize_t len = HPy_Length(ctx, keep);
            return HPyLong_FromSsize_t(ctx, len);
        }

        @EXPORT(f)
        @EXPORT(g)
        @INIT
    """)
    s = "hello leaks!"
    mod.f(s)
    assert hpy_debug_capture.invalid_handles_count == 0
    assert mod.g() == len(s)
    assert hpy_debug_capture.invalid_handles_count == 1


def test_invalid_handle_crashes_python_if_no_hook(compiler, python_subprocess, fatal_exit_code):
    if not SUPPORTS_SYS_EXECUTABLE:
        pytest.skip("no sys.executable")

    mod = compiler.compile_module("""
        HPyDef_METH(f, "f", f_impl, HPyFunc_O, .doc="double close")
        static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
        {
            HPy h = HPy_Dup(ctx, arg);
            HPy_Close(ctx, h);
            HPy_Close(ctx, h); // double close
            return HPy_Dup(ctx, ctx->h_None);
        }

        @EXPORT(f)
        @INIT
    """)
    result = python_subprocess.run(mod, "mod.f(42);")
    assert result.returncode == fatal_exit_code