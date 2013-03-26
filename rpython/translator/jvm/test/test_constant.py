import py
from rpython.translator.oosupport.test_template.constant import BaseTestConstant
from rpython.translator.jvm.test.runtest import JvmTest

class TestConstant(BaseTestConstant, JvmTest):
    pass
