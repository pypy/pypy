from pypy import conftest
from pypy.translator.translator import graphof
from pypy.jit.timeshifter.test.test_timeshift import hannotate
from pypy.jit.timeshifter.rtyper import HintRTyper
from pypy.jit.codegen.llgraph.rgenop import RGenOp
from pypy.rpython.llinterp import LLInterpreter
from pypy.objspace.flow.model import checkgraph

from pypy.rpython.objectmodel import hint


def timeshift_from_portal(main, portal, main_args):
    hs, ha, rtyper = hannotate(main, main_args, portal=portal)

    # make the timeshifted graphs
    hrtyper = HintRTyper(ha, rtyper, RGenOp)
    t = rtyper.annotator.translator
    origportalgraph = graphof(t, portal)
    hrtyper.specialize(origportalgraph=origportalgraph,
                       view = conftest.option.view)

    for graph in ha.translator.graphs:
        checkgraph(graph)
        t.graphs.append(graph)

    if conftest.option.view:
        t.view()
    maingraph = graphof(t, main)

    llinterp = LLInterpreter(rtyper)

    return llinterp.eval_graph(maingraph, main_args)


def test_simple():

    def main(code, x):
        return evaluate(code, x)

    def evaluate(y, x):
        hint(y, concrete=True)
        z = y+x
        return z

    res = timeshift_from_portal(main, evaluate, [3, 2])

    assert res == 5
    
