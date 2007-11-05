

from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin

class BaseTestRUnicode(BaseRtypingTest):
    def test_simple(self):
        def f(n):
            if n % 2 == 0:
                x = 'xxx'
            else:
                x = u'x\u221Ex'
            return x[n]

        for i in range(0, 3):
            res = self.interpret(f, [i])
            assert res == f(i)

class TestLLtype(BaseTestRUnicode, LLRtypeMixin):
    pass
