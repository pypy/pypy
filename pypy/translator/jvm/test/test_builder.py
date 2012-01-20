from pypy.translator.jvm.test.runtest import JvmTest
from pypy.rpython.test.test_rbuilder import BaseTestStringBuilder
import py

class TestJvmStringBuilder(JvmTest, BaseTestStringBuilder):
    def test_append_charpsize(self):
        py.test.skip("append_charpsize(): not implemented on ootype")
