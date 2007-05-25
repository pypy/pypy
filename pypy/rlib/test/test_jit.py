import py
from pypy.rlib.jit import hint, _is_early_constant
from pypy.translator.translator import TranslationContext, graphof
from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin, OORtypeMixin

class TestJIT(BaseRtypingTest, LLRtypeMixin):
    def test_hint(self):
        def f():
            x = hint(5, hello="world")
            return x
        res = self.interpret(f, [])
        assert res == 5

    def test_is_early_constant(self):
        def f(x):
            if _is_early_constant(x):
                return 42
            return 0

        assert f(3) == 0
        res = self.interpret(f, [5])
        assert res == 0

        def g():
            return f(88)
        
        res = self.interpret(g, [])
        assert res == 42



