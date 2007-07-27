import py
from pypy.translator.jvm.test.runtest import JvmTest
from pypy.translator.oosupport.test_template.overflow import BaseTestOverflow

class TestOverflow(BaseTestOverflow, JvmTest):

    def test_lshift(self):
        py.test.skip('Shift is currently not implemented in src/PyPy.java because the C version interacts with Pypy directly, and it\'s not clear how to do that in Java')



