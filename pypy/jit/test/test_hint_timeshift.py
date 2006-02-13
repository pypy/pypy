import py
from pypy.translator.translator import TranslationContext, graphof
from pypy.jit.hintannotator import HintAnnotator
from pypy.jit.hintbookkeeper import HintBookkeeper
from pypy.jit.hintmodel import *
from pypy.jit.hinttimeshift import HintTimeshift
from pypy.jit import rtimeshift, hintrtyper
from pypy.jit.test.test_llabstractinterp import annotation, summary
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.objectmodel import hint
from pypy.rpython import rgenop
from pypy.annotation import model as annmodel
from pypy.rpython.llinterp import LLInterpreter
from pypy.objspace.flow.model import checkgraph
from pypy import conftest


def hannotate(func, values, policy=None):
    # build the normal ll graphs for ll_function
    t = TranslationContext()
    a = t.buildannotator()
    argtypes = [annotation(a, x) for x in values]
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

def timeshift(ll_function, values, opt_consts=[]):
    hs, ha, rtyper = hannotate(ll_function, values)
    htshift = HintTimeshift(ha, rtyper)
    htshift.timeshift()
    t = rtyper.annotator.translator
    for graph in ha.translator.graphs:
        checkgraph(graph)
        t.graphs.append(graph)
    if conftest.option.view:
        t.view()
    # run the time-shifted graph-producing graphs
    graph1 = ha.translator.graphs[0]
    jitstate = rtimeshift.ll_setup_jitstate()
    graph1args = [jitstate]
    residual_graph_args = []
    assert len(graph1.getargs()) == 1 + len(values)
    for i, (v, llvalue) in enumerate(zip(graph1.getargs()[1:], values)):
        r = htshift.hrtyper.bindingrepr(v)
        residual_v = r.residual_values(llvalue)
        if len(residual_v) == 0:
            # green
            graph1args.append(llvalue)
        else:
            # red
            assert residual_v == [llvalue], "XXX for now"
            TYPE = htshift.originalconcretetype(v)
            box = rtimeshift.ll_input_redbox(jitstate, TYPE)
            if i in opt_consts: # XXX what should happen here interface wise is unclear
                box = rtimeshift.REDBOX.ll_make_from_const(llvalue)
            graph1args.append(box)
            residual_graph_args.append(llvalue)
    llinterp = LLInterpreter(rtyper)
    result1 = llinterp.eval_graph(graph1, graph1args)
    # now try to run the block produced by the jitstate
    r = htshift.hrtyper.bindingrepr(graph1.getreturnvar())
    if isinstance(r, hintrtyper.GreenRepr):
        result_gvar = rgenop.genconst(result1)
    elif isinstance(r, hintrtyper.RedRepr):
        result_gvar = rtimeshift.ll_gvar_from_redbox(jitstate, result1, r.original_concretetype)
    else:
        raise NotImplementedError(r)
    jitblock = rtimeshift.ll_close_jitstate(jitstate, result_gvar)
    residual_graph = rgenop.buildgraph(jitblock)
    insns = summary(residual_graph)
    res = rgenop.testgengraph(residual_graph, residual_graph_args,
                              viewbefore = conftest.option.view)
    return insns, res

def test_simple_fixed():
    def ll_function(x, y):
        return hint(x + y, concrete=True)
    insns, res = timeshift(ll_function, [5, 7])
    assert res == 12
    assert insns == {}

def test_simple():
    def ll_function(x, y):
        return x + y
    insns, res = timeshift(ll_function, [5, 7])
    assert res == 12
    assert insns == {'int_add': 1}

def test_convert_const_to_redbox():
    def ll_function(x, y):
        x = hint(x, concrete=True)
        tot = 0
        while x:    # conversion from green '0' to red 'tot'
            tot += y
            x -= 1
        return tot
    insns, res = timeshift(ll_function, [7, 2])
    assert res == 14
    assert insns == {'int_add': 7}

def test_simple_opt_const_propagation2():
    def ll_function(x, y):
        return x + y
    insns, res = timeshift(ll_function, [5, 7], [0, 1])
    assert res == 12
    assert insns == {}

def test_simple_opt_const_propagation1():
    def ll_function(x):
        return -x
    insns, res = timeshift(ll_function, [5], [0])
    assert res == -5
    assert insns == {}

def test_loop_merge():
    def ll_function(x, y):
        tot = 0
        x = hint(x, concrete=True)        
        while x:
            tot += y
            x -= 1
        return tot
    insns, res = timeshift(ll_function, [7, 2], [0, 1])
    assert res == 14
    # not really testing merge logic properly, we would need both a split
    # (on a red exitswitch) and a join for that, just that the new code doesn't explode
