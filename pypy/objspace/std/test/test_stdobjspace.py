import autopath

objspacename = 'std'

class TestW_StdObjSpace:

    def test_wrap_wrap(self):
        raises(TypeError,
                          self.space.wrap,
                          self.space.wrap(0))

    def hopeful_test_exceptions(self):
        self.apptest("self.failUnless(issubclass(ArithmeticError, Exception))")
        self.apptest("self.failIf(issubclass(ArithmeticError, KeyError))")
