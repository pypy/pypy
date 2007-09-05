import py
from pypy.translator.jvm.test.runtest import JvmTest
from pypy.translator.oosupport.test_template.cast import BaseTestCast

class TestCast(BaseTestCast, JvmTest):

    def test_cast_primitive(self):
        py.test.skip('fixme!')
