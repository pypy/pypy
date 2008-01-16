
from pypy.interpreter import gateway
from pypy.interpreter import argument
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
        assert code.signature() == (['x', 'y'], 'hello', None)
        def d(self, w_boo):
            pass
        code = gateway.BuiltinCode(d, unwrap_spec= ['self',
                                                   gateway.W_Root], self_type=gateway.Wrappable)
        assert code.signature() == (['self', 'boo'], None, None)
        def e(space, w_x, w_y, __args__):
            pass
        code = gateway.BuiltinCode(e, unwrap_spec=[gateway.ObjSpace,
                                                   gateway.W_Root,
                                                   gateway.W_Root,
                                                   gateway.Arguments])
        assert code.signature() == (['x', 'y'], 'args', 'keywords')

        def f(space, index):
            pass
        code = gateway.BuiltinCode(f, unwrap_spec=[gateway.ObjSpace, "index"])
        assert code.signature() == (["index"], None, None)


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
        args = argument.Arguments(self.space, [w(123), w(23)], {},
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
        args = gateway.Arguments(self.space, [w(6)], {'hello': w(7),
                                                      'world': w(8)})
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
            return space.wrap(s0+s1)       
        app_g3_ss = gateway.interp2app_temp(g3_ss,
                                         unwrap_spec=[gateway.ObjSpace,
                                                      str,str])
        w_app_g3_ss = space.wrap(app_g3_ss) 
        assert self.space.eq_w(
            space.call(w_app_g3_ss, 
                       space.newtuple([w('foo'), w('bar')]),
                       space.newdict()),
            w('foobar'))
        assert self.space.eq_w(
            space.call_function(w_app_g3_ss, w('foo'), w('bar')),
            w('foobar'))

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
