import py
from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin, OORtypeMixin

class BaseTestRemptydict(BaseRtypingTest):
    def test_empty_dict(self):
        class A:
            pass
        a = A()
        a.d1 = {}
        def func():
            a.d2 = {}
            return bool(a.d1) or bool(a.d2)
        res = self.interpret(func, [])
        assert res is False

    def test_iterate_over_empty_dict(self):
        def f():
            n = 0
            d = {}
            for x in []:                n += x
            for y in d:                 n += y
            for z in d.iterkeys():      n += z
            for s in d.itervalues():    n += s
            for t, u in d.items():      n += t * u
            for t, u in d.iteritems():  n += t * u
            return n
        res = self.interpret(f, [])
        assert res == 0

class TestLLtype(BaseTestRemptydict, LLRtypeMixin):
    pass

class TestOOtype(BaseTestRemptydict, OORtypeMixin):
    def test_almost_empty_dict(self):
        def f(flag):
            d = {}
            if flag:
                d[None] = None
            return None in d
        assert self.interpret(f, [True]) is True
        assert self.interpret(f, [False]) is False
