from pypy.translator.backendopt.removenoops import remove_void, remove_same_as, \
        remove_unaryops
from pypy.translator.backendopt.inline import inline_function
from pypy.translator.translator import TranslationContext, graphof
from pypy.translator.test.snippet import simple_method
from pypy.objspace.flow.model import checkgraph, flatten, Block
from pypy.rpython.lltypesystem.lltype import Void, Signed
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.llinterp import LLInterpreter

import py
log = py.log.Producer('test_backendoptimization')


def annotate_and_remove_void(f, annotate):
    t = TranslationContext()
    t.buildannotator().build_types(f, annotate)
    t.buildrtyper().specialize()
    remove_void(t)
    return t

def test_remove_void_args():
    def f(i):
        return [1,2,3,i][i]
    t = annotate_and_remove_void(f, [int])
    for graph in t.graphs:
        assert checkgraph(graph) is None
        for arg in graph.startblock.inputargs:
            assert arg.concretetype is not Void
    interp = LLInterpreter(t.rtyper)
    assert interp.eval_graph(graphof(t, f), [0]) == 1 

def test_remove_void_in_struct():
    t = annotate_and_remove_void(simple_method, [int])
    #t.view()
    for graph in t.graphs:
        log('func : ' + graph.name)
        log('graph: ' + str(graph))
        assert checkgraph(graph) is None
        #for fieldname in self.struct._names:    #XXX helper (in lltype?) should remove these voids
        #    type_ = getattr(struct, fieldname)
        #    log('fieldname=%(fieldname)s , type_=%(type_)s' % locals())
        #    assert _type is not Void
    #interp = LLInterpreter(t.flowgraphs, t.rtyper)
    #assert interp.eval_function(f, [0]) == 1 

def test_remove_same_as():
    def nothing(x):
        return x
    def f():
        nothing(False)
        if nothing(True):
            return 42
        else:
            return 666
    t = TranslationContext()
    t.buildannotator().build_types(f, [])
    t.buildrtyper().specialize()
    # now we make the 'if True' appear
    f_graph = graphof(t, f)
    inline_function(t, nothing, f_graph)
    # here, the graph looks like  v21=same_as(True);  exitswitch: v21
    remove_same_as(f_graph)
    t.checkgraphs()
    # only one path should be left
    for block in f_graph.iterblocks():
        assert len(block.exits) <= 1

    interp = LLInterpreter(t.rtyper)
    result = interp.eval_graph(f_graph, [])
    assert result == 42

def test_remove_unaryops():
    # We really want to use remove_unaryops for things like ooupcast and
    # oodowncast in dynamically typed languages, but it's easier to test
    # it with operations on ints here.
    def f(x):
        i = llop.int_invert(Signed, x)
        i = llop.int_add(Signed, x, 1)
        return llop.int_neg(Signed, i)
    t = TranslationContext()
    t.buildannotator().build_types(f, [int])
    t.buildrtyper().specialize()
    f_graph = graphof(t, f)
    remove_unaryops(f_graph, ["int_neg", "int_invert"])
    t.checkgraphs()

    interp = LLInterpreter(t.rtyper)
    result = interp.eval_graph(f_graph, [-2])
    assert result == -1

