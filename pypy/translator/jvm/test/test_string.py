import py
from pypy.translator.jvm.test.runtest import JvmTest
import pypy.translator.oosupport.test_template.string as oostring

class TestJvmString(JvmTest, oostring.BaseTestString):

    EMPTY_STRING_HASH = 0
    
    def test_unichar_const(self):
        py.test.skip("JVM doesn't support unicode for command line arguments")
    test_unichar_eq = test_unichar_const
    test_unichar_ord = test_unichar_const
    test_unichar_hash = test_unichar_const

    def test_upper(self):
        py.test.skip("eval has trouble with evaluation of null literals")
    test_lower = test_upper

    def test_float(self):
        py.test.skip("JVM does not yet support ooparse_float")

    def test_getitem_exc(self):
        py.test.skip("TODO: Appears to be a bug in test_rstr.py??")
