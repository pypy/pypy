from .support import HPyTest


class TestBuildValue(HPyTest):

    def make_tests_module(self, test_cases):
        # Creates a module with function "f", that takes index of a test case
        # to execute. Argument test_cases should be a tuple with first item
        # being C code of the test case.
        # Generates, e.g.: case 0: return HPy_BuildValue(...);
        test_cases_c_code = ["case {}: {}; break;".format(i, case[0]) for i, case in enumerate(test_cases)]
        return self.make_module("""
            #include <limits.h>

            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {{
                switch (HPyLong_AsLong(ctx, arg)) {{
                    {test_cases}
                    default:
                        HPyErr_SetString(ctx, ctx->h_ValueError, "Wrong test case number");
                        return HPy_NULL;
                }}
            }}

            @EXPORT(f)
            @INIT
        """.format(test_cases='\n'.join(test_cases_c_code)))

    def test_formats(self):
        test_cases = [
            ('return HPy_BuildValue(ctx, "");', None),
            ('return HPy_BuildValue(ctx, "i", 42);', 42),
            ('return HPy_BuildValue(ctx, "i", 0);', 0),
            ('return HPy_BuildValue(ctx, "i", -1);', -1),
            ('return HPy_BuildValue(ctx, "I", 33);', 33),
            ('return HPy_BuildValue(ctx, "k", 1);', 1),
            ('return HPy_BuildValue(ctx, "K", 6543);', 6543),
            ('return HPy_BuildValue(ctx, "n", 9876);', 9876),
            ('return HPy_BuildValue(ctx, "l", 345L);', 345),
            ('return HPy_BuildValue(ctx, "l", -876L);', -876),
            ('return HPy_BuildValue(ctx, "L", 545LL);', 545),
            ('return HPy_BuildValue(ctx, "L", -344LL);', -344),
            ('return HPy_BuildValue(ctx, "f", 0.25f);', 0.25),
            ('return HPy_BuildValue(ctx, "d", 0.25);', 0.25),
            ('return HPy_BuildValue(ctx, "ii", -1, 1);', (-1, 1)),
            ('return HPy_BuildValue(ctx, "(i)", -1);', (-1,)),
            ('return HPy_BuildValue(ctx, "(i,i)", -1, 1);', (-1, 1)),
            ('return HPy_BuildValue(ctx, "(ii)", -1, 1);', (-1, 1)),
            ('return HPy_BuildValue(ctx, "s", "test string");', 'test string'),
            ('return HPy_BuildValue(ctx, "[ii]", 4, 2);', [4, 2]),
            ('return HPy_BuildValue(ctx, "[i,i]", 4, 2);', [4, 2]),
            ('return HPy_BuildValue(ctx, "[is]", 4, "2");', [4, '2']),
            ('return HPy_BuildValue(ctx, "[]");', []),
            ('return HPy_BuildValue(ctx, "[(is)((f)[kk])i]", 4, "str", 0.25, 4, 2, 14267);',
                [(4, 'str'), ((0.25,), [4, 2]), 14267]),
            ('return HPy_BuildValue(ctx, "{s:i, s:f}", "A", 4, "B", 0.25);',
                {'A':4, "B":0.25}),
            ('return HPy_BuildValue(ctx, "{s:(i,i), s:f}", "A", 4, 4, "B", 0.25);',
                {'A':(4, 4), "B":0.25}),
            ('return HPy_BuildValue(ctx, "[{s:(i,i), s:f},i]", "A", 4, 4, "B", 0.25, 42);',
                [{'A':(4, 4), "B":0.25}, 42]),
            ('return HPy_BuildValue(ctx, "({s:(i,i), s:f},[i])", "A", 4, 4, "B", 0.25, 42);',
                ({'A':(4, 4), "B":0.25}, [42])),
        ]
        mod = self.make_tests_module(test_cases)
        for i, (code, expected) in enumerate(test_cases):
            actual = mod.f(i)
            assert actual == expected, code

    def test_bad_formats(self):
        test_cases = [
            ('return HPy_BuildValue(ctx, "(q)", 42);',
             "bad format char 'q' in the format string passed to HPy_BuildValue"),
            ('return HPy_BuildValue(ctx, "(i", 42);',
             "unmatched '(' in the format string passed to HPy_BuildValue"),
            ('return HPy_BuildValue(ctx, "[i", 42);',
             "unmatched '[' in the format string passed to HPy_BuildValue"),
            ('return HPy_BuildValue(ctx, "([(i)k", 42);',
             "unmatched '(' in the format string passed to HPy_BuildValue"),
            ('return HPy_BuildValue(ctx, "(i]", 42);',
             "unmatched '(' in the format string passed to HPy_BuildValue"),
            ('return HPy_BuildValue(ctx, "[i)", 42);',
             "unmatched '[' in the format string passed to HPy_BuildValue"),
            ('return HPy_BuildValue(ctx, "N", 42);',
             "HPy_BuildValue does not support the 'N' formatting unit."),
            ('return HPy_BuildValue(ctx, "{i:i", "foo", 42);',
             "unmatched '{' in the format string passed to HPy_BuildValue"),
            ('return HPy_BuildValue(ctx, "{i:i,,}", "foo", 42);',
             "unexpected ',' in the format string passed to HPy_BuildValue"),
            ('return HPy_BuildValue(ctx, "{i:ii,}", "foo", 42, 42);',
             "missing ',' in the format string passed to HPy_BuildValue"),
            ('return HPy_BuildValue(ctx, "{i}", 42);',
             "missing ':' in the format string passed to HPy_BuildValue"),
        ]
        import pytest
        mod = self.make_tests_module(test_cases)
        for i, (code, expected_error) in enumerate(test_cases):
            with pytest.raises(SystemError) as e:
                mod.f(i)
            assert expected_error in str(e), code

    def test_O_and_aliases(self):
        mod = self.make_module("""
            HPyDef_METH(fo, "fo", HPyFunc_O)
            static HPy fo_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                return HPy_BuildValue(ctx, "O", arg);
            }

            HPyDef_METH(fs, "fs", HPyFunc_O)
            static HPy fs_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                return HPy_BuildValue(ctx, "S", arg);
            }

            @EXPORT(fo)
            @EXPORT(fs)
            @INIT
        """)

        class Dummy:
            pass
        obj = Dummy()
        assert mod.fo(obj) == obj
        assert mod.fs(obj) == obj

    def test_O_with_new_object(self):
        # HPy_BuildValue does not steal the reference to the object passed as 'O',
        # the caller still needs to close it, otherwise -> handle leak
        mod = self.make_module("""
            #include <stdio.h>
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                HPy o = HPyLong_FromLong(ctx, 42);
                HPy result;
                if (HPyLong_AsLong(ctx, arg)) {
                    result = HPy_BuildValue(ctx, "O", o);
                } else {
                    result = HPy_BuildValue(ctx, "(dO)", 0.25, o);
                }
                HPy_Close(ctx, o);
                return result;
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f(0) == (0.25, 42)
        assert mod.f(1) == 42

    def test_O_with_null(self):
        import pytest
        mod = self.make_module("""
            HPyDef_METH(no_msg, "no_msg", HPyFunc_O)
            static HPy no_msg_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                if (HPyLong_AsLong(ctx, arg)) {
                    return HPy_BuildValue(ctx, "O", HPy_NULL);
                } else {
                    return HPy_BuildValue(ctx, "(iO)", 42, HPy_NULL);
                }
            }

            HPyDef_METH(with_msg, "with_msg", HPyFunc_O)
            static HPy with_msg_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                HPyErr_SetString(ctx, ctx->h_ValueError, "Some err msg that will be asserted");
                return no_msg_impl(ctx, self, arg);
            }

            @EXPORT(with_msg)
            @EXPORT(no_msg)
            @INIT
        """)
        for i in [0, 1]:
            with pytest.raises(ValueError) as e:
                mod.with_msg(i)
            assert "Some err msg that will be asserted" in str(e)
        for i in [0, 1]:
            with pytest.raises(SystemError) as e:
                mod.no_msg(i)
            assert 'HPy_NULL object passed to HPy_BuildValue' in str(e)


    def test_OO_pars_with_new_objects(self):
        mod = self.make_module("""
            #include <stdio.h>
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                HPy o1 = HPyLong_FromLong(ctx, 1);
                HPy o2 = HPyLong_FromLong(ctx, 2);
                HPy result = HPy_BuildValue(ctx, "(OO)", o1, o2);
                HPy_Close(ctx, o1);
                HPy_Close(ctx, o2);
                return result;
            }
            @EXPORT(f)
            @INIT
        """)
        assert mod.f(None) == (1, 2)

    def test_num_limits(self):
        test_cases = [
            ('return HPy_BuildValue(ctx, "(ii)", INT_MIN, INT_MAX);',),
            ('return HPy_BuildValue(ctx, "(ll)", LONG_MIN, LONG_MAX);',),
            ('return HPy_BuildValue(ctx, "(LL)", LLONG_MIN, LLONG_MAX);',),
            ('return HPy_BuildValue(ctx, "(iI)", -1, UINT_MAX);',),
            ('return HPy_BuildValue(ctx, "(ik)", -1, ULONG_MAX);',),
            ('return HPy_BuildValue(ctx, "(iK)", -1, ULLONG_MAX);',),
            ('return HPy_BuildValue(ctx, "(nn)", HPY_SSIZE_T_MIN, HPY_SSIZE_T_MAX);',),
        ]
        mod = self.make_tests_module(test_cases)
        for i, (test,) in enumerate(test_cases):
            result = mod.f(i)
            assert result[0] < 0, test
            assert result[1] > 0, test
