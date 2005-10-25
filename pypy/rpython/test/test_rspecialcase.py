from pypy.rpython.lltypesystem.lltype import *
from pypy.rpython.test.test_llinterp import interpret, gengraph

from pypy.translator.ann_override import PyPyAnnotatorPolicy


def test_override_ignore():
    def f():
        pass
    f._annspecialcase_ = "override:ignore"
    def g(i):
        if i == 1:
            return "ab"
        else:
            return f()
    res = interpret(g, [0])
    assert not res
    res = interpret(g, [1])
    assert ''.join(res.chars) == "ab"

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
    t, typer = gengraph(g, [int])
    from pypy.translator import simplify
    from pypy.translator.backendopt import removenoops
    from pypy.objspace.flow.model import checkgraph
    graph = t.getflowgraph(g)
    removenoops.remove_same_as(graph)
    simplify.eliminate_empty_blocks(graph)
    #should not crash:
    checkgraph(graph)
    
def test_meth_override_ignore():
    class X:
        def f(self):
            pass
        f._annspecialcase_ = "override:ignore"
    def g(i):
        x = X()
        if i == 1:
            return "ab"
        else:
            return x.f()

    res = interpret(g, [0])
    assert not res
    res = interpret(g, [1])
    assert ''.join(res.chars) == "ab"
