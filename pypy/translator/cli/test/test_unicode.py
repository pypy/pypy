import py
from pypy.translator.cli.test.runtest import CliTest
from pypy.rpython.test.test_runicode import BaseTestRUnicode

# ====> ../../../rpython/test/test_runicode.py

class TestCliUnicode(CliTest, BaseTestRUnicode):

    EMPTY_STRING_HASH = 0

    def test_unichar_const(self):
        py.test.skip("CLI interpret doesn't support unicode for input arguments")
    test_unichar_eq = test_unichar_const
    test_unichar_ord = test_unichar_const
    test_unichar_hash = test_unichar_const
    test_char_unichar_eq = test_unichar_const
    test_char_unichar_eq_2 = test_unichar_const

    def test_getitem_exc(self):
        py.test.skip('fixme!')

    def test_inplace_add(self):
        py.test.skip("CLI tests can't have string as input arguments")
