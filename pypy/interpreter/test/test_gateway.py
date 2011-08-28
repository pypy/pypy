
# -*- coding: utf-8 -*-

from pypy.conftest import gettestobjspace
from pypy.interpreter import gateway, argument
from pypy.interpreter.gateway import ObjSpace, W_Root
import py
import sys

class FakeFunc(object):
    def __init__(self, space, name):
        self.space = space
        self.name = name
        self.defs_w = []

class TestBuiltinCode:
    def test_signature(self):
        def c(space, w_x, w_y, hello_w):
            pass
        code = gateway.BuiltinCode(c, unwrap_spec=[gateway.ObjSpace,
                                                   gateway.W_Root,
                                                   gateway.W_Root,
                                                   'args_w'])
        assert code.signature() == argument.Signature(['x', 'y'], 'hello', None)
        def d(self, w_boo):
            pass
        code = gateway.BuiltinCode(d, unwrap_spec= ['self',
                                                   gateway.W_Root], self_type=gateway.Wrappable)
        assert code.signature() == argument.Signature(['self', 'boo'], None, None)
        def e(space, w_x, w_y, __args__):
            pass
        code = gateway.BuiltinCode(e, unwrap_spec=[gateway.ObjSpace,
                                                   gateway.W_Root,
                                                   gateway.W_Root,
                                                   gateway.Arguments])
        assert code.signature() == argument.Signature(['x', 'y'], 'args', 'keywords')

        def f(space, index):
            pass
        code = gateway.BuiltinCode(f, unwrap_spec=[gateway.ObjSpace, "index"])
        assert code.signature() == argument.Signature(["index"], None, None)


    def test_call(self):
        def c(space, w_x, w_y, hello_w):
            u = space.unwrap
            w = space.wrap
            assert len(hello_w) == 2
            assert u(hello_w[0]) == 0
            assert u(hello_w[1]) == True
            return w((u(w_x) - u(w_y) + len(hello_w)))
        code = gateway.BuiltinCode(c, unwrap_spec=[gateway.ObjSpace,
                                                   gateway.W_Root,
                                                   gateway.W_Root,
                                                   'args_w'])
        w = self.space.wrap
        args = argument.Arguments(self.space, [w(123), w(23), w(0), w(True)])
        w_result = code.funcrun(FakeFunc(self.space, "c"), args)
        assert self.space.eq_w(w_result, w(102))

    def test_call_index(self):
        def c(space, index):
            assert type(index) is int
        code = gateway.BuiltinCode(c, unwrap_spec=[gateway.ObjSpace,
                                                   "index"])
        w = self.space.wrap
        args = argument.Arguments(self.space, [w(123)])
        code.funcrun(FakeFunc(self.space, "c"), args)

    def test_call_args(self):
        def c(space, w_x, w_y, __args__):
            args_w, kwds_w = __args__.unpack()
            u = space.unwrap
            w = space.wrap
            return w((u(w_x) - u(w_y) + len(args_w))
                     * u(kwds_w['boo']))
        code = gateway.BuiltinCode(c, unwrap_spec=[gateway.ObjSpace,
                                                   gateway.W_Root,
                                                   gateway.W_Root,
                                                   gateway.Arguments])
        w = self.space.wrap
        args = argument.Arguments(self.space, [w(123), w(23)], [], [],
                                  w_stararg = w((0, True)),
                                  w_starstararg = w({'boo': 10}))
        w_result = code.funcrun(FakeFunc(self.space, "c"), args)
        assert self.space.eq_w(w_result, w(1020))

