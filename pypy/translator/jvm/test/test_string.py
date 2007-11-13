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
    test_char_unichar_eq = test_unichar_const
    test_char_unichar_eq_2 = test_unichar_const

    def test_upper(self):
        py.test.skip("eval has trouble with evaluation of null literals")
    test_lower = test_upper

    def test_getitem_exc(self):
        # This test is supposed to crash in a system specific way;
        # in our case an StringIndexOutOfBounds exception is thrown,
        # but we don't bother to make runtest understand how to parse that,
        # so we just skip the test.
        py.test.skip("test fails in JVM specific way")

    def test_string_constant(self):
        const = ''.join(map(chr, range(0, 256)))
        def fn():
            return const
        res = self.interpret(fn, [])
        assert res == const
