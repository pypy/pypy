from pypy.translator.translator import TranslationContext, graphof
from pypy.jit.hintannotator import HintAnnotator
from pypy.jit.hintmodel import SomeLLAbstractConstant, OriginTreeNode
from pypy.rpython.lltypesystem import lltype

def hannotate(func, argtypes):
    # build the normal ll graphs for ll_function
    t = TranslationContext()
    a = t.buildannotator()
    a.build_types(func, argtypes)
    rtyper = t.buildrtyper()
    rtyper.specialize()
    graph1 = graphof(t, func)
    # build hint annotator types
    hannotator = HintAnnotator()
    hs = hannotator.build_graph_types(graph1, [SomeLLAbstractConstant(v.concretetype,
                                                                      {OriginTreeNode(): True})
                                               for v in graph1.getargs()])
    return hs

def test_simple():
    def ll_function(x, y):
        return x + y
    hs = hannotate(ll_function, [int, int])
    assert isinstance(hs, SomeLLAbstractConstant)
    assert len(hs.origins) == 1
    assert hs.concretetype == lltype.Signed

def test_join():
    def ll_function(cond, x,y):
        if cond:
            z = x+y
        else:
            z = x-y
        return z
    hs = hannotate(ll_function, [bool, int, int])
    assert isinstance(hs, SomeLLAbstractConstant)
    assert len(hs.origins) == 2
    assert hs.concretetype == lltype.Signed