class TestGateway:

    def test_app2interp(self):
        w = self.space.wrap
        def app_g3(a, b):
            return a+b
        g3 = gateway.app2interp_temp(app_g3)
        assert self.space.eq_w(g3(self.space, w('foo'), w('bar')), w('foobar'))

    def test_app2interp1(self):
        w = self.space.wrap
        def noapp_g3(a, b):
            return a+b
        g3 = gateway.app2interp_temp(noapp_g3, gateway.applevel_temp)
        assert self.space.eq_w(g3(self.space, w('foo'), w('bar')), w('foobar'))

    def test_app2interp2(self):
        """same but using transformed code"""
        w = self.space.wrap
        def noapp_g3(a, b):
            return a+b
        g3 = gateway.app2interp_temp(noapp_g3, gateway.applevelinterp_temp)
        assert self.space.eq_w(g3(self.space, w('foo'), w('bar')), w('foobar'))

    def test_app2interp_general_args(self):
        w = self.space.wrap
        def app_general(x, *args, **kwds):
            assert type(args) is tuple
            assert type(kwds) is dict
            return x + 10 * len(args) + 100 * len(kwds)
        gg = gateway.app2interp_temp(app_general)
        args = gateway.Arguments(self.space, [w(6), w(7)])
        assert self.space.int_w(gg(self.space, w(3), args)) == 23
        args = gateway.Arguments(self.space, [w(6)], ['hello', 'world'], [w(7), w(8)])
        assert self.space.int_w(gg(self.space, w(3), args)) == 213

    def test_interp2app(self):
        space = self.space
        w = space.wrap
        def g3(space, w_a, w_b):
            return space.add(w_a, w_b)
        app_g3 = gateway.interp2app_temp(g3)
        w_app_g3 = space.wrap(app_g3)
        assert self.space.eq_w(
            space.call(w_app_g3,
                       space.newtuple([w('foo'), w('bar')]),
                       space.newdict()),
            w('foobar'))
        assert self.space.eq_w(
            space.call_function(w_app_g3, w('foo'), w('bar')),
            w('foobar'))

    def test_interp2app_unwrap_spec(self):
        space = self.space
        w = space.wrap
        def g3(space, w_a, w_b):
            return space.add(w_a, w_b)
        app_g3 = gateway.interp2app_temp(g3,
                                         unwrap_spec=[gateway.ObjSpace,
                                                      gateway.W_Root,
                                                      gateway.W_Root])
        w_app_g3 = space.wrap(app_g3)
        assert self.space.eq_w(
            space.call(w_app_g3,
                       space.newtuple([w('foo'), w('bar')]),
                       space.newdict()),
            w('foobar'))
        assert self.space.eq_w(
            space.call_function(w_app_g3, w('foo'), w('bar')),
            w('foobar'))

    def test_interp2app_unwrap_spec_auto(self):
        def f(space, w_a, w_b):
            pass
        unwrap_spec = gateway.BuiltinCode(f)._unwrap_spec
        assert unwrap_spec == [ObjSpace, W_Root, W_Root]

    def test_interp2app_unwrap_spec_bool(self):
        space = self.space
        w = space.wrap
        def g(space, b):
            return space.wrap(b)
        app_g = gateway.interp2app(g, unwrap_spec=[gateway.ObjSpace, bool])
        app_g2 = gateway.interp2app(g, unwrap_spec=[gateway.ObjSpace, bool])
        assert app_g is app_g2
        w_app_g = space.wrap(app_g)
        assert self.space.eq_w(space.call_function(w_app_g, space.wrap(True)),
                               space.wrap(True))

    def test_caching_methods(self):
        class Base(gateway.Wrappable):
            def f(self):
                return 1

        class A(Base):
            pass
        class B(Base):
            pass
        app_A = gateway.interp2app(A.f)
        app_B = gateway.interp2app(B.f)
        assert app_A is not app_B

    def test_interp2app_unwrap_spec_nonnegint(self):
        space = self.space
        w = space.wrap
        def g(space, x):
            return space.wrap(x * 6)
        app_g = gateway.interp2app(g, unwrap_spec=[gateway.ObjSpace,
                                                   'nonnegint'])
        app_g2 = gateway.interp2app(g, unwrap_spec=[gateway.ObjSpace,
                                                   'nonnegint'])
        assert app_g is app_g2
        w_app_g = space.wrap(app_g)
        assert self.space.eq_w(space.call_function(w_app_g, space.wrap(7)),
                               space.wrap(42))
        assert self.space.eq_w(space.call_function(w_app_g, space.wrap(0)),
                               space.wrap(0))
        space.raises_w(space.w_ValueError,
                       space.call_function, w_app_g, space.wrap(-1))

    def test_interp2app_unwrap_spec_c_int(self):
        from pypy.rlib.rarithmetic import r_longlong
        space = self.space
        w = space.wrap
        def g(space, x):
            return space.wrap(x + 6)
        app_g = gateway.interp2app(g, unwrap_spec=[gateway.ObjSpace,
                                                   'c_int'])
        app_ug = gateway.interp2app(g, unwrap_spec=[gateway.ObjSpace,
                                                   'c_uint'])
        app_ng = gateway.interp2app(g, unwrap_spec=[gateway.ObjSpace,
                                                   'c_nonnegint'])
        assert app_ug is not app_g
        w_app_g = space.wrap(app_g)
        w_app_ug = space.wrap(app_ug)
        w_app_ng = space.wrap(app_ng)
        #
        assert self.space.eq_w(space.call_function(w_app_g, space.wrap(7)),
                               space.wrap(13))
        space.raises_w(space.w_OverflowError,
                       space.call_function, w_app_g,
                       space.wrap(r_longlong(0x80000000)))
        space.raises_w(space.w_OverflowError,
                       space.call_function, w_app_g,
                       space.wrap(r_longlong(-0x80000001)))
        #
        assert self.space.eq_w(space.call_function(w_app_ug, space.wrap(7)),
                               space.wrap(13))
        assert self.space.eq_w(space.call_function(w_app_ug,
                                                   space.wrap(0x7FFFFFFF)),
                               space.wrap(r_longlong(0x7FFFFFFF+6)))
        space.raises_w(space.w_ValueError,
                       space.call_function, w_app_ug, space.wrap(-1))
        space.raises_w(space.w_OverflowError,
                       space.call_function, w_app_ug,
                       space.wrap(r_longlong(0x100000000)))
        #
        assert self.space.eq_w(space.call_function(w_app_ng, space.wrap(7)),
                               space.wrap(13))
        space.raises_w(space.w_OverflowError,
                       space.call_function, w_app_ng,
                       space.wrap(r_longlong(0x80000000)))
        space.raises_w(space.w_ValueError,
                       space.call_function, w_app_ng, space.wrap(-1))

    def test_interp2app_unwrap_spec_args_w(self):
        space = self.space
        w = space.wrap
        def g3_args_w(space, args_w):
            return space.add(args_w[0], args_w[1])
        app_g3_args_w = gateway.interp2app_temp(g3_args_w,
                                         unwrap_spec=[gateway.ObjSpace,
                                                      'args_w'])
        w_app_g3_args_w = space.wrap(app_g3_args_w)
        assert self.space.eq_w(
            space.call(w_app_g3_args_w,
                       space.newtuple([w('foo'), w('bar')]),
                       space.newdict()),
            w('foobar'))
        assert self.space.eq_w(
            space.call_function(w_app_g3_args_w, w('foo'), w('bar')),
            w('foobar'))

    def test_interp2app_unwrap_spec_str(self):
        space = self.space
        w = space.wrap
        def g3_ss(space, s0, s1):
            if s1 is None:
                return space.wrap(42)
            return space.wrap(s0+s1)
        app_g3_ss = gateway.interp2app_temp(g3_ss,
                                         unwrap_spec=[gateway.ObjSpace,
                                                      str, 'str_or_None'])
        w_app_g3_ss = space.wrap(app_g3_ss)
        assert self.space.eq_w(
            space.call(w_app_g3_ss,
                       space.newtuple([w('foo'), w('bar')]),
                       space.newdict()),
            w('foobar'))
        assert self.space.eq_w(
            space.call_function(w_app_g3_ss, w('foo'), w('bar')),
            w('foobar'))
        assert self.space.eq_w(
            space.call_function(w_app_g3_ss, w('foo'), space.w_None),
            w(42))
        space.raises_w(space.w_TypeError, space.call_function,
                       w_app_g3_ss, space.w_None, w('bar'))

    def test_interp2app_unwrap_spec_int_float(self):
        space = self.space
        w = space.wrap
        def g3_if(space, i0, f1):
            return space.wrap(i0+f1)
        app_g3_if = gateway.interp2app_temp(g3_if,
                                         unwrap_spec=[gateway.ObjSpace,
                                                      int,float])
        w_app_g3_if = space.wrap(app_g3_if)
        assert self.space.eq_w(
            space.call(w_app_g3_if,
                       space.newtuple([w(1), w(1.0)]),
                       space.newdict()),
            w(2.0))
        assert self.space.eq_w(
            space.call_function(w_app_g3_if, w(1), w(1.0)),
            w(2.0))

    def test_interp2app_unwrap_spec_r_longlong(self):
        space = self.space
        w = space.wrap
        def g3_ll(space, n):
            return space.wrap(n * 3)
        app_g3_ll = gateway.interp2app_temp(g3_ll,
                                         unwrap_spec=[gateway.ObjSpace,
                                                      gateway.r_longlong])
        w_app_g3_ll = space.wrap(app_g3_ll)
        w_big = w(gateway.r_longlong(10**10))
        assert space.eq_w(
            space.call(w_app_g3_ll,
                       space.newtuple([w_big]),
                       space.newdict()),
            w(gateway.r_longlong(3 * 10**10)))
        assert space.eq_w(
            space.call_function(w_app_g3_ll, w_big),
            w(gateway.r_longlong(3 * 10**10)))
        w_huge = w(10L**100)
        space.raises_w(space.w_OverflowError,
                       space.call_function, w_app_g3_ll, w_huge)

    def test_interp2app_unwrap_spec_r_uint(self):
        space = self.space
        w = space.wrap
        def g3_ll(space, n):
            return space.wrap(n * 3)
        app_g3_ll = gateway.interp2app_temp(g3_ll,
                                         unwrap_spec=[gateway.ObjSpace,
                                                      gateway.r_uint])
        w_app_g3_ll = space.wrap(app_g3_ll)
        w_big = w(gateway.r_uint(sys.maxint+100))
        assert space.eq_w(
            space.call_function(w_app_g3_ll, w_big),
            w(gateway.r_uint((sys.maxint+100)*3)))
        space.raises_w(space.w_OverflowError,
                       space.call_function, w_app_g3_ll, w(10L**100))
        space.raises_w(space.w_ValueError,
                       space.call_function, w_app_g3_ll, w(-1))

    def test_interp2app_unwrap_spec_r_ulonglong(self):
        space = self.space
        w = space.wrap
        def g3_ll(space, n):
            return space.wrap(n * 3)
        app_g3_ll = gateway.interp2app_temp(g3_ll,
                                         unwrap_spec=[gateway.ObjSpace,
                                                      gateway.r_ulonglong])
        w_app_g3_ll = space.wrap(app_g3_ll)
        w_big = w(gateway.r_ulonglong(-100))
        assert space.eq_w(
            space.call_function(w_app_g3_ll, w_big),
            w(gateway.r_ulonglong(-300)))
        space.raises_w(space.w_OverflowError,
                       space.call_function, w_app_g3_ll, w(10L**100))
        space.raises_w(space.w_ValueError,
                       space.call_function, w_app_g3_ll, w(-1))
        space.raises_w(space.w_ValueError,
                       space.call_function, w_app_g3_ll, w(-10L**99))

    def test_interp2app_unwrap_spec_index(self):
        space = self.space
        w = space.wrap
        def g3_idx(space, idx0):
            return space.wrap(idx0 + 1)
        app_g3_idx = gateway.interp2app_temp(g3_idx,
                                         unwrap_spec=[gateway.ObjSpace,
                                                      'index'])
        w_app_g3_idx = space.wrap(app_g3_idx)
        assert space.eq_w(
            space.call_function(w_app_g3_idx, w(123)),
            w(124))
        space.raises_w(space.w_OverflowError,
                       space.call_function,
                       w_app_g3_idx,
                       space.mul(space.wrap(sys.maxint), space.wrap(7)))
        space.raises_w(space.w_OverflowError,
                       space.call_function,
                       w_app_g3_idx,
                       space.mul(space.wrap(sys.maxint), space.wrap(-7)))

    def test_interp2app_unwrap_spec_typechecks(self):
        space = self.space
        w = space.wrap
        def g3_id(space, x):
            return space.wrap(x)
        app_g3_i = gateway.interp2app_temp(g3_id,
                                         unwrap_spec=[gateway.ObjSpace,
                                                      int])
        w_app_g3_i = space.wrap(app_g3_i)
        assert space.eq_w(space.call_function(w_app_g3_i,w(1)),w(1))
        assert space.eq_w(space.call_function(w_app_g3_i,w(1L)),w(1))
        raises(gateway.OperationError,space.call_function,w_app_g3_i,w(sys.maxint*2))
        raises(gateway.OperationError,space.call_function,w_app_g3_i,w(None))
        raises(gateway.OperationError,space.call_function,w_app_g3_i,w("foo"))
        raises(gateway.OperationError,space.call_function,w_app_g3_i,w(1.0))

        app_g3_s = gateway.interp2app_temp(g3_id,
                                         unwrap_spec=[gateway.ObjSpace,
                                                      str])
        w_app_g3_s = space.wrap(app_g3_s)
        assert space.eq_w(space.call_function(w_app_g3_s,w("foo")),w("foo"))
        raises(gateway.OperationError,space.call_function,w_app_g3_s,w(None))
        raises(gateway.OperationError,space.call_function,w_app_g3_s,w(1))
        raises(gateway.OperationError,space.call_function,w_app_g3_s,w(1.0))

        app_g3_f = gateway.interp2app_temp(g3_id,
                                         unwrap_spec=[gateway.ObjSpace,
                                                      float])
        w_app_g3_f = space.wrap(app_g3_f)
        assert space.eq_w(space.call_function(w_app_g3_f,w(1.0)),w(1.0))
        assert space.eq_w(space.call_function(w_app_g3_f,w(1)),w(1.0))
        assert space.eq_w(space.call_function(w_app_g3_f,w(1L)),w(1.0))
        raises(gateway.OperationError,space.call_function,w_app_g3_f,w(None))
        raises(gateway.OperationError,space.call_function,w_app_g3_f,w("foo"))

    def test_interp2app_unwrap_spec_unicode(self):
        space = self.space
        w = space.wrap
        def g3_u(space, uni):
            return space.wrap(len(uni))
        app_g3_u = gateway.interp2app_temp(g3_u,
                                         unwrap_spec=[gateway.ObjSpace,
                                                      unicode])
        w_app_g3_u = space.wrap(app_g3_u)
        assert self.space.eq_w(
            space.call_function(w_app_g3_u, w(u"foo")),
            w(3))
        assert self.space.eq_w(
            space.call_function(w_app_g3_u, w("baz")),
            w(3))
        raises(gateway.OperationError, space.call_function, w_app_g3_u,
               w(None))
        raises(gateway.OperationError, space.call_function, w_app_g3_u,
               w(42))


    def test_interp2app_unwrap_spec_func(self):
        space = self.space
        w = space.wrap
        def g_id(space, w_x):
            return w_x
        l =[]
        def checker(w_x):
            l.append(w_x)
            return w_x

        app_g_id = gateway.interp2app_temp(g_id,
                                           unwrap_spec=[gateway.ObjSpace,
                                                        (checker, gateway.W_Root)])
        w_app_g_id = space.wrap(app_g_id)
        assert space.eq_w(space.call_function(w_app_g_id,w("foo")),w("foo"))
        assert len(l) == 1
        assert space.eq_w(l[0], w("foo"))

    def test_interp2app_classmethod(self):
        space = self.space
        w = space.wrap
        def g_run(space, w_type):
            assert space.is_w(w_type, space.w_str)
            return w(42)

        app_g_run = gateway.interp2app_temp(g_run,
                                            unwrap_spec=[gateway.ObjSpace,
                                                         gateway.W_Root],
                                            as_classmethod=True)
        w_app_g_run = space.wrap(app_g_run)
        w_bound = space.get(w_app_g_run, w("hello"), space.w_str)
        assert space.eq_w(space.call_function(w_bound), w(42))

    def test_interp2app_fastcall(self):
        space = self.space
        w = space.wrap
        w_3 = w(3)

        def f(space):
            return w_3
        app_f = gateway.interp2app_temp(f, unwrap_spec=[gateway.ObjSpace])
        w_app_f = w(app_f)

        # sanity
        assert isinstance(w_app_f.code, gateway.BuiltinCode0)

        called = []
        fastcall_0 = w_app_f.code.fastcall_0
        def witness_fastcall_0(space, w_func):
            called.append(w_func)
            return fastcall_0(space, w_func)

        w_app_f.code.fastcall_0 = witness_fastcall_0

        w_3 = space.newint(3)
        w_res = space.call_function(w_app_f)

        assert w_res is w_3
        assert called == [w_app_f]

        called = []

        w_res = space.appexec([w_app_f], """(f):
        return f()
        """)

        assert w_res is w_3
        assert called == [w_app_f]

    def test_interp2app_fastcall_method(self):
        space = self.space
        w = space.wrap
        w_3 = w(3)

        def f(space, w_self, w_x):
            return w_x
        app_f = gateway.interp2app_temp(f, unwrap_spec=[gateway.ObjSpace,
                                                        gateway.W_Root,
                                                        gateway.W_Root])
        w_app_f = w(app_f)

        # sanity
        assert isinstance(w_app_f.code, gateway.BuiltinCode2)

        called = []
        fastcall_2 = w_app_f.code.fastcall_2
        def witness_fastcall_2(space, w_func, w_a, w_b):
            called.append(w_func)
            return fastcall_2(space, w_func, w_a, w_b)

        w_app_f.code.fastcall_2 = witness_fastcall_2

        w_res = space.appexec([w_app_f, w_3], """(f, x):
        class A(object):
           m = f # not a builtin function, so works as method
        y = A().m(x)
        b = A().m
        z = b(x)
        return y is x and z is x
        """)

        assert space.is_true(w_res)
        assert called == [w_app_f, w_app_f]

    def test_plain(self):
        space = self.space

        def g(space, w_a, w_x):
            return space.newtuple([space.wrap('g'), w_a, w_x])

        w_g = space.wrap(gateway.interp2app_temp(g,
                         unwrap_spec=[gateway.ObjSpace,
                                      gateway.W_Root,
                                      gateway.W_Root]))

        args = argument.Arguments(space, [space.wrap(-1), space.wrap(0)])

        w_res = space.call_args(w_g, args)
        assert space.is_true(space.eq(w_res, space.wrap(('g', -1, 0))))

        w_self = space.wrap('self')

        args0 = argument.Arguments(space, [space.wrap(0)])
        args = args0.prepend(w_self)

        w_res = space.call_args(w_g, args)
        assert space.is_true(space.eq(w_res, space.wrap(('g', 'self', 0))))

        args3 = argument.Arguments(space, [space.wrap(3)])
        w_res = space.call_obj_args(w_g, w_self, args3)
        assert space.is_true(space.eq(w_res, space.wrap(('g', 'self', 3))))

    def test_unwrap_spec_decorator(self):
        space = self.space
        @gateway.unwrap_spec(gateway.ObjSpace, gateway.W_Root, int)
        def g(space, w_thing, i):
            return space.newtuple([w_thing, space.wrap(i)])
        w_g = space.wrap(gateway.interp2app_temp(g))
        args = argument.Arguments(space, [space.wrap(-1), space.wrap(0)])
        w_res = space.call_args(w_g, args)
        assert space.eq_w(w_res, space.wrap((-1, 0)))

    def test_unwrap_spec_decorator_kwargs(self):
        space = self.space
        @gateway.unwrap_spec(i=int)
        def f(space, w_thing, i):
            return space.newtuple([w_thing, space.wrap(i)])
        unwrap_spec = gateway.BuiltinCode(f)._unwrap_spec
        assert unwrap_spec == [ObjSpace, W_Root, int]

