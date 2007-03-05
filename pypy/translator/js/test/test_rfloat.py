
import py
from pypy.translator.js.test.runtest import JsTest
from pypy.rpython.test.test_rfloat import BaseTestRfloat

class TestJsFloat(JsTest, BaseTestRfloat):
    def test_from_r_uint(self):
        py.test.skip("Not implemented")
