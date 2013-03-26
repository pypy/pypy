import py
from rpython.translator.jvm.test.runtest import JvmTest
from rpython.rtyper.test.test_rrange import BaseTestRrange

class TestJvmRange(JvmTest, BaseTestRrange):
    def test_rlist_range(self):
        pass # it doesn't make sense here
