import py
from pypy.translator.cli.test.runtest import CliTest
from pypy.rpython.test.test_rstr import BaseTestRstr

class TestCliString(CliTest, BaseTestRstr):
    def test_char_isxxx(self):
        def fn(s):
            return (s.isspace()      |
                    s.isdigit() << 1 |
                    s.isalpha() << 2 |
                    s.isalnum() << 3 |
                    s.isupper() << 4 |
                    s.islower() << 5)
        # need to start from 1, because we cannot pass '\x00' as a command line parameter        
        for i in range(1, 128):
            ch = chr(i)
            res = self.interpret(fn, [ch])
            assert res == fn(ch)

    def test_unichar_const(self):
        py.test.skip("CLI interpret doesn't support unicode for input arguments")
    test_unichar_eq = test_unichar_const
    test_unichar_ord = test_unichar_const
    test_unichar_hash = test_unichar_const

    def test_upper(self):
        py.test.skip("CLI doens't support backquotes inside string literals")
    test_lower = test_upper

    def test_replace_TyperError(self):
        pass # it doesn't make sense here

    def test_int(self):
        py.test.skip("CLI doesn't support integer parsing, yet")
    test_int_valueerror = test_int
