import pytest
from rpython.rtyper.lltypesystem import lltype
from pypy.module.hpy_universal.apiset import APISet

class TestAPISet(object):

    def test_func(self):
        api = APISet()
        @api.func([lltype.Signed, lltype.Signed], lltype.Float)
        def divide(space, a, b):
            return float(a)/b
        #
        assert divide(None, 5, 2) == 2.5
        assert api.all_functions == [divide]

    def test_basename(self):
        api = APISet()
        @api.func([], lltype.Void)
        def HPyFoo_Bar(space):
            return None
        @api.func([], lltype.Void)
        def _HPyFoo_Internal(space):
            return None

        assert HPyFoo_Bar.basename == 'Foo_Bar'
        assert _HPyFoo_Internal.basename == 'Foo_Internal'

    def test_llhelper(self):
        api = APISet()
        @api.func([lltype.Signed, lltype.Signed], lltype.Float)
        def divide(space, a, b):
            assert space == 'MySpace'
            return float(a)/b
        #
        space = 'MySpace'
        lldivide = divide.get_llhelper(space)
        assert lldivide(5, 2) == 2.5

    def test_freeze(self):
        api = APISet()
        @api.func([], lltype.Void)
        def foo(space):
            return None
        #
        api._freeze_()
        with pytest.raises(RuntimeError):
            @api.func([], lltype.Void)
            def bar(space):
                return None
