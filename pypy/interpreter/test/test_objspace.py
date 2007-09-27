from py.test import raises
from pypy.interpreter.error import OperationError
from pypy.interpreter.function import Function
from pypy.interpreter.pycode import PyCode
from pypy.rlib.rarithmetic import r_longlong
import sys

# this test isn't so much to test that the objspace interface *works*
# -- it's more to test that it's *there*

class TestObjSpace: 
    def test_newstring(self):
        w = self.space.wrap
        s = 'abc'
        chars_w = [w(ord(c)) for c in s]
        assert self.space.eq_w(w(s), self.space.newstring(chars_w))

    def test_newstring_fail(self):
        w = self.space.wrap
        s = 'abc'
        not_chars_w = [w(c) for c in s]
        self.space.raises_w(self.space.w_TypeError,
                            self.space.newstring,
                            not_chars_w)
        self.space.raises_w(self.space.w_ValueError,
                            self.space.newstring,
                            [w(-1)])

    def test_newlist(self):
        w = self.space.wrap
        l = range(10)
        w_l = self.space.newlist([w(i) for i in l])
        assert self.space.eq_w(w_l, w(l))

    def test_newdict(self):
        d = {}
        w_d = self.space.newdict()
        assert self.space.eq_w(w_d, self.space.wrap(d))

    def test_newtuple(self):
        w = self.space.wrap
        t = tuple(range(10))
        w_t = self.space.newtuple([w(i) for i in t])
        assert self.space.eq_w(w_t, w(t))

    def test_is_true(self):
        w = self.space.wrap
        true = (1==1)
        false = (1==0)
        w_true = w(true)
        w_false = w(false)
        assert self.space.is_true(w_true)
        assert not self.space.is_true(w_false)

    def test_is_(self):
        w_l = self.space.newlist([])
        w_m = self.space.newlist([])
        assert self.space.is_(w_l, w_l) == self.space.w_True
        assert self.space.is_(w_l, w_m) == self.space.w_False

    def test_newbool(self):
        assert self.space.newbool(0) == self.space.w_False
        assert self.space.newbool(1) == self.space.w_True

    def test_unpackiterable(self):
        w = self.space.wrap
        l = [w(1), w(2), w(3), w(4)]
        w_l = self.space.newlist(l)
        assert self.space.unpackiterable(w_l) == l
        assert self.space.unpackiterable(w_l, 4) == l
        raises(ValueError, self.space.unpackiterable, w_l, 3)
        raises(ValueError, self.space.unpackiterable, w_l, 5)

    def test_unpacktuple(self):
        w = self.space.wrap
        l = [w(1), w(2), w(3), w(4)]
        w_l = self.space.newtuple(l)
        assert self.space.unpacktuple(w_l) == l
        assert self.space.unpacktuple(w_l, 4) == l
        raises(ValueError, self.space.unpacktuple, w_l, 3)
        raises(ValueError, self.space.unpacktuple, w_l, 5)

    def test_exception_match(self):
        assert self.space.exception_match(self.space.w_ValueError,
                                                   self.space.w_ValueError)
        assert self.space.exception_match(self.space.w_IndexError,
                                                   self.space.w_LookupError)
        assert not self.space.exception_match(self.space.w_ValueError,
                                               self.space.w_LookupError)

    def test_lookup(self):
        w = self.space.wrap
        w_object_doc = self.space.getattr(self.space.w_object, w("__doc__"))
        w_instance = self.space.appexec([], "(): return object()")
        assert self.space.lookup(w_instance, "__doc__") == w_object_doc 
        assert self.space.lookup(w_instance, "gobbledygook") is None
        w_instance = self.space.appexec([], """():
            class Lookup(object):
                "bla" 
            return Lookup()""")
        assert self.space.str_w(self.space.lookup(w_instance, "__doc__")) == "bla"

    def test_callable(self):
        def is_callable(w_obj):
            return self.space.is_true(self.space.callable(w_obj))

        assert is_callable(self.space.w_int)
        assert not is_callable(self.space.wrap(1))
        w_func = self.space.appexec([], "():\n def f(): pass\n return f")
        assert is_callable(w_func)
        w_lambda_func = self.space.appexec([], "(): return lambda: True")
        assert is_callable(w_lambda_func)
        
        w_instance = self.space.appexec([], """():
            class Call(object):
                def __call__(self): pass
            return Call()""")
        assert is_callable(w_instance)

        w_instance = self.space.appexec([],
                "():\n class NoCall(object): pass\n return NoCall()")
        assert not is_callable(w_instance)
        self.space.setattr(w_instance, self.space.wrap("__call__"), w_func)
        assert not is_callable(w_instance)

        w_oldstyle = self.space.appexec([], """():
            class NoCall:
                __metaclass__ = _classobj
            return NoCall()""")
        assert not is_callable(w_oldstyle)
        self.space.setattr(w_oldstyle, self.space.wrap("__call__"), w_func)
        assert is_callable(w_oldstyle)

    def test_interp_w(self):
        w = self.space.wrap
        w_bltinfunction = self.space.builtin.get('len')
        res = self.space.interp_w(Function, w_bltinfunction)
        assert res is w_bltinfunction   # with the std objspace only
        self.space.raises_w(self.space.w_TypeError, self.space.interp_w, PyCode, w_bltinfunction)
        self.space.raises_w(self.space.w_TypeError, self.space.interp_w, Function, w(42))
        self.space.raises_w(self.space.w_TypeError, self.space.interp_w, Function, w(None))
        res = self.space.interp_w(Function, w(None), can_be_None=True)
        assert res is None

    def test_getindex_w(self):
        w_instance1 = self.space.appexec([], """():
            class X(object):
                def __index__(self): return 42
            return X()""")
        w_instance2 = self.space.appexec([], """():
            class Y(object):
                def __index__(self): return 2**70
            return Y()""")
        first = self.space.getindex_w(w_instance1, None)
        assert first == 42
        second = self.space.getindex_w(w_instance2, None)
        assert second == sys.maxint
        self.space.raises_w(self.space.w_IndexError,
                            self.space.getindex_w, w_instance2, self.space.w_IndexError)
        try:
            self.space.getindex_w(self.space.w_tuple, None, "foobar")
        except OperationError, e:
            assert e.match(self.space, self.space.w_TypeError)
            assert "foobar" in e.errorstr(self.space)
        else:
            assert 0, "should have raised"

    def test_r_longlong_w(self):
        space = self.space
        w_value = space.wrap(12)
        res = space.r_longlong_w(w_value)
        assert res == 12
        assert type(res) is r_longlong
        w_value = space.wrap(r_longlong(-sys.maxint * 42))
        res = space.r_longlong_w(w_value)
        assert res == -sys.maxint * 42
        assert type(res) is r_longlong
        w_obj = space.wrap("hello world")
        space.raises_w(space.w_TypeError, space.r_longlong_w, w_obj)
        w_obj = space.wrap(-12.34)
        space.raises_w(space.w_TypeError, space.r_longlong_w, w_obj)


class TestModuleMinimal: 
    def test_sys_exists(self):
        assert self.space.sys 

    def test_import_exists(self):
        space = self.space
        assert space.builtin 
        w_name = space.wrap('__import__')
        w_builtin = space.sys.getmodule('__builtin__')
        w_import = self.space.getattr(w_builtin, w_name) 
        assert space.is_true(w_import)

    def test_sys_import(self):
        from pypy.interpreter.main import run_string
        run_string('import sys', space=self.space)
