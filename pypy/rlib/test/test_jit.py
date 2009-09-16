import py
from pypy.rlib.jit import hint, we_are_jitted, JitDriver
from pypy.translator.translator import TranslationContext, graphof
from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin, OORtypeMixin
from pypy.rpython.lltypesystem import lltype

class BaseTestJIT(BaseRtypingTest):
    def test_hint(self):
        def f():
            x = hint(5, hello="world")
            return x
        res = self.interpret(f, [])
        assert res == 5

    def test_we_are_jitted(self):
        def f(x):
            try:
                if we_are_jitted():
                    return x
                return x + 1
            except Exception:
                return 5
        res = self.interpret(f, [4])
        assert res == 5


    def test_annotate_hooks(self):
        
        def can_inline(m): pass
        def get_printable_location(m): pass
        def leave(m, n): pass
        
        myjitdriver = JitDriver(greens=['m'], reds=['n'],
                                can_inline=can_inline,
                                get_printable_location=get_printable_location,
                                leave=leave)
        def fn(n):
            m = 42.5
            while n > 0:
                myjitdriver.can_enter_jit(m=m, n=n)
                myjitdriver.jit_merge_point(m=m, n=n)
                n -= 1
            return n

        t, rtyper, fngraph = self.gengraph(fn, [int])

        def getargs(func):
            for graph in t.graphs:
                if getattr(graph, 'func', None) is func:
                    return [v.concretetype for v in graph.getargs()]
            raise Exception, 'function %r has not been annotated' % func

        leave_args = getargs(leave)
        assert leave_args == [lltype.Float, lltype.Signed]

        can_inline_args = getargs(can_inline)
        get_printable_location_args = getargs(get_printable_location)
        assert can_inline_args == get_printable_location_args == [lltype.Float]


class TestJITLLtype(BaseTestJIT, LLRtypeMixin):
    pass

class TestJITOOtype(BaseTestJIT, OORtypeMixin):
    pass
