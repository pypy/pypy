import testsupport
from pypy.objspace.std.moduleobject import W_ModuleObject


class TestW_ModuleObject(testsupport.TestCase):

    def setUp(self):
        self.space = testsupport.stdobjspace()

    def tearDown(self):
        pass

    def test_name(self):
        space = self.space
        w_m = W_ModuleObject(space, space.wrap('somename'))
        self.assertEqual_w(space.getattr(w_m, space.wrap('__name__')),
                           space.wrap('somename'))

    def test_setgetdel(self):
        space = self.space
        w_x = space.wrap(123)
        w_yy = space.w_True
        w_m = W_ModuleObject(space, space.wrap('somename'))
        space.setattr(w_m, space.wrap('x'), w_x)
        space.setattr(w_m, space.wrap('yy'), w_yy)
        self.assertEqual_w(space.getattr(w_m, space.wrap('x')), w_x)
        self.assertEqual_w(space.getattr(w_m, space.wrap('yy')), w_yy)
        space.delattr(w_m, space.wrap('x'))
        self.assertRaises_w(space.w_AttributeError, space.getattr,
                            w_m, space.wrap('x'))
        self.assertEqual_w(space.getattr(w_m, space.wrap('yy')), w_yy)

if __name__ == '__main__':
    testsupport.main()
