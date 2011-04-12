import py
from pypy.translator.jvm.test.runtest import JvmTest
from pypy.translator.oosupport.test_template.extreme import BaseTestExtreme

class TestExtreme(BaseTestExtreme, JvmTest):

    def test_runtimeerror_due_to_stack_overflow(self):
        py.test.skip('hotspot bug')
