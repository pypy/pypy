import pytest
import operator
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

    def test_func_with_func_name(self, api):
        def make_binary(name, op):
            @api.func('double func(long a, long b)', func_name=name)
            def func(space, a, b):
                return op(a, b)
            return func
        #
        add = make_binary('add', operator.add)
        sub = make_binary('sub', operator.sub)
        assert add.__name__ == 'add'
        assert sub.__name__ == 'sub'
        assert add(None, 8, 5) == 13
        assert sub(None, 12, 3) == 9
        assert api.all_functions == [add, sub]

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
