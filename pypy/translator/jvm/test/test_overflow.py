import py
from pypy.translator.jvm.test.runtest import JvmTest
from pypy.translator.oosupport.test_template.overflow import BaseTestOverflow

class TestOverflow(BaseTestOverflow, JvmTest):
    #def test_sub(self):
    #    py.test.skip('fixme!')

    def test_lshift(self):
        py.test.skip('fixme!')



