from pypy.lib import functools
import unittest
from test import test_support
from weakref import proxy
import py

@staticmethod
def PythonPartial(func, *args, **keywords):
    'Pure Python approximation of partial()'
    def newfunc(*fargs, **fkeywords):
        newkeywords = keywords.copy()
        newkeywords.update(fkeywords)
        return func(*(args + fargs), **newkeywords)
    newfunc.func = func
    newfunc.args = args
    newfunc.keywords = keywords
    return newfunc

def capture(*args, **kw):
    """capture all positional and keyword arguments"""
    return args, kw

class TestPartial:

    thetype = functools.partial

    def test_basic_examples(self):
        p = self.thetype(capture, 1, 2, a=10, b=20)
        assert p(3, 4, b=30, c=40) == (
                         ((1, 2, 3, 4), dict(a=10, b=30, c=40)))
        p = self.thetype(map, lambda x: x*10)
        assert p([1,2,3,4]) == [10, 20, 30, 40]

    def test_attributes(self):
        p = self.thetype(capture, 1, 2, a=10, b=20)
        # attributes should be readable
        assert p.func == capture
        assert p.args == (1, 2)
        assert p.keywords == dict(a=10, b=20)
        # attributes should not be writable
        if not isinstance(self.thetype, type):
            return
        py.test.raises(TypeError, setattr, p, 'func', map)
        py.test.raises(TypeError, setattr, p, 'args', (1, 2))
        py.test.raises(TypeError, setattr, p, 'keywords', dict(a=1, b=2))

    def test_argument_checking(self):
        py.test.raises(TypeError, self.thetype)     # need at least a func arg
        try:
            self.thetype(2)()
        except TypeError:
            pass
        else:
            raise AssertionError, 'First arg not checked for callability'

    def test_protection_of_callers_dict_argument(self):
        # a caller's dictionary should not be altered by partial
        def func(a=10, b=20):
            return a
        d = {'a':3}
        p = self.thetype(func, a=5)
        assert p(**d) == 3
        assert d == {'a':3}
        p(b=7)
        assert d == {'a':3}

    def test_arg_combinations(self):
        # exercise special code paths for zero args in either partial
        # object or the caller
        p = self.thetype(capture)
        assert p() == ((), {})
        assert p(1,2) == ((1,2), {})
        p = self.thetype(capture, 1, 2)
        assert p() == ((1,2), {})
        assert p(3,4) == ((1,2,3,4), {})

    def test_kw_combinations(self):
        # exercise special code paths for no keyword args in
        # either the partial object or the caller
        p = self.thetype(capture)
        assert p() == ((), {})
        assert p(a=1) == ((), {'a':1})
        p = self.thetype(capture, a=1)
        assert p() == ((), {'a':1})
        assert p(b=2) == ((), {'a':1, 'b':2})
        # keyword args in the call override those in the partial object
        assert p(a=3, b=2) == ((), {'a':3, 'b':2})

    def test_positional(self):
        # make sure positional arguments are captured correctly
        for args in [(), (0,), (0,1), (0,1,2), (0,1,2,3)]:
            p = self.thetype(capture, *args)
            expected = args + ('x',)
            got, empty = p('x')
            assert expected == got and empty == {}

    def test_keyword(self):
        # make sure keyword arguments are captured correctly
        for a in ['a', 0, None, 3.5]:
            p = self.thetype(capture, a=a)
            expected = {'a':a,'x':None}
            empty, got = p(x=None)
            assert expected == got and empty == ()

    def test_no_side_effects(self):
        # make sure there are no side effects that affect subsequent calls
        p = self.thetype(capture, 0, a=1)
        args1, kw1 = p(1, b=2)
        assert args1 == (0,1) and kw1 == {'a':1,'b':2}
        args2, kw2 = p()
        assert args2 == (0,) and kw2 == {'a':1}

    def test_error_propagation(self):
        def f(x, y):
            x / y
        py.test.raises(ZeroDivisionError, self.thetype(f, 1, 0))
        py.test.raises(ZeroDivisionError, self.thetype(f, 1), 0)
        py.test.raises(ZeroDivisionError, self.thetype(f), 1, 0)
        py.test.raises(ZeroDivisionError, self.thetype(f, y=0), 1)

    def test_attributes(self):
        p = self.thetype(hex)
        try:
            del p.__dict__
        except (TypeError, AttributeError):
            pass
        else:
            raise AssertionError, 'partial object allowed __dict__ to be deleted'

    def test_weakref(self):
        f = self.thetype(int, base=16)
        p = proxy(f)
        assert f.func == p.func
        f = None
        import gc
        gc.collect()
        py.test.raises(ReferenceError, getattr, p, 'func')

    def test_with_bound_and_unbound_methods(self):
        data = map(str, range(10))
        join = self.thetype(str.join, '')
        assert join(data) == '0123456789'
        join = self.thetype(''.join)
        assert join(data) == '0123456789'

