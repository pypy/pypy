from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin, OORtypeMixin


class BaseTestGenerator(BaseRtypingTest):

    def test_simple_explicit(self):
        def g(a, b, c):
            yield a
            yield b
            yield c
        def f():
            gen = g(3, 5, 8)
            x = gen.next() * 100
            x += gen.next() * 10
            x += gen.next()
            return x
        res = self.interpret(f, [])
        assert res == 358


class TestLLtype(BaseTestGenerator, LLRtypeMixin):
    pass

class TestOOtype(BaseTestGenerator, OORtypeMixin):
    pass
