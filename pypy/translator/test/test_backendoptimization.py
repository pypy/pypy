from pypy.translator.backendoptimization import remove_void, inline_function
from pypy.translator.translator import Translator
from pypy.rpython.lltype import Void
from pypy.rpython.llinterp import LLInterpreter
from pypy.objspace.flow.model import checkgraph
from pypy.translator.test.snippet import simple_method, is_perfect_number
from pypy.translator.llvm.log import log

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

def test_inline_simple():
    def f(x, y):
        return (g(x, y) + 1) * x
    def g(x, y):
        if x > 0:
            return x * y
        else:
            return -x * y
    t = Translator(f)
    a = t.annotate([int, int])
    a.simplify()
    t.specialize()
    inline_function(t, g, t.flowgraphs[f])
    interp = LLInterpreter(t.flowgraphs, t.rtyper)
    result = interp.eval_function(f, [-1, 5])
    assert result == f(-1, 5)
    result = interp.eval_function(f, [2, 12])
    assert result == f(2, 12)

def test_inline_big():
    def f(x):
        result = []
        for i in range(1, x+1):
            if is_perfect_number(i):
                result.append(i)
        return result
    t = Translator(f)
    a = t.annotate([int])
    a.simplify()
    t.specialize()
    inline_function(t, is_perfect_number, t.flowgraphs[f])
    interp = LLInterpreter(t.flowgraphs, t.rtyper)
    result = interp.eval_function(f, [10])
    assert result.length == len(f(10))

def test_inline_raising():
    def f(x):
        if x == 1:
            raise ValueError
        return x
    def g(x):
        a = f(x)
        if x == 2:
            raise KeyError
    def h(x):
        try:
            g(x)
        except ValueError:
            return 1
        except KeyError:
            return 2
        return x
    t = Translator(h)
    a = t.annotate([int])
    a.simplify()
    t.specialize()
    inline_function(t, f, t.flowgraphs[g])
    interp = LLInterpreter(t.flowgraphs, t.rtyper)
    result = interp.eval_function(h, [0])
    assert result == 0
    result = interp.eval_function(h, [1])
    assert result == 1
    result = interp.eval_function(h, [2])
    assert result == 2    

def DONOTtest_inline_exceptions():
    def f(x):
        if x:
            raise ValueError
    def g(x):
        try:
            f(x)
        except ValueError:
            return 1
        return 1
    t = Translator(g)
    a = t.annotate([int])
    a.simplify()
    t.specialize()
    t.view()
    inline_function(t, f, t.flowgraphs[g])
    t.view()
    
