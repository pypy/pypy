import py
from pypy.rpython.test.test_rdict import TestOOtype as _TestOOtype
from pypy.rpython.test.test_remptydict import BaseTestRemptydict
from pypy.rpython.test.test_rconstantdict import BaseTestRconstantdict

class BaseTestDict(_TestOOtype):
    def test_dict_of_void(self):
        class A: pass
        def f():
            d2 = {A(): None, A(): None}
            return len(d2)
        res = self.interpret(f, [])
        assert res == 2

    def test_dict_of_void_iter(self):
        def f():
            d = {1: None, 2: None, 3: None}
            total = 0
            for key, value in d.iteritems():
                total += key
            return total
        assert self.interpret(f, []) == 6

class BaseTestEmptyDict(BaseTestRemptydict):
    pass

class BaseTestConstantDict(BaseTestRconstantdict):
    def test_tuple_as_key(self):
        mydict = {('r',): 42}
        def fn(ch):
            return mydict[(ch,)]
        assert self.interpret(fn, ['r']) == 42
