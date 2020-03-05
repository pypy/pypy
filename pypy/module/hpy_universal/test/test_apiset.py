import pytest
from rpython.rtyper.lltypesystem import lltype
from pypy.module._hpy_universal import llapi
from pypy.module._hpy_universal.apiset import APISet

class TestAPISet(object):

    @pytest.fixture
    def api(self):
        return APISet(llapi.cts)

    def test_parse_signature(self, api):
        sig = 'HPy HPyNumber_Add(HPyContext ctx, HPy x, HPy y)'
        name, FPTR = api.parse_signature(sig)
        assert name == 'HPyNumber_Add'
        assert FPTR.TO.ARGS == (llapi.HPyContext, llapi.HPy, llapi.HPy)
        assert FPTR.TO.RESULT == llapi.HPy

    def test_func(self, api):
        @api.func('double divide(long a, long b)')
        def divide(space, a, b):
            return float(a)/b
        #
        assert divide(None, 5, 2) == 2.5
        assert api.all_functions == [divide]

    def test_basename(self, api):
        @api.func('void HPyFoo_Bar(void)')
        def HPyFoo_Bar(space):
            return None
        @api.func('void _HPyFoo_Internal(void)')
        def _HPyFoo_Internal(space):
            return None

        assert HPyFoo_Bar.basename == 'Foo_Bar'
        assert _HPyFoo_Internal.basename == 'Foo_Internal'

    def test_llhelper(self, api):
        @api.func('double divide(long a, long b)')
        def divide(space, a, b):
            assert space == 'MySpace'
            return float(a)/b
        #
        space = 'MySpace'
        lldivide = divide.get_llhelper(space)
        assert lldivide(5, 2) == 2.5

    def test_freeze(self, api):
        @api.func('void foo(void)')
        def foo(space):
            return None
        #
        api._freeze_()
        with pytest.raises(RuntimeError) as exc:
            @api.func('void bar(void)')
            def bar(space):
                return None
        assert 'Too late to call' in str(exc)
