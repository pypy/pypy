"""
NOTE: this tests are also meant to be run as PyPy "applevel" tests.

This means that global imports will NOT be visible inside the test
functions. In particular, you have to "import pytest" inside the test in order
to be able to use e.g. pytest.raises (which on PyPy will be implemented by a
"fake pytest module")
"""
from .support import HPyTest


class TestParseItem(HPyTest):
    def make_parse_item(self, fmt, type, hpy_converter):
        mod = self.make_module("""
            HPyDef_METH(f, "f", f_impl, HPyFunc_VARARGS)
            static HPy f_impl(HPyContext ctx, HPy self,
                              HPy *args, HPy_ssize_t nargs)
            {{
                {type} a;
                if (!HPyArg_Parse(ctx, args, nargs, "{fmt}", &a))
                    return HPy_NULL;
                return {hpy_converter}(ctx, a);
            }}
            @EXPORT(f)
            @INIT
        """.format(fmt=fmt, type=type, hpy_converter=hpy_converter))
        return mod

    def test_i(self):
        mod = self.make_parse_item("i", "int", "HPyLong_FromLong")
        assert mod.f(1) == 1
        assert mod.f(-2) == -2

    def test_l(self):
        mod = self.make_parse_item("l", "long", "HPyLong_FromLong")
        assert mod.f(1) == 1
        assert mod.f(-2) == -2

    def test_d(self):
        import pytest
        mod = self.make_parse_item("d", "double", "HPyFloat_FromDouble")
        assert mod.f(1.) == 1.
        assert mod.f(-2) == -2.
        with pytest.raises(TypeError) as err:
            mod.f("x")
        assert str(err.value) == "must be real number, not str"

    def test_O(self):
        mod = self.make_parse_item("O", "HPy", "HPy_Dup")
        assert mod.f("a") == "a"
        assert mod.f(5) == 5