class AppTestPyTestMark:
    @py.test.mark.unlikely_to_exist
    def test_anything(self):
        pass


class TestPassThroughArguments:

    def test_pass_trough_arguments0(self):
        space = self.space

        called = []

        def f(space, __args__):
            called.append(__args__)
            a_w, _ = __args__.unpack()
            return space.newtuple([space.wrap('f')]+a_w)

        w_f = space.wrap(gateway.interp2app_temp(f,
                         unwrap_spec=[gateway.ObjSpace,
                                      gateway.Arguments]))

        args = argument.Arguments(space, [space.wrap(7)])

        w_res = space.call_args(w_f, args)
        assert space.is_true(space.eq(w_res, space.wrap(('f', 7))))

        # white-box check for opt
        assert called[0] is args

    def test_pass_trough_arguments1(self):
        space = self.space

        called = []

        def g(space, w_self, __args__):
            called.append(__args__)
            a_w, _ = __args__.unpack()
            return space.newtuple([space.wrap('g'), w_self, ]+a_w)

        w_g = space.wrap(gateway.interp2app_temp(g,
                         unwrap_spec=[gateway.ObjSpace,
                                      gateway.W_Root,
                                      gateway.Arguments]))

        old_funcrun = w_g.code.funcrun
        def funcrun_witness(func, args):
            called.append('funcrun')
            return old_funcrun(func, args)

        w_g.code.funcrun = funcrun_witness

        w_self = space.wrap('self')

        args3 = argument.Arguments(space, [space.wrap(3)])
        w_res = space.call_obj_args(w_g, w_self, args3)
        assert space.is_true(space.eq(w_res, space.wrap(('g', 'self', 3))))
        # white-box check for opt
        assert len(called) == 1
        assert called[0] is args3

        called = []
        args0 = argument.Arguments(space, [space.wrap(0)])
        args = args0.prepend(w_self)

        w_res = space.call_args(w_g, args)
        assert space.is_true(space.eq(w_res, space.wrap(('g', 'self', 0))))
        # no opt in this case
        assert len(called) == 2
        assert called[0] == 'funcrun'
        called = []

        # higher level interfaces

        w_res = space.call_function(w_g, w_self)
        assert space.is_true(space.eq(w_res, space.wrap(('g', 'self'))))
        assert len(called) == 1
        assert isinstance(called[0], argument.Arguments)
        called = []

        w_res = space.appexec([w_g], """(g):
        return g('self', 11)
        """)
        assert space.is_true(space.eq(w_res, space.wrap(('g', 'self', 11))))
        assert len(called) == 1
        assert isinstance(called[0], argument.Arguments)
        called = []

        w_res = space.appexec([w_g], """(g):
        class A(object):
           m = g # not a builtin function, so works as method
        d = {'A': A}
        exec \"\"\"
# own compiler
a = A()
y = a.m(33)
\"\"\" in d
        return d['y'] == ('g', d['a'], 33)
        """)
        assert space.is_true(w_res)
        assert len(called) == 1
        assert isinstance(called[0], argument.Arguments)

