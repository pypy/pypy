import py
from pypy.translator.oosupport.test_template.constant import BaseTestConstant
from pypy.translator.jvm.test.runtest import JvmTest

class TestConstant(BaseTestConstant, JvmTest):

    def test_many_constants(self):
        py.test.skip('Initializing a large constant list generates a function too large for the JVM limits')
