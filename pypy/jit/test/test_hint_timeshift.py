import py
from pypy.translator.translator import TranslationContext, graphof
from pypy.jit.hintannotator import HintAnnotator
from pypy.jit.hintbookkeeper import HintBookkeeper
from pypy.jit.hintmodel import *
from pypy.jit.hinttimeshift import HintTimeshift
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.objectmodel import hint
from pypy.annotation import model as annmodel
from pypy.annotation.policy import AnnotatorPolicy
from pypy import conftest


P_OOPSPEC = AnnotatorPolicy()
P_OOPSPEC.oopspec = True

def hannotate(func, argtypes, policy=None):
    # build the normal ll graphs for ll_function
    t = TranslationContext()
    a = t.buildannotator()
    a.build_types(func, argtypes)
    rtyper = t.buildrtyper()
    rtyper.specialize()
    graph1 = graphof(t, func)
    # build hint annotator types
    hannotator = HintAnnotator(policy=policy)
    hannotator.base_translator = t
    hs = hannotator.build_types(graph1, [SomeLLAbstractConstant(v.concretetype,
                                                                {OriginFlags(): True})
                                         for v in graph1.getargs()])
    if conftest.option.view:
        hannotator.translator.view()
    return hs, hannotator, rtyper

def timeshift(ll_function, argtypes):
    hs, ha, rtyper = hannotate(ll_function, argtypes)
    htshift = HintTimeshift(ha, rtyper)
    htshift.timeshift()
    t = rtyper.annotator.translator
    t.graphs.extend(ha.translator.graphs)
    if conftest.option.view:
        t.view()

def test_simple_fixed():
    def ll_function(x, y):
        return hint(x + y, concrete=True)
    timeshift(ll_function, [int, int])

def test_simple():
    def ll_function(x, y):
        return x + y
    timeshift(ll_function, [int, int])
