from pypy.translator.cli.test.runtest import CliTest
from pypy.translator.cli.dotnet import Math

class TestDotnet(CliTest):

    def test_abs(self):
        def fn(x):
            return Math.Abs(x)
        assert self.interpret(fn, [-42]) == 42