class TestArgParse(HPyTest):
    def make_two_arg_add(self, fmt="OO"):
        mod = self.make_module("""
            HPyDef_METH(f, "f", f_impl, HPyFunc_VARARGS)
            static HPy f_impl(HPyContext ctx, HPy self,
                              HPy *args, HPy_ssize_t nargs)
            {{
                HPy a;
                HPy b = HPy_NULL;
                HPy res;
                if (!HPyArg_Parse(ctx, args, nargs, "{fmt}", &a, &b))
                    return HPy_NULL;
                if (HPy_IsNull(b)) {{
                    b = HPyLong_FromLong(ctx, 5);
                }} else {{
                    b = HPy_Dup(ctx, b);
                }}
                res = HPy_Add(ctx, a, b);
                HPy_Close(ctx, b);
                return res;
            }}
            @EXPORT(f)
            @INIT
        """.format(fmt=fmt))
        return mod

    def test_many_int_arguments(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", f_impl, HPyFunc_VARARGS)
            static HPy f_impl(HPyContext ctx, HPy self,
                              HPy *args, HPy_ssize_t nargs)
            {
                long a, b, c, d, e;
                if (!HPyArg_Parse(ctx, args, nargs, "lllll",
                                  &a, &b, &c, &d, &e))
                    return HPy_NULL;
                return HPyLong_FromLong(ctx,
                    10000*a + 1000*b + 100*c + 10*d + e);
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f(4, 5, 6, 7, 8) == 45678

    def test_many_handle_arguments(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", f_impl, HPyFunc_VARARGS)
            static HPy f_impl(HPyContext ctx, HPy self,
                              HPy *args, HPy_ssize_t nargs)
            {
                HPy a, b;
                if (!HPyArg_Parse(ctx, args, nargs, "OO", &a, &b))
                    return HPy_NULL;
                return HPy_Add(ctx, a, b);
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f("a", "b") == "ab"

    def test_unsupported_fmt(self):
        import pytest
        mod = self.make_two_arg_add(fmt="ZZ:two_add")
        with pytest.raises(SystemError) as exc:
            mod.f("a")
        assert str(exc.value) == "two_add() unknown arg format code"

    def test_too_few_args(self):
        import pytest
        mod = self.make_two_arg_add("OO:two_add")
        with pytest.raises(TypeError) as exc:
            mod.f()
        assert str(exc.value) == "two_add() required positional argument missing"

    def test_too_many_args(self):
        import pytest
        mod = self.make_two_arg_add("OO:two_add")
        with pytest.raises(TypeError) as exc:
            mod.f(1, 2, 3)
        assert str(exc.value) == "two_add() mismatched args (too many arguments for fmt)"

    def test_optional_args(self):
        mod = self.make_two_arg_add(fmt="O|O")
        assert mod.f(1) == 6
        assert mod.f(3, 4) == 7

    def test_keyword_only_args_fails(self):
        import pytest
        mod = self.make_two_arg_add(fmt="O$O:two_add")
        with pytest.raises(SystemError) as exc:
            mod.f(1, 2)
        assert str(exc.value) == "two_add() unknown arg format code"

    def test_error_default_message(self):
        import pytest
        mod = self.make_two_arg_add(fmt="OOO")
        with pytest.raises(TypeError) as exc:
            mod.f(1, 2)
        assert str(exc.value) == "function required positional argument missing"

    def test_error_with_function_name(self):
        import pytest
        mod = self.make_two_arg_add(fmt="OOO:my_func")
        with pytest.raises(TypeError) as exc:
            mod.f(1, 2)
        assert str(exc.value) == "my_func() required positional argument missing"

    def test_error_with_overridden_message(self):
        import pytest
        mod = self.make_two_arg_add(fmt="OOO;my-error-message")
        with pytest.raises(TypeError) as exc:
            mod.f(1, 2)
        assert str(exc.value) == "my-error-message"


class TestArgParseKeywords(HPyTest):
    def make_two_arg_add(self, fmt="O+O+"):
        mod = self.make_module("""
            HPyDef_METH(f, "f", f_impl, HPyFunc_KEYWORDS)
            static HPy f_impl(HPyContext ctx, HPy self,
                              HPy *args, HPy_ssize_t nargs, HPy kw)
            {{
                HPy a, b;
                static const char *kwlist[] = {{ "a", "b", NULL }};
                if (!HPyArg_ParseKeywords(ctx, args, nargs, kw, "{fmt}",
                                          kwlist, &a, &b))
                    return HPy_NULL;
                return HPy_Add(ctx, a, b);
            }}
            @EXPORT(f)
            @INIT
        """.format(fmt=fmt))
        return mod

    def test_handle_two_arguments(self):
        mod = self.make_two_arg_add("O+O+")
        assert mod.f("x", b="y") == "xy"

    def test_handle_reordered_arguments(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", f_impl, HPyFunc_KEYWORDS)
            static HPy f_impl(HPyContext ctx, HPy self,
                              HPy *args, HPy_ssize_t nargs, HPy kw)
            {
                HPy a, b;
                static const char *kwlist[] = { "a", "b", NULL };
                if (!HPyArg_ParseKeywords(ctx, args, nargs, kw, "O+O+", kwlist, &a, &b))
                    return HPy_NULL;
                return HPy_Add(ctx, a, b);
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f(b="y", a="x") == "xy"

    def test_handle_optional_arguments(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", f_impl, HPyFunc_KEYWORDS)
            static HPy f_impl(HPyContext ctx, HPy self,
                              HPy *args, HPy_ssize_t nargs, HPy kw)
            {
                HPy a;
                HPy b = HPy_NULL;
                HPy res;
                static const char *kwlist[] = { "a", "b", NULL };
                if (!HPyArg_ParseKeywords(ctx, args, nargs, kw, "O+|O+", kwlist, &a, &b))
                    return HPy_NULL;
                if (HPy_IsNull(b)) {{
                    b = HPyLong_FromLong(ctx, 5);
                }}
                res = HPy_Add(ctx, a, b);
                HPy_Close(ctx, a);
                HPy_Close(ctx, b);
                return res;
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f(a=3, b=2) == 5
        assert mod.f(3, 2) == 5
        assert mod.f(a=3) == 8
        assert mod.f(3) == 8

    def test_unsupported_fmt(self):
        import pytest
        mod = self.make_two_arg_add(fmt="ZZ:two_add")
        with pytest.raises(SystemError) as exc:
            mod.f("a")
        assert str(exc.value) == "two_add() unknown arg format code"

    def test_missing_required_argument(self):
        import pytest
        mod = self.make_two_arg_add(fmt="O+O+:add_two")
        with pytest.raises(TypeError) as exc:
            mod.f(1)
        assert str(exc.value) == "add_two() no value for required argument"

    def test_mismatched_args_too_few_keywords(self):
        import pytest
        mod = self.make_two_arg_add(fmt="O+O+O+:add_two")
        with pytest.raises(TypeError) as exc:
            mod.f(1, 2)
        assert str(exc.value) == "add_two() mismatched args (too few keywords for fmt)"

    def test_mismatched_args_too_many_keywords(self):
        import pytest
        mod = self.make_two_arg_add(fmt="O+:add_two")
        with pytest.raises(TypeError) as exc:
            mod.f(1, 2)
        assert str(exc.value) == "add_two() mismatched args (too many keywords for fmt)"

    def test_blank_keyword_argument_exception(self):
        import pytest
        mod = self.make_module("""
            HPyDef_METH(f, "f", f_impl, HPyFunc_KEYWORDS)
            static HPy f_impl(HPyContext ctx, HPy self,
                              HPy *args, HPy_ssize_t nargs, HPy kw)
            {
                HPy a, b, c;
                static const char *kwlist[] = { "", "b", "", NULL };
                if (!HPyArg_ParseKeywords(ctx, args, nargs, kw, "NNN", kwlist,
                                          &a, &b, &c))
                    return HPy_NULL;
                return HPy_Dup(ctx, ctx->h_None);
            }
            @EXPORT(f)
            @INIT
        """)
        with pytest.raises(SystemError) as exc:
            mod.f()
        assert str(exc.value) == "function empty keyword parameter name"

    def test_positional_only_argument(self):
        import pytest
        mod = self.make_module("""
            HPyDef_METH(f, "f", f_impl, HPyFunc_KEYWORDS)
            static HPy f_impl(HPyContext ctx, HPy self,
                              HPy *args, HPy_ssize_t nargs, HPy kw)
            {
                HPy a;
                HPy b = HPy_NULL;
                HPy res;
                static const char *kwlist[] = { "", "b", NULL };
                if (!HPyArg_ParseKeywords(ctx, args, nargs, kw, "O+|O+", kwlist, &a, &b))
                    return HPy_NULL;
                if (HPy_IsNull(b)) {
                    b = HPyLong_FromLong(ctx, 5);
                } else {
                    b = HPy_Dup(ctx, b);
                }
                res = HPy_Add(ctx, a, b);
                HPy_Close(ctx, b);
                return res;
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f(1, b=2) == 3
        assert mod.f(1, 2) == 3
        assert mod.f(1) == 6
        with pytest.raises(TypeError) as exc:
            mod.f(a=1, b=2)
        assert str(exc.value) == "function no value for required argument"

    def test_keyword_only_argument(self):
        import pytest
        mod = self.make_two_arg_add(fmt="O+$O+")
        assert mod.f(1, b=2) == 3
        assert mod.f(a=1, b=2) == 3
        with pytest.raises(TypeError) as exc:
            mod.f(1, 2)
        assert str(exc.value) == (
            "function keyword only argument passed as positional argument")

    def test_error_default_message(self):
        import pytest
        mod = self.make_two_arg_add(fmt="O+O+O+")
        with pytest.raises(TypeError) as exc:
            mod.f(1, 2)
        assert str(exc.value) == "function mismatched args (too few keywords for fmt)"

    def test_error_with_function_name(self):
        import pytest
        mod = self.make_two_arg_add(fmt="O+O+O+:my_func")
        with pytest.raises(TypeError) as exc:
            mod.f(1, 2)
        assert str(exc.value) == "my_func() mismatched args (too few keywords for fmt)"

    def test_error_with_overridden_message(self):
        import pytest
        mod = self.make_two_arg_add(fmt="O+O+O+;my-error-message")
        with pytest.raises(TypeError) as exc:
            mod.f(1, 2)
        assert str(exc.value) == "my-error-message"
