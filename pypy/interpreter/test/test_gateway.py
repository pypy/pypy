
import autopath
from pypy.interpreter import gateway
import py

class TestBuiltinCode: 
    def test_signature(self):
        def c(space, w_x, w_y, *hello_w):
            pass
        code = gateway.BuiltinCode(c, unwrap_spec=[gateway.ObjSpace,
                                                   gateway.W_Root,
                                                   gateway.W_Root,
                                                   'starargs'])
        assert code.signature() == (['x', 'y'], 'hello', None)
        def d(self, w_boo):
            pass
        code = gateway.BuiltinCode(d, unwrap_spec= ['self',
                                                   gateway.W_Root], self_type=gateway.BaseWrappable)
        assert code.signature() == (['self', 'boo'], None, None)
        def e(space, w_x, w_y, __args__):
            pass
        code = gateway.BuiltinCode(e, unwrap_spec=[gateway.ObjSpace,
                                                   gateway.W_Root,
                                                   gateway.W_Root,
                                                   gateway.Arguments])
        assert code.signature() == (['x', 'y'], 'args', 'keywords')

    def test_call(self):
        def c(space, w_x, w_y, *hello_w):
            u = space.unwrap
            w = space.wrap
            assert len(hello_w) == 2
            assert u(hello_w[0]) == 0
            assert u(hello_w[1]) == True
            return w((u(w_x) - u(w_y) + len(hello_w)))
        code = gateway.BuiltinCode(c, unwrap_spec=[gateway.ObjSpace,
                                                   gateway.W_Root,
                                                   gateway.W_Root,
                                                   'starargs'])
        w = self.space.wrap
        w_dict = self.space.newdict([
            (w('x'), w(123)),
            (w('y'), w(23)),
            (w('hello'), self.space.newtuple([w(0), w(True)])),
            ])
        w_result = code.exec_code(self.space, w_dict, w_dict)
        assert self.space.eq_w(w_result, w(102))

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
        w_dict = self.space.newdict([
            (w('x'), w(123)),
            (w('y'), w(23)),
            (w('args'), self.space.newtuple([w(0), w(True)])),
            (w('keywords'), self.space.newdict([(w('boo'), w(10))])),
            ])
        w_result = code.exec_code(self.space, w_dict, w_dict)
        assert self.space.eq_w(w_result, w(1020))


class TestGateway: 

    def test_app2interp(self):
        w = self.space.wrap
        def app_g3(a, b):
            return a+b
        g3 = gateway.app2interp_temp(app_g3)
        assert self.space.eq_w(g3(self.space, w('foo'), w('bar')), w('foobar'))
        
    def test_app2interp2(self):
    	"""same but using transformed code"""
        w = self.space.wrap
        def noapp_g3(a, b):
            return a+b
        g3 = gateway.app2interp_temp(noapp_g3, gateway.applevelinterp_temp)
        assert self.space.eq_w(g3(self.space, w('foo'), w('bar')), w('foobar'))
        
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
                       space.newdict([])),
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
                       space.newdict([])),
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
                       space.newdict([])),
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
                       space.newdict([])),
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
                       space.newdict([])),
            w(2.0))
        assert self.space.eq_w(
            space.call_function(w_app_g3_if, w(1), w(1.0)),
            w(2.0))

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
        raises(gateway.OperationError,space.call_function,w_app_g3_i,w(2**32))
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


    def test_importall(self):
        w = self.space.wrap
        g = {'app_g3': app_g3}
        gateway.importall(g, temporary=True)
        g3 = g['g3']
        assert self.space.eq_w(g3(self.space, w('bar')), w('foobar'))

##    def test_exportall(self):
##        not used any more


def app_g3(b):
    return 'foo'+b
