import py
from pypy.tool import udir
from pypy.translator.jvm.test.runtest import JvmTest
from pypy.rpython.test.test_rbuiltin import BaseTestRbuiltin

class TestJavaBuiltin(JvmTest, BaseTestRbuiltin):
    def test_os(self):
        py.test.skip("Jvm os support uncertain")

