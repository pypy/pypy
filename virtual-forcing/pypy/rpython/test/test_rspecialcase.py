from pypy.rpython.lltypesystem.lltype import *
from pypy.rpython.test.test_llinterp import gengraph
from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin, OORtypeMixin

def test_ignore_breaking_transformations():
    def f():
        pass
    f._annspecialcase_ = "override:ignore"
    def g(i):
        if i == 1:
            return "ab"
        else:
            try:
                return f()
            except:
                return "hello!"
    t, typer, graph = gengraph(g, [int])
    from pypy.translator import simplify
    from pypy.translator.backendopt import removenoops
    from pypy.objspace.flow.model import checkgraph
    removenoops.remove_same_as(graph)
    simplify.eliminate_empty_blocks(graph)
    #should not crash:
    checkgraph(graph)

class BaseTestRspecialcase(BaseRtypingTest):

    def test_override_ignore(self):
        def f():
            xxx
        f._annspecialcase_ = "override:ignore"
        def g(i):
            if i == 1:
                return "ab"
            else:
                return f()
        res = self.interpret(g, [0])
        assert not res
        res = self.interpret(g, [1])
        assert self.ll_to_string(res) == "ab"

class TestLLtype(BaseTestRspecialcase, LLRtypeMixin):
    pass

class TestOOtype(BaseTestRspecialcase, OORtypeMixin):
    pass
