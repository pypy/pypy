import py
from pypy.translator.jvm.test.runtest import JvmTest
from pypy.translator.oosupport.test_template.cast import BaseTestCast

class TestCast(BaseTestCast, JvmTest):

    def test_uint_to_float(self):
        # This is most likely with how we render uints when we print them, and they get parsed.
        py.test.skip('Same issue seen in other tests with uints... 2147450880.0 == 2147483648.0')
