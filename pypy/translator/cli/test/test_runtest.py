from pypy.translator.cli.test.runtest import CliTest
from pypy.translator.cli.test.runtest import FLOAT_PRECISION

def ident(x):
    return x

class TestRunTest(CliTest):

    def test_int(self):
        assert self.interpret(ident, [42]) == 42
    
    def test_bool(self):
        assert self.interpret(ident, [True]) == True
        assert self.interpret(ident, [False]) == False

    def test_float(self):
        x = 10/3.0
        res = self.interpret(ident, [x])
        assert round(x, FLOAT_PRECISION) == round(res, FLOAT_PRECISION)

    def test_char(self):
        assert self.interpret(ident, ['a']) == 'a'

    def test_list(self):
        def fn():
            return [1, 2, 3]
        assert self.interpret(fn, []) == [1, 2, 3]
