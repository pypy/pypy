import py
from pypy.translator.translator import TranslationContext, graphof
from pypy.jit.hintannotator import HintAnnotator
from pypy.jit.hintbookkeeper import HintBookkeeper
from pypy.jit.hintmodel import *
from pypy.jit.hintrtyper import HintTyper
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.objectmodel import hint
from pypy.annotation import model as annmodel
from pypy.annotation.policy import AnnotatorPolicy
from pypy import conftest


P_OOPSPEC = AnnotatorPolicy()
P_OOPSPEC.oopspec = True

def hannotate(func, argtypes, policy=None, annotator=False):
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
    t = hannotator.translator
    if conftest.option.view:
        t.view()
    if annotator:
        return hs, hannotator
    else:
        return hs

def test_canonical_reprs():
    from pypy.jit import hintrconstant
    htyper = HintTyper(None)
    r_fixed_signed = htyper.fixedrepr(lltype.Signed)
    assert isinstance(r_fixed_signed, hintrconstant.LLFixedConstantRepr)
    assert r_fixed_signed.lowleveltype == lltype.Signed
    r_fixed_signed2 = htyper.fixedrepr(lltype.Signed)
    assert r_fixed_signed2 is r_fixed_signed

def test_simple():
    py.test.skip("in-progress")
    def ll_function(x, y):
        return x + y
    hs, ha  = hannotate(ll_function, [int, int], annotator=True)
    htyper = HintTyper(ha)
    htyper.specialize()

