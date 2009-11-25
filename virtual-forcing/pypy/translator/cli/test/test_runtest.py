import py
from pypy.translator.oosupport.test_template.runtest import BaseTestRunTest
from pypy.translator.cli.test.runtest import CliTest

class TestRunTest(BaseTestRunTest, CliTest):

    def test_auto_raise_exc(self):
        def fn():
            raise ValueError
        f = self._compile(fn, [], auto_raise_exc=True)
        py.test.raises(ValueError, f)

    def test_big_arglist(self):
        def fn(a0, a1, a2, a3, a4, a5, a6, a7, a8, a9):
            return a0
        res = self.interpret(fn, [42]*10)
        assert res == 42

    def test_input_string(self):
        def fn(s):
            return len(s)
        res = self.interpret(fn, ["hello"])
        assert res == 5
