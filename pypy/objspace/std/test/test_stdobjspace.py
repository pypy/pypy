import autopath
from pypy.interpreter.error import OperationError


objspacename = 'std'

class TestW_StdObjSpace:

    def test_wrap_wrap(self):
        raises(TypeError,
                          self.space.wrap,
                          self.space.wrap(0))

    def test_str_w_non_str(self):
        raises(OperationError,self.space.str_w,self.space.wrap(None))
        raises(OperationError,self.space.str_w,self.space.wrap(0))

    def test_int_w_non_int(self):
        raises(OperationError,self.space.int_w,self.space.wrap(None))
        raises(OperationError,self.space.int_w,self.space.wrap(""))        

    def hopeful_test_exceptions(self):
        self.apptest("self.failUnless(issubclass(ArithmeticError, Exception))")
        self.apptest("self.failIf(issubclass(ArithmeticError, KeyError))")
