import py
from pypy.translator.cli.test.runtest import CliTest
from pypy.rpython.test.test_rfloat import BaseTestRfloat

class TestCliFloat(CliTest, BaseTestRfloat):

    inf = 'Infinity'
    minus_inf = '-Infinity'
    nan = 'NaN'

    def test_parse_float(self):
        ex = ['', '    ', '0', '1', '-1.5', '1.5E2', '2.5e-1', ' 0 ', '?']
        def fn(i):
            s = ex[i]
            try:
                return float(s)
            except ValueError:
                return -999.0
        
        for i in range(len(ex)):
            expected = fn(i)
            res = self.interpret(fn, [i])
            assert res == expected

    def test_r_singlefloat(self):
        py.test.skip("not implemented: single-precision floats")
