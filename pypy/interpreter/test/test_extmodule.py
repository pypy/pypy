
import autopath
from pypy.tool import test
from pypy.interpreter.extmodule import ExtModule


class TestExtModule(test.IntTestCase):
    def setUp(self):
        self.space = test.objspace()

        class M(ExtModule):
            __name__ = 'm'
            constant = 678
            def app_egg(self, x):
                return -x
            def foo(self, w_spam):
                return self.space.neg(w_spam)
        self.m = M(self.space)

    def test_app_method(self):
        w = self.space.wrap
        self.assertEqual_w(self.m.egg(w(42)), w(-42))

    def test_app_exported(self):
        w = self.space.wrap
        w_m = w(self.m)
        w_result = self.space.call_method(w_m, 'egg', w(42))
        self.assertEqual_w(w_result, w(-42))

    def test_interp_method(self):
        w = self.space.wrap
        self.assertEqual_w(self.m.app_foo(w(42)), w(-42))

    def test_interp_exported(self):
        w = self.space.wrap
        w_m = w(self.m)
        w_result = self.space.call_method(w_m, 'foo', w(42))
        self.assertEqual_w(w_result, w(-42))

    def test_constant(self):
        w = self.space.wrap
        w_m = w(self.m)
        self.assertEqual_w(self.space.getattr(w_m, w('constant')), w(678))


if __name__ == '__main__':
    test.main()
