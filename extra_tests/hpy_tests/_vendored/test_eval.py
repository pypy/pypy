from textwrap import dedent
from .support import HPyTest

class TestEval(HPyTest):
    def test_compile(self):
        import pytest
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_VARARGS)
            static HPy f_impl(HPyContext *ctx, HPy self, const HPy *args, size_t nargs)
            {
                const char *source, *filename;
                HPy_SourceKind src_kind;
                int src_kind_i;
                if (!HPyArg_Parse(ctx, NULL, args, nargs, "ssi", &source, &filename, &src_kind_i))
                    return HPy_NULL;

                switch (src_kind_i)
                {
                case 0: src_kind = HPy_SourceKind_Expr; break;
                case 1: src_kind = HPy_SourceKind_File; break;
                case 2: src_kind = HPy_SourceKind_Single; break;
                default:
                    // just pass through for testing
                    src_kind = (HPy_SourceKind) src_kind_i;
                }
                return HPy_Compile_s(ctx, source, filename, src_kind);
            }
            @EXPORT(f)
            @INIT
        """)
        c0 = mod.f("1 + 2", "hello0.py", 0)
        assert c0
        assert c0.co_filename == "hello0.py"
        assert eval(c0) == 3

        c1 = mod.f(dedent("""
        a = 1
        b = 2
        def add(x, y):
            return x + y
        res = add(a, b)
        """), "hello1.py", 1)
        globals1 = dict()
        locals1 = dict()
        assert eval(c1, globals1, locals1) is None
        assert "add" in locals1, "was: %r" % locals1
        assert locals1["a"] == 1
        assert locals1["b"] == 2
        assert locals1["res"] == 3

        c2 = mod.f("x = 1 + 2", "hello2.py", 2)
        locals2 = dict()
        assert eval(c2, dict(), locals2) is None
        assert locals2["x"] == 3

        with pytest.raises(SyntaxError):
            mod.f("1 +.", "hello1.c", 0)

        with pytest.raises(SystemError):
            mod.f("1+2", "hello.c", 777)

    def test_eval_code(self):
        import pytest
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_VARARGS)
            static HPy f_impl(HPyContext *ctx, HPy self, const HPy *args, size_t nargs)
            {
                if (nargs != 3) {
                    HPyErr_SetString(ctx, ctx->h_TypeError, "expected exactly 3 args");
                    return HPy_NULL;
                }
                return HPy_EvalCode(ctx, args[0], args[1], args[2]);
            }
            @EXPORT(f)
            @INIT
        """)
        c0 = compile("a + b", "hello.py", "eval")
        assert mod.f(c0, dict(), dict(a=2, b=3)) == 5

        locals1 = dict(a=10, b=20)
        c1 = compile("x = a + b", "hello.py", "exec")
        assert mod.f(c1, dict(), locals1) is None
        assert locals1['x'] == 30

        c0 = compile("raise ValueError", "hello.py", "exec")
        with pytest.raises(ValueError):
            mod.f(c0, dict(__builtins__=__builtins__), dict())
