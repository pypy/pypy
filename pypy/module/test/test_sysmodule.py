import autopath
from pypy.tool import test 

class SysTests(test.TestCase):
    def setUp(self):
        self.space = test.objspace()
        self.sys_w = self.space.get_builtin_module(self.space.wrap("sys"))
    def tearDown(self):
        pass

    def test_stdout_exists(self):
        s = self.space
        self.failUnless_w(s.getattr(self.sys_w, s.wrap("stdout")))

if __name__ == '__main__':
    test.main()

