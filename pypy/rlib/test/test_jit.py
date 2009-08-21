import py
from pypy.rlib.jit import hint
from pypy.translator.translator import TranslationContext, graphof
from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin, OORtypeMixin

class TestJIT(BaseRtypingTest, LLRtypeMixin):
    def test_hint(self):
        def f():
            x = hint(5, hello="world")
            return x
        res = self.interpret(f, [])
        assert res == 5
