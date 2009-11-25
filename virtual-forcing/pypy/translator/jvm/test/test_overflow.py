import py
from pypy.translator.jvm.test.runtest import JvmTest
from pypy.translator.oosupport.test_template.overflow import BaseTestOverflow

class TestOverflow(BaseTestOverflow, JvmTest):
    pass

