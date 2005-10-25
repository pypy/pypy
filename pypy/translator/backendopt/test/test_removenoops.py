from pypy.translator.backendopt.removenoops import remove_void, remove_same_as
from pypy.translator.backendopt.inline import inline_function
from pypy.translator.translator import Translator
from pypy.translator.test.snippet import simple_method
from pypy.objspace.flow.model import checkgraph, flatten, Block
from pypy.rpython.lltypesystem.lltype import Void
from pypy.rpython.llinterp import LLInterpreter

import py
log = py.log.Producer('test_backendoptimization')


def annotate_and_remove_void(f, annotate):
    t = Translator(f)
    a = t.annotate(annotate)
    t.specialize()
    remove_void(t)
    return t

def test_remove_void_args():
    def f(i):
        return [1,2,3,i][i]
    t = annotate_and_remove_void(f, [int])
    for func, graph in t.flowgraphs.iteritems():
        assert checkgraph(graph) is None
        for arg in graph.startblock.inputargs:
            assert arg.concretetype is not Void
    interp = LLInterpreter(t.flowgraphs, t.rtyper)
    assert interp.eval_function(f, [0]) == 1 

def test_remove_void_in_struct():
    t = annotate_and_remove_void(simple_method, [int])
    #t.view()
    log(t.flowgraphs.iteritems())
    for func, graph in t.flowgraphs.iteritems():
        log('func : ' + str(func))
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
    t = Translator(f)
    a = t.annotate([])
    t.specialize()
    # now we make the 'if True' appear
    inline_function(t, nothing, t.flowgraphs[f])
    # here, the graph looks like  v21=same_as(True);  exitswitch: v21
    remove_same_as(t.flowgraphs[f])
    t.checkgraphs()
    # only one path should be left
    for node in flatten(t.flowgraphs[f]):
        if isinstance(node, Block):
            assert len(node.exits) <= 1

    interp = LLInterpreter(t.flowgraphs, t.rtyper)
    result = interp.eval_function(f, [])
    assert result == 42