class TestPassThroughArguments_CALL_METHOD(TestPassThroughArguments):

    def setup_class(cls):
        space = gettestobjspace(usemodules=('_stackless',), **{
            "objspace.opcodes.CALL_METHOD": True
            })
        cls.space = space

class AppTestKeywordsToBuiltinSanity(object):

    def test_type(self):
        class X(object):
            def __init__(self, **kw):
                pass
        clash = type.__call__.func_code.co_varnames[0]

        X(**{clash: 33})
        type.__call__(X, **{clash: 33})

    def test_object_new(self):
        class X(object):
            def __init__(self, **kw):
                pass
        clash = object.__new__.func_code.co_varnames[0]

        X(**{clash: 33})
        object.__new__(X, **{clash: 33})


    def test_dict_new(self):
        clash = dict.__new__.func_code.co_varnames[0]

        dict(**{clash: 33})
        dict.__new__(dict, **{clash: 33})

    def test_dict_init(self):
        d = {}
        clash = dict.__init__.func_code.co_varnames[0]

        d.__init__(**{clash: 33})
        dict.__init__(d, **{clash: 33})

    def test_dict_update(self):
        d = {}
        clash = dict.update.func_code.co_varnames[0]

        d.update(**{clash: 33})
        dict.update(d, **{clash: 33})

