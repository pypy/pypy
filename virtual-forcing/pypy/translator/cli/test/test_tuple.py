import py
from pypy.translator.cli.test.runtest import CliTest
from pypy.rpython.test.test_rtuple import BaseTestRtuple

class TestCliTuple(CliTest, BaseTestRtuple):
    def test_builtin_records(self):
        def fn(x, y):
            return x, y
        res = self.interpret(fn, [1.0, 1])
        assert res.item0 == 1.0 and res.item1 == 1
        res = self.interpret(fn, [1.0, 1.0])
        assert res.item0 == 1.0 and res.item1 == 1.0
