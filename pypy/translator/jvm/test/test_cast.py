import py
from pypy.translator.jvm.test.runtest import JvmTest
from pypy.translator.oosupport.test_template.cast import BaseTestCast

class TestCast(BaseTestCast, JvmTest):

    def test_uint_to_float(self):
        py.test.skip('fixme!')

    def test_bool_to_float(self):
        py.test.skip('fixme!')
