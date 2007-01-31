
import py
from pypy.translator.js.test.runtest import JsTest
from pypy.rpython.test.test_rpbc import BaseTestRPBC

class TestJsPBC(JsTest, BaseTestRPBC):
    
    def test_call_memoized_function_with_bools(self):
        py.test.skip("WIP")

    def test_conv_from_None(self):
        py.test.skip("WIP")



