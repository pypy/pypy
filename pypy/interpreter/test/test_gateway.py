
import autopath
from pypy.tool import testit
from pypy.interpreter import gateway

class TestBuiltinCode(testit.IntTestCase):
    def setUp(self):
        self.space = testit.objspace()

    def test_signature(self):
        def c(space, w_x, w_y, *hello_w):
            pass
        code = gateway.BuiltinCode(c)
        self.assertEqual(code.signature(), (['x', 'y'], 'hello', None))
        def d(self, w_boo):
            pass
        code = gateway.BuiltinCode(d)
        self.assertEqual(code.signature(), (['self', 'boo'], None, None))
        def e(space, w_x, w_y, __args__):
            pass
        code = gateway.BuiltinCode(e)
        self.assertEqual(code.signature(), (['x', 'y'], 'args', 'keywords'))

    def test_call(self):
        def c(space, w_x, w_y, *hello_w):
            u = space.unwrap
            w = space.wrap
            self.assertEquals(len(hello_w), 2)
            self.assertEquals(u(hello_w[0]), 0)
            self.assertEquals(u(hello_w[1]), True)
            return w((u(w_x) - u(w_y) + len(hello_w)))
        code = gateway.BuiltinCode(c)
        w = self.space.wrap
        w_dict = self.space.newdict([
            (w('x'), w(123)),
            (w('y'), w(23)),
            (w('hello'), self.space.newtuple([w(0), w(True)])),
            ])
        w_result = code.exec_code(self.space, w_dict, w_dict)
        self.assertEqual_w(w_result, w(102))

    def test_call_args(self):
        def c(space, w_x, w_y, __args__):
            args_w, kwds_w = __args__.unpack()
            u = space.unwrap
            w = space.wrap
            return w((u(w_x) - u(w_y) + len(args_w))
                     * u(kwds_w['boo']))
        code = gateway.BuiltinCode(c)
        w = self.space.wrap
        w_dict = self.space.newdict([
            (w('x'), w(123)),
            (w('y'), w(23)),
            (w('args'), self.space.newtuple([w(0), w(True)])),
            (w('keywords'), self.space.newdict([(w('boo'), w(10))])),
            ])
        w_result = code.exec_code(self.space, w_dict, w_dict)
        self.assertEqual_w(w_result, w(1020))


class TestGateway(testit.IntTestCase):
    def setUp(self):
        self.space = testit.objspace()

    def test_app2interp(self):
        w = self.space.wrap
        def app_g3(a, b):
            return a+b
        g3 = gateway.app2interp_temp(app_g3)
        self.assertEqual_w(g3(self.space, w('foo'), w('bar')), w('foobar'))
        
    def test_interp2app(self):
        space = self.space
        w = space.wrap
        def g3(space, w_a, w_b):
            return space.add(w_a, w_b)
        app_g3 = gateway.interp2app_temp(g3)
        w_app_g3 = space.wrap(app_g3) 
        self.assertEqual_w(
            space.call(w_app_g3, 
                       space.newtuple([w('foo'), w('bar')]),
                       space.newdict([])),
            w('foobar'))
        self.assertEqual_w(
            space.call_function(w_app_g3, w('foo'), w('bar')),
            w('foobar'))

    def test_importall(self):
        w = self.space.wrap
        g = {}
        exec """
def app_g3(a, b):
    return a+b
def app_g1(x):
    return g3('foo', x)
""" in g
        gateway.importall(g, temporary=True)
        g1 = g['g1']
        self.assertEqual_w(g1(self.space, w('bar')), w('foobar'))

    def test_exportall(self):
        w = self.space.wrap
        g = {}
        exec """
def g3(space, w_a, w_b):
    return space.add(w_a, w_b)
def app_g1(x):
    return g3('foo', x)
""" in g
        gateway.exportall(g, temporary=True)
        g1 = gateway.app2interp_temp(g['app_g1'])
        self.assertEqual_w(g1(self.space, w('bar')), w('foobar'))


if __name__ == '__main__':
    testit.main()
