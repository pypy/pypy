import testsupport

class SysTests(testsupport.TestCase):
    def setUp(self):
        self.space = testsupport.objspace()
        self.sys_w = self.space.getitem(self.space.w_modules,
                                        self.space.wrap("sys"))
    def tearDown(self):
        pass

    def test_stdout_exists(self):
        s = self.space
        self.failUnless_w(s.getattr(self.sys_w, s.wrap("stdout")))

if __name__ == '__main__':
    testsupport.main()

