
import autopath
from pypy.tool import test
from pypy.interpreter.module import Module


class TestModule(test.IntTestCase):
    def setUp(self):
        self.space = test.objspace()
        self.m = Module(self.space, self.space.wrap('m'))

    def test_name(self):
        w = self.space.wrap
        w_m = w(self.m)
        self.assertEqual_w(self.space.getattr(w_m, w('__name__')), w('m'))

    def test_attr(self):
        w = self.space.wrap
        w_m = w(self.m)
        self.space.setattr(w_m, w('x'), w(15))
        self.assertEqual_w(self.space.getattr(w_m, w('x')), w(15))
        self.space.delattr(w_m, w('x'))
        self.assertRaises_w(self.space.w_AttributeError,
                            self.space.delattr, w_m, w('x'))

class Test_ModuleObject(test.AppTestCase):

    def setUp(self):
        self.space = test.objspace()
        
    def test_attr(self):
        m = __import__('__builtin__')
        m.x = 15
        self.assertEqual(m.x, 15)
        self.assertEqual(getattr(m, 'x'), 15)
        setattr(m, 'x', 23)
        self.assertEqual(m.x, 23)
        self.assertEqual(getattr(m, 'x'), 23)
        del m.x
        self.assertRaises(AttributeError, getattr, m, 'x')
        m.x = 15
        delattr(m, 'x')
        self.assertRaises(AttributeError, getattr, m, 'x')
        self.assertRaises(AttributeError, delattr, m, 'x')

if __name__ == '__main__':
    test.main()
