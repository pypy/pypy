import autopath
from pypy.tool import test 

class SysTests(test.TestCase):
    def setUp(self):
        self.space = test.objspace()
        self.sys_w = self.space.get_builtin_module("sys")
    def tearDown(self):
        pass

    def test_stdout_exists(self):
        s = self.space
        self.failUnless_w(s.getattr(self.sys_w, s.wrap("stdout")))

class AppSysTests(test.AppTestCase):
    def test_path_exists(self):
        import sys
        self.failUnless(hasattr(sys, 'path'), "sys.path gone missing")
    def test_modules_exists(self):
        import sys
        self.failUnless(hasattr(sys, 'modules'), "sys.modules gone missing")
    def test_dict_exists(self):
        import sys
        self.failUnless(hasattr(sys, '__dict__'), "sys.__dict__ gone missing")
    def test_name_exists(self):
        import sys
        self.failUnless(hasattr(sys, '__name__'), "sys.__name__ gone missing")

if __name__ == '__main__':
    test.main()

