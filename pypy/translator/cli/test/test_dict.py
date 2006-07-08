import py
from pypy.translator.cli.test.runtest import CliTest
from pypy.rpython.test.test_rdict import BaseTestRdict

class TestCliDict(CliTest, BaseTestRdict):
    def test_dict_of_void(self):
        class A: pass
        def f():
            d2 = {A(): None, A(): None}
            return len(d2)
        res = self.interpret(f, [])
        assert res == 2

    def test_dict_of_dict(self):
        py.test.skip("CLI doesn't support recursive dicts")
