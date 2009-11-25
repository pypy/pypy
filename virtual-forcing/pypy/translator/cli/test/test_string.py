import py
from pypy.translator.cli.test.runtest import CliTest
import pypy.translator.oosupport.test_template.string as oostring

class TestCliString(CliTest, oostring.BaseTestString):

    EMPTY_STRING_HASH = 0

    def test_unichar_const(self):
        py.test.skip("CLI interpret doesn't support unicode for input arguments")
    test_unichar_eq = test_unichar_const
    test_unichar_ord = test_unichar_const
    test_unichar_hash = test_unichar_const
    test_char_unichar_eq = test_unichar_const
    test_char_unichar_eq_2 = test_unichar_const

    def test_upper(self):
        py.test.skip("CLI doens't support backquotes inside string literals")
    test_lower = test_upper

    def test_hlstr(self):
        py.test.skip("CLI tests can't have string as input arguments")

    test_inplace_add = test_hlstr

    def test_getitem_exc(self):
        py.test.skip('fixme!')

    def test_compare(self):
        strings = ['aa', 'ZZ']
        def fn(i, j):
            return strings[i] < strings[j]
        assert self.interpret(fn, [0, 1], backendopt=False) == fn(0, 1)

    def test_literal_length(self):
        strings = ['aa', 'a\x01', 'a\x00']
        def fn():
            for s in strings:
                assert len(s) == 2
        self.interpret(fn, [], backendopt=False)
