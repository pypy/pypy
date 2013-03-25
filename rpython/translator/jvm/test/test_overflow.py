import py
from rpython.translator.jvm.test.runtest import JvmTest
from rpython.translator.oosupport.test_template.overflow import BaseTestOverflow

class TestOverflow(BaseTestOverflow, JvmTest):
    pass

