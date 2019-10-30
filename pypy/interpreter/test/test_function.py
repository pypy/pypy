import pytest
from pypy.interpreter import eval
from pypy.interpreter.function import Function, Method, descr_function_get
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.argument import Arguments


class TestMethod:
    def setup_method(self, method):
        def c(self, bar):
            return bar
        code = PyCode._from_code(self.space, c.func_code)
        self.fn = Function(self.space, code, self.space.newdict())

    def test_get(self):
        space = self.space
        w_meth = descr_function_get(space, self.fn, space.wrap(5), space.type(space.wrap(5)))
        meth = space.unwrap(w_meth)
        assert isinstance(meth, Method)

    def test_call(self):
        space = self.space
        w_meth = descr_function_get(space, self.fn, space.wrap(5), space.type(space.wrap(5)))
        meth = space.unwrap(w_meth)
        w_result = meth.call_args(Arguments(space, [space.wrap(42)]))
        assert space.unwrap(w_result) == 42

    def test_fail_call(self):
        space = self.space
        w_meth = descr_function_get(space, self.fn, space.wrap(5), space.type(space.wrap(5)))
        meth = space.unwrap(w_meth)
        args = Arguments(space, [space.wrap("spam"), space.wrap("egg")])
        self.space.raises_w(self.space.w_TypeError, meth.call_args, args)

    def test_method_get(self):
        space = self.space
        # Create some function for this test only
        def m(self): return self
        func = Function(space, PyCode._from_code(self.space, m.func_code),
                        space.newdict())
        # Some shorthands
        obj1 = space.wrap(23)
        obj2 = space.wrap(42)
        args = Arguments(space, [])
        # Check method returned from func.__get__()
        w_meth1 = descr_function_get(space, func, obj1, space.type(obj1))
        meth1 = space.unwrap(w_meth1)
        assert isinstance(meth1, Method)
        assert meth1.call_args(args) == obj1
        # Check method returned from method.__get__()
        # --- meth1 is already bound so meth1.__get__(*) is meth1.
        w_meth2 = meth1.descr_method_get(obj2, space.type(obj2))
        meth2 = space.unwrap(w_meth2)
        assert isinstance(meth2, Method)
        assert meth2.call_args(args) == obj1
        # Check method returned from unbound_method.__get__()
        w_meth3 = descr_function_get(space, func, space.w_None, space.type(obj2))
        meth3 = space.unwrap(w_meth3)
        w_meth4 = meth3.descr_method_get(obj2, space.w_None)
        meth4 = space.unwrap(w_meth4)
        assert isinstance(meth4, Method)
        assert meth4.call_args(args) == obj2
        # Check method returned from unbound_method.__get__()
        # --- with an incompatible class
        w_meth5 = meth3.descr_method_get(space.wrap('hello'), space.w_text)
        assert space.is_w(w_meth5, w_meth3)
        # Same thing, with an old-style class
        w_oldclass = space.call_function(
            space.builtin.get('__metaclass__'),
            space.wrap('OldClass'), space.newtuple([]), space.newdict())
        w_meth6 = meth3.descr_method_get(space.wrap('hello'), w_oldclass)
        assert space.is_w(w_meth6, w_meth3)
        # Reverse order of old/new styles
        w_meth7 = descr_function_get(space, func, space.w_None, w_oldclass)
        meth7 = space.unwrap(w_meth7)
        w_meth8 = meth7.descr_method_get(space.wrap('hello'), space.w_text)
        assert space.is_w(w_meth8, w_meth7)

class TestShortcuts(object):

    def test_call_function(self):
        space = self.space

        d = {}
        for i in range(10):
            args = "(" + ''.join(["a%d," % a for a in range(i)]) + ")"
            exec """
def f%s:
    return %s
""" % (args, args) in d
            f = d['f']
            res = f(*range(i))
            code = PyCode._from_code(self.space, f.func_code)
            fn = Function(self.space, code, self.space.newdict())

            assert fn.code.fast_natural_arity == i|PyCode.FLATPYCALL
            if i < 5:

                def bomb(*args):
                    assert False, "shortcutting should have avoided this"

                code.funcrun = bomb
                code.funcrun_obj = bomb

            args_w = map(space.wrap, range(i))
            w_res = space.call_function(fn, *args_w)
            check = space.is_true(space.eq(w_res, space.wrap(res)))
            assert check

    def test_flatcall(self):
        space = self.space

        def f(a):
            return a
        code = PyCode._from_code(self.space, f.func_code)
        fn = Function(self.space, code, self.space.newdict())

        assert fn.code.fast_natural_arity == 1|PyCode.FLATPYCALL

        def bomb(*args):
            assert False, "shortcutting should have avoided this"

        code.funcrun = bomb
        code.funcrun_obj = bomb

        w_3 = space.newint(3)
        w_res = space.call_function(fn, w_3)

        assert w_res is w_3

        w_res = space.appexec([fn, w_3], """(f, x):
        return f(x)
        """)

        assert w_res is w_3

    def test_flatcall_method(self):
        space = self.space

        def f(self, a):
            return a
        code = PyCode._from_code(self.space, f.func_code)
        fn = Function(self.space, code, self.space.newdict())

        assert fn.code.fast_natural_arity == 2|PyCode.FLATPYCALL

        def bomb(*args):
            assert False, "shortcutting should have avoided this"

        code.funcrun = bomb
        code.funcrun_obj = bomb

        w_3 = space.newint(3)
        w_res = space.appexec([fn, w_3], """(f, x):
        class A(object):
           m = f
        y = A().m(x)
        b = A().m
        z = b(x)
        return y is x and z is x
        """)

        assert space.is_true(w_res)

    def test_flatcall_default_arg(self):
        space = self.space

        def f(a, b):
            return a+b
        code = PyCode._from_code(self.space, f.func_code)
        fn = Function(self.space, code, self.space.newdict(),
                      defs_w=[space.newint(1)])

        assert fn.code.fast_natural_arity == 2|eval.Code.FLATPYCALL

        def bomb(*args):
            assert False, "shortcutting should have avoided this"

        code.funcrun = bomb
        code.funcrun_obj = bomb

        w_3 = space.newint(3)
        w_4 = space.newint(4)
        # ignore this for now
        #w_res = space.call_function(fn, w_3)
        # assert space.eq_w(w_res, w_4)

        w_res = space.appexec([fn, w_3], """(f, x):
        return f(x)
        """)

        assert space.eq_w(w_res, w_4)

    def test_flatcall_default_arg_method(self):
        space = self.space

        def f(self, a, b):
            return a+b
        code = PyCode._from_code(self.space, f.func_code)
        fn = Function(self.space, code, self.space.newdict(),
                      defs_w=[space.newint(1)])

        assert fn.code.fast_natural_arity == 3|eval.Code.FLATPYCALL

        def bomb(*args):
            assert False, "shortcutting should have avoided this"

        code.funcrun = bomb
        code.funcrun_obj = bomb

        w_3 = space.newint(3)

        w_res = space.appexec([fn, w_3], """(f, x):
        class A(object):
           m = f
        y = A().m(x)
        b = A().m
        z = b(x)
        return y+10*z
        """)

        assert space.eq_w(w_res, space.wrap(44))


class TestFunction:

    def test_func_defaults(self):
        from pypy.interpreter import gateway
        def g(w_a=None):
            pass
        app_g = gateway.interp2app_temp(g)
        space = self.space
        w_g = space.wrap(app_g)
        w_defs = space.getattr(w_g, space.wrap("func_defaults"))
        assert space.is_w(w_defs, space.w_None)
