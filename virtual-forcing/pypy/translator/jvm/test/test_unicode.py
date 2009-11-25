import py
from pypy.translator.jvm.test.runtest import JvmTest
from pypy.rpython.test.test_runicode import BaseTestRUnicode

# ====> ../../../rpython/test/test_runicode.py

class TestJvmUnicode(JvmTest, BaseTestRUnicode):

    EMPTY_STRING_HASH = 0

    def test_unichar_const(self):
        def fn():
            return u'\u03b1'
        assert self.interpret(fn, []) == u'\u03b1'

    def test_unichar_eq(self):
        py.test.skip("JVM doesn't support unicode for command line arguments")
    test_unichar_ord = test_unichar_eq
    test_unichar_hash = test_unichar_eq
    test_char_unichar_eq = test_unichar_eq
    test_char_unichar_eq_2 = test_unichar_eq

    def test_getitem_exc(self):
        py.test.skip('fixme!')

    def test_unicode_constant(self):
        const = u''.join(map(unichr, range(0, 256)))
        const = const + u'\ufffd'
        def fn():
            return const
        res = self.interpret(fn, [])
        assert res == const
