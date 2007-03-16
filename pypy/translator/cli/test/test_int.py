import py
from pypy.translator.cli.test.runtest import CliTest
from pypy.rpython.test.test_rint import BaseTestRint

class TestCliInt(CliTest, BaseTestRint):
    def test_char_constant(self):
        def dummyfn(i):
            return chr(i)
        res = self.interpret(dummyfn, [ord(' ')])
        assert res == ' '
        # remove the following test, it's not supported by CLI
##        res = self.interpret(dummyfn, [0])
##        assert res == '\0'
        res = self.interpret(dummyfn, [ord('a')])
        assert res == 'a'

    def test_rarithmetic(self):
        pass # it doesn't make sense here

    div_mod_iteration_count = 20
