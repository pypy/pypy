import py
from rpython.translator.jvm.test.runtest import JvmTest
from rpython.translator.oosupport.test_template.extreme import BaseTestExtreme

class TestExtreme(BaseTestExtreme, JvmTest):

    def test_runtimeerror_due_to_stack_overflow(self):
        py.test.skip('hotspot bug')
