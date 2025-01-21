from .support import HPyTest

class TestIter(HPyTest):

    def test_Check(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                if (HPyIter_Check(ctx, arg))
                    return HPy_Dup(ctx, ctx->h_True);
                return HPy_Dup(ctx, ctx->h_False);
            }
            @EXPORT(f)
            @INIT
        """)

        class CustomIterable:
            def __init__(self):
                self._iter = iter([1, 2, 3])

            def __iter__(self):
                return self._iter

        class CustomIterator:
            def __init__(self):
                self._iter = iter([1, 2, 3])

            def __iter__(self):
                return self._iter

            def __next__(self):
                return next(self._iter)

        assert mod.f(object()) is False
        assert mod.f(10) is False

        assert mod.f((1, 2)) is False
        assert mod.f(iter((1, 2))) is True

        assert mod.f([]) is False
        assert mod.f(iter([])) is True

        assert mod.f('hello') is False
        assert mod.f(iter('hello')) is True

        assert mod.f(map(int, ("1", "2"))) is True
        assert mod.f(range(1, 10)) is False

        assert mod.f(CustomIterable()) is False
        assert mod.f(iter(CustomIterable())) is True
        assert mod.f(CustomIterator()) is True

    def test_Next(self):
        mod = self.make_module("""
            HPyDef_METH(f, "f", HPyFunc_O)
            static HPy f_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                HPy result = HPyIter_Next(ctx, arg);
                int is_null = HPy_IsNull(result);

                if (is_null && HPyErr_Occurred(ctx))
                    return HPy_NULL;
                if (is_null)
                    return HPyErr_SetObject(ctx, ctx->h_StopIteration, ctx->h_None);
                return result;
            }
            @EXPORT(f)
            @INIT
        """)

        class CustomIterator:
            def __init__(self):
                self._iter = iter(["a", "b", "c"])

            def __iter__(self):
                return self._iter

            def __next__(self):
                return next(self._iter)
            
        assert mod.f(iter([3, 2, 1])) == 3
        assert mod.f((i for i in range(1, 10))) == 1
        assert mod.f(CustomIterator()) == "a"

        import pytest
        with pytest.raises(StopIteration):
            assert mod.f(iter([]))

        
