import py
from pypy.translator.jvm.test.runtest import JvmTest
from pypy.rpython.test.test_rlist import BaseTestRlist

class TestJvmList(JvmTest, BaseTestRlist):
    def test_recursive(self):
        py.test.skip("JVM doesn't support recursive lists")
    
    def test_getitem_exc_1(self):
        py.test.skip('fixme!')

    def test_getitem_exc_2(self):
        py.test.skip('fixme!')

    def test_r_short_list(self):
        py.test.skip('fixme!')

    def test_zeroed_list(self):
        def fn():
            lst = [0] * 16
            return lst[0]
        res = self.interpret(fn, [])
        assert res == 0

    def test_bool_fixed_list(self):
        """ Tests that we handle boolean fixed lists, which do not require
        boxing or unboxing """
        def fn(i):
            lst = [False, True]
            if lst[i]:
                return 22
            else:
                return 44
        for i in range(0,2):
            res = self.interpret(fn, [i])
            assert res == fn(i)
        
