
import autopath
import os
from pypy.tool import testit
from pypy.interpreter.extmodule import BuiltinModule


class TestBuiltinModule(testit.IntTestCase):
    def setUp(self):
        self.space = testit.objspace()

    def test_foomodule(self):
        space = self.space
        sourcefile = os.path.join(autopath.this_dir, 'foomodule.py')
        m = BuiltinModule(space, 'foo', sourcefile=sourcefile)
        w = space.wrap
        w_m = space.wrap(m)
        self.assertEqual_w(space.getattr(w_m, w('__name__')), w('foo'))
        self.assertEqual_w(space.getattr(w_m, w('__file__')), w(sourcefile))
        # check app-level definitions
        self.assertEqual_w(m.w_foo, space.w_Ellipsis)
        self.assertEqual_w(space.getattr(w_m, w('foo1')), space.w_Ellipsis)
        self.assertEqual_w(space.getattr(w_m, w('foo')), space.w_Ellipsis)
        self.assertEqual_w(space.call_method(w_m, 'bar', w(4), w(3)), w(12))
        self.assertEqual_w(space.getattr(w_m, w('foo2')), w('hello'))
        self.assertEqual_w(space.getattr(w_m, w('foo3')), w('hi, guido!'))
        # check interp-level definitions
        self.assertEqual_w(m.w_foo2, w('hello'))
        self.assertEqual_w(m.foobuilder(w('xyzzy')), w('hi, xyzzy!'))
        self.assertEqual_w(m.fortytwo, w(42))


if __name__ == '__main__':
    testit.main()
