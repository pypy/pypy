import testsupport

class TestW_StdObjSpace(testsupport.TestCase):

    def setUp(self):
        self.space = testsupport.stdobjspace()

    def tearDown(self):
        pass

    def test_wrap_wrap(self):
        self.assertRaises(TypeError,
                          self.space.wrap,
                          self.space.wrap(0))

    def hopeful_test_exceptions(self):
        self.apptest("self.failUnless(issubclass(ArithmeticError, Exception))")
        self.apptest("self.failIf(issubclass(ArithmeticError, KeyError))")


if __name__ == '__main__':
    testsupport.main()
