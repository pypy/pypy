from pypy.translator.oosupport.test_template.runtest import BaseTestRunTest
from pypy.translator.jvm.test.runtest import JvmTest

class TestRunTest(BaseTestRunTest, JvmTest):
    def test_big_ullong(self):
        import py
        py.test.skip('fixme!')
