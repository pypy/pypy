from pypy.translator.translator import TranslationContext, graphof
from pypy.jit.hintannotator import HintAnnotator
from pypy.jit.hintmodel import *
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.objectmodel import hint

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


def test_simple_hint_result():
    def ll_function(cond, x,y):
        if cond:
            z = x+y
        else:
            z = x-y
        z = hint(z, concrete=True)
        return z
    hs = hannotate(ll_function, [bool, int, int])
    assert isinstance(hs, SomeLLConcreteValue)
    assert hs.concretetype == lltype.Signed
  
def test_simple_hint_origins():
    def ll_function(cond, x,y):
        if cond:
            z = x+y
        else:
            z = x-y
        z1 = hint(z, concrete=True)
        return z # origin of z1
    hs = hannotate(ll_function, [bool, int, int])
    assert isinstance(hs, SomeLLAbstractConstant)
    assert len(hs.origins) == 2
    for o in hs.origins:
        assert o.fixed
        assert len(o.origins) == 2
        for o in o.origins:
            assert o.fixed
            assert not o.origins
    assert hs.concretetype == lltype.Signed
 
def test_simple_variable():
    def ll_function(x,y):
        x = hint(x, variable=True) # special hint only for testing purposes!!!
        return x + y
    hs = hannotate(ll_function, [int, int])
    assert type(hs) is SomeLLAbstractValue
    assert hs.concretetype == lltype.Signed
    
def test_simple_concrete_propagation():
    def ll_function(x,y):
        x = hint(x, concrete=True)
        return x + y
    hs = hannotate(ll_function, [int, int])
    assert type(hs) is SomeLLConcreteValue
    assert hs.concretetype == lltype.Signed
     
