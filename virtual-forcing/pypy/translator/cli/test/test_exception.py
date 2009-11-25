import py
from pypy.translator.cli.test.runtest import CliTest
from pypy.translator.oosupport.test_template.exception import BaseTestException

class TestCliException(CliTest, BaseTestException):
    use_exception_transformer = False
    backendopt = False

    def interpret(self, *args, **kwds):
        kwds['exctrans'] = self.use_exception_transformer
        return CliTest.interpret(self, *args, **kwds)

    def test_raise_and_catch_other(self):
        pass

    def test_raise_prebuilt_and_catch_other(self):
        pass


class TestCliExceptionTransformer(TestCliException):
    use_exception_transformer = True
    backendopt = False
