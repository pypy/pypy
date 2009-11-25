import py
from pypy.translator.jvm.test.runtest import JvmTest
from pypy.translator.oosupport.test_template.exception import BaseTestException

class TestJvmException(JvmTest, BaseTestException):

    def test_raise_and_catch_other(self):
        pass

    def test_raise_prebuilt_and_catch_other(self):
        pass
