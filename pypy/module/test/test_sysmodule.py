import testsupport, unittest
from pypy.interpreter.unittest_w import TestCase_w
from pypy.objspace.std.objspace import StdObjSpace

class SysTests(TestCase_w):
    def setUp(self):
        self.space = StdObjSpace()
        self.sys_w = self.space.getitem(self.space.w_modules,
                                        self.space.wrap("sys"))
    def tearDown(self):
        pass

    def test_stdout_exists(self):
        s = self.space
        self.failUnless_w(s.getattr(self.sys_w, s.wrap("stdout")))

if __name__ == '__main__':
    unittest.main()

