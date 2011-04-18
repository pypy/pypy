import py
from pypy.translator.cli.test.runtest import CliTest
from pypy.rpython.test.test_rlist import BaseTestRlist
from pypy.rlib.rarithmetic import r_uint

class TestCliList(CliTest, BaseTestRlist):
    def test_recursive(self):
        py.test.skip("CLI doesn't support recursive lists")

    def test_getitem_exc_1(self):
        py.test.skip('fixme!')

    def test_getitem_exc_2(self):
        py.test.skip('fixme!')

    def test_list_unsigned(self):
        def fn(x):
            lst = [r_uint(0), r_uint(1)]
            lst[0] = r_uint(x)
            return lst[0]
        res = self.interpret(fn, [42])
        assert res == 42

    def test_list_bool(self):
        def fn(x):
            lst = [True, False]
            lst[0] = x
            return lst[0]
        res = self.interpret(fn, [False])
        assert res == False
