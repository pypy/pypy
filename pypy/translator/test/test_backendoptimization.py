from pypy.translator.backendoptimization import remove_void
from pypy.translator.translator import Translator
from pypy.rpython.lltype import Void
from pypy.rpython.llinterp import LLInterpreter
from pypy.objspace.flow.model import checkgraph
from pypy.translator.test.snippet import simple_method
from pypy.translator.llvm2.log import log

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

