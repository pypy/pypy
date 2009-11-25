import py
from pypy.translator.jvm.test.runtest import JvmTest
from pypy.rpython.test.test_rrange import BaseTestRrange

class TestJvmRange(JvmTest, BaseTestRrange):
    def test_rlist_range(self):
        pass # it doesn't make sense here
