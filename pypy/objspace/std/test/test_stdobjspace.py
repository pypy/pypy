import autopath
from pypy.tool import testit

class TestW_StdObjSpace(testit.TestCase):

    def setUp(self):
        self.space = testit.objspace('std')

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
    testit.main()
