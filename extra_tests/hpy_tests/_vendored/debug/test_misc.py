import pytest
from test.support import SUPPORTS_SYS_EXECUTABLE, SUPPORTS_MEM_PROTECTION

@pytest.fixture
def hpy_abi():
    return "debug"


@pytest.mark.skipif(not SUPPORTS_SYS_EXECUTABLE, reason="needs subprocess")
def test_use_invalid_as_struct(compiler, python_subprocess):
    mod = compiler.compile_module("""
        typedef struct {
            int value;
        } DummyObject;
        HPyType_HELPERS(DummyObject, HPyType_BuiltinShape_Object)
        
        static HPyType_Spec Dummy_spec = {
            .name = "mytest.Dummy",
            .basicsize = sizeof(DummyObject),
            .builtin_shape = HPyType_BuiltinShape_Type
        };
                

        HPyDef_METH(f, "f", HPyFunc_O)
        static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
        {
            DummyObject *data = DummyObject_AsStruct(ctx, arg);
            return HPyLong_FromLong(ctx, data->value);
        }

        @EXPORT_TYPE("Dummy", Dummy_spec)
        @EXPORT(f)
        @INIT
    """)
    code = "assert mod.f(mod.Dummy()) == 0"
    result = python_subprocess.run(mod, code)
    assert result.returncode != 0
    assert "Invalid usage of _HPy_AsStruct_Object" in result.stderr.decode("utf-8")


@pytest.mark.skipif(not SUPPORTS_SYS_EXECUTABLE, reason="needs subprocess")
def test_typecheck(compiler, python_subprocess):
    mod = compiler.compile_module("""
        HPyDef_METH(f, "f", HPyFunc_VARARGS)
        static HPy f_impl(HPyContext *ctx, HPy self, const HPy *args, size_t nargs)
        {
            if (nargs != 2) {
                HPyErr_SetString(ctx, ctx->h_TypeError, "expected exactly 2 arguments");
                return HPy_NULL;
            }
            int res = HPy_TypeCheck(ctx, args[0], args[1]);
            return HPyBool_FromLong(ctx, res);
        }
        @EXPORT(f)
        @INIT
    """)
    code = "assert mod.f(mod.f('hello', 2)) == 0"
    result = python_subprocess.run(mod, code)
    assert result.returncode != 0
    assert "HPy_TypeCheck arg 2 must be a type" in result.stderr.decode("utf-8")


@pytest.mark.skipif(not SUPPORTS_MEM_PROTECTION, reason=
                    "Could be implemented by checking the contents on close.")
@pytest.mark.skipif(not SUPPORTS_SYS_EXECUTABLE, reason="needs subprocess")
def test_type_getname(compiler, python_subprocess):
    mod = compiler.compile_module("""
        #define MODE_READ_ONLY 0
        #define MODE_USE_AFTER_FREE 1
        HPyDef_METH(f, "f", HPyFunc_VARARGS)
        static HPy f_impl(HPyContext *ctx, HPy self, const HPy *args, size_t nargs)
        {
            HPy type;
            int mode;
            const char *name;
            char *buffer;

            // parse arguments
            if (nargs != 2) {
                HPyErr_SetString(ctx, ctx->h_TypeError, "expected exactly 2 arguments");
                return HPy_NULL;
            }
            mode = HPyLong_AsLong(ctx, args[0]);
            if (mode < 0) {
                HPyErr_Clear(ctx);
                HPyErr_SetString(ctx, ctx->h_ValueError, "invalid test mode");
                return HPy_NULL;
            }
            type = mode == 1 ? HPy_Dup(ctx, args[1]) : args[1];

            name = HPyType_GetName(ctx, type);
            if (name == NULL)
                return HPy_NULL;

            switch (mode) {
            case MODE_READ_ONLY:
                // write to read-only memory
                buffer = (char *)name;
                buffer[0] = 'h';
                break;
            case MODE_USE_AFTER_FREE:
                // will cause use after handle was closed
                HPy_Close(ctx, type);
                break;
            }
            return HPyUnicode_FromString(ctx, name);
        }
        @EXPORT(f)
        @INIT
    """)
    result = python_subprocess.run(mod, "mod.f(0, 'hello')")
    assert result.returncode != 0
    assert "HPyType_GetName arg must be a type" in result.stderr.decode("utf-8")

    result = python_subprocess.run(mod, "mod.f(0, str)")
    assert result.returncode != 0

    result = python_subprocess.run(mod, "mod.f(1, str)")
    assert result.returncode != 0


@pytest.mark.skipif(not SUPPORTS_SYS_EXECUTABLE, reason="needs subprocess")
def test_type_issubtype(compiler, python_subprocess):
    mod = compiler.compile_module("""
        HPyDef_METH(f, "f", HPyFunc_VARARGS)
        static HPy f_impl(HPyContext *ctx, HPy self, const HPy *args, size_t nargs)
        {
            if (nargs != 2) {
                HPyErr_SetString(ctx, ctx->h_TypeError, "expected exactly 2 arguments");
                return HPy_NULL;
            }
            return HPyLong_FromLong(ctx, HPyType_IsSubtype(ctx, args[0], args[1]));
        }
        @EXPORT(f)
        @INIT
    """)
    result = python_subprocess.run(mod, "mod.f(bool, 'hello')")
    assert result.returncode != 0
    assert "HPyType_IsSubtype arg 2 must be a type" in result.stderr.decode("utf-8")

    result = python_subprocess.run(mod, "mod.f('hello', str)")
    assert result.returncode != 0
    assert "HPyType_IsSubtype arg 1 must be a type" in result.stderr.decode("utf-8")


@pytest.mark.skipif(not SUPPORTS_SYS_EXECUTABLE, reason="needs subprocess")
def test_unicode_substring(compiler, python_subprocess):
    mod = compiler.compile_module("""
        HPyDef_METH(f, "f", HPyFunc_VARARGS)
        static HPy f_impl(HPyContext *ctx, HPy self, const HPy *args, size_t nargs)
        {
            HPy_ssize_t start, end;
            if (nargs != 3) {
                HPyErr_SetString(ctx, ctx->h_TypeError, "expected exactly 3 arguments");
                return HPy_NULL;
            }

            start = HPyLong_AsSsize_t(ctx, args[1]);
            if (start == -1 && HPyErr_Occurred(ctx))
                return HPy_NULL;

            end = HPyLong_AsSsize_t(ctx, args[2]);
            if (end == -1 && HPyErr_Occurred(ctx))
                return HPy_NULL;

            return HPyUnicode_Substring(ctx, args[0], start, end);
        }
        @EXPORT(f)
        @INIT
    """)
    result = python_subprocess.run(mod, "mod.f(b'hello', 2, 3)")
    assert result.returncode != 0
    assert "HPyUnicode_Substring arg 1 must be a Unicode object" in result.stderr.decode("utf-8")