class PartialSubclass(functools.partial):
    pass

class TestPartialSubclass(TestPartial):

    thetype = PartialSubclass


class TestPythonPartial(TestPartial):

    thetype = PythonPartial

class TestUpdateWrapper:

    def check_wrapper(self, wrapper, wrapped,
                      assigned=functools.WRAPPER_ASSIGNMENTS,
                      updated=functools.WRAPPER_UPDATES):
        # Check attributes were assigned
        for name in assigned:
            assert getattr(wrapper, name) == getattr(wrapped, name)
        # Check attributes were updated
        for name in updated:
            wrapper_attr = getattr(wrapper, name)
            wrapped_attr = getattr(wrapped, name)
            for key in wrapped_attr:
                assert wrapped_attr[key] == wrapper_attr[key]

    def test_default_update(self):
        def f():
            """This is a test"""
            pass
        f.attr = 'This is also a test'
        def wrapper():
            pass
        functools.update_wrapper(wrapper, f)
        self.check_wrapper(wrapper, f)
        assert wrapper.__name__ == 'f'
        assert wrapper.__doc__ == 'This is a test'
        assert wrapper.attr == 'This is also a test'

    def test_no_update(self):
        def f():
            """This is a test"""
            pass
        f.attr = 'This is also a test'
        def wrapper():
            pass
        functools.update_wrapper(wrapper, f, (), ())
        self.check_wrapper(wrapper, f, (), ())
        assert wrapper.__name__ == 'wrapper'
        assert wrapper.__doc__ == None
        assert not hasattr(wrapper, 'attr')

    def test_selective_update(self):
        def f():
            pass
        f.attr = 'This is a different test'
        f.dict_attr = dict(a=1, b=2, c=3)
        def wrapper():
            pass
        wrapper.dict_attr = {}
        assign = ('attr',)
        update = ('dict_attr',)
        functools.update_wrapper(wrapper, f, assign, update)
        self.check_wrapper(wrapper, f, assign, update)
        assert wrapper.__name__ == 'wrapper'
        assert wrapper.__doc__ == None
        assert wrapper.attr == 'This is a different test'
        assert wrapper.dict_attr == f.dict_attr

    def test_builtin_update(self):
        # Test for bug #1576241
        def wrapper():
            pass
        functools.update_wrapper(wrapper, max)
        assert wrapper.__name__ == 'max'
        assert wrapper.__doc__ == max.__doc__

class TestWraps(TestUpdateWrapper):

    def test_default_update(self):
        def f():
            """This is a test"""
            pass
        f.attr = 'This is also a test'
        @functools.wraps(f)
        def wrapper():
            pass
        self.check_wrapper(wrapper, f)
        assert wrapper.__name__ == 'f'
        assert wrapper.__doc__ == 'This is a test'
        assert wrapper.attr == 'This is also a test'

    def test_no_update(self):
        def f():
            """This is a test"""
            pass
        f.attr = 'This is also a test'
        @functools.wraps(f, (), ())
        def wrapper():
            pass
        self.check_wrapper(wrapper, f, (), ())
        assert wrapper.__name__ == 'wrapper'
        assert wrapper.__doc__ == None
        assert not hasattr(wrapper, 'attr')

    def test_selective_update(self):
        def f():
            pass
        f.attr = 'This is a different test'
        f.dict_attr = dict(a=1, b=2, c=3)
        def add_dict_attr(f):
            f.dict_attr = {}
            return f
        assign = ('attr',)
        update = ('dict_attr',)
        @functools.wraps(f, assign, update)
        @add_dict_attr
        def wrapper():
            pass
        self.check_wrapper(wrapper, f, assign, update)
        assert wrapper.__name__ == 'wrapper'
        assert wrapper.__doc__ == None
        assert wrapper.attr == 'This is a different test'
        assert wrapper.dict_attr == f.dict_attr
