from pypy.translator.backendoptimization import remove_void, inline_function
from pypy.translator.backendoptimization import remove_simple_mallocs
from pypy.translator.translator import Translator
from pypy.rpython.lltype import Void
from pypy.rpython.llinterp import LLInterpreter
from pypy.objspace.flow.model import checkgraph, flatten, Block
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

def test_inline_several_times():
    def f(x):
        return (x + 1) * 2
    def g(x):
        if x:
            a = f(x) + f(x)
        else:
            a = f(x) + 1
        return a + f(x)
    t = Translator(g)
    a = t.annotate([int])
    a.simplify()
    t.specialize()
    inline_function(t, f, t.flowgraphs[g])
    interp = LLInterpreter(t.flowgraphs, t.rtyper)
    result = interp.eval_function(g, [0])
    assert result == g(0)
    result = interp.eval_function(g, [42])
    assert result == g(42)

def test_inline_exceptions():
    def f(x):
        if x == 0:
            raise ValueError
        if x == 1:
            raise KeyError
    def g(x):
        try:
            f(x)
        except ValueError:
            return 2
        except KeyError:
            return 3
        return 1
    t = Translator(g)
    a = t.annotate([int])
    a.simplify()
    t.specialize()
    inline_function(t, f, t.flowgraphs[g])
    interp = LLInterpreter(t.flowgraphs, t.rtyper)
    result = interp.eval_function(g, [0])
    assert result == 2
    result = interp.eval_function(g, [1])
    assert result == 3
    result = interp.eval_function(g, [42])
    assert result == 1

def DONOTtest_inline_var_exception():
    # this test is disabled for now, because f() contains a direct_call
    # (at the end, to a ll helper, to get the type of the exception object)
    def f(x):
        e = None
        if x == 0:
            e = ValueError()
        elif x == 1:
            e = KeyError()
        if x == 0 or x == 1:
            raise e
    def g(x):
        try:
            f(x)
        except ValueError:
            return 2
        except KeyError:
            return 3
        return 1
    t = Translator(g)
    a = t.annotate([int])
    a.simplify()
    t.specialize()
    inline_function(t, f, t.flowgraphs[g])
    interp = LLInterpreter(t.flowgraphs, t.rtyper)
    result = interp.eval_function(g, [0])
    assert result == 2
    result = interp.eval_function(g, [1])
    assert result == 3
    result = interp.eval_function(g, [42])
    assert result == 1

def DONOTtest_call_call():
    # for reference.  Just remove this test if we decide not to support
    # catching exceptions while inlining a graph that contains further
    # direct_calls.
    def e(x):
        if x < 0:
            raise KeyError
        return x+1
    def f(x):
        return e(x)+2
    def g(x):
        try:
            return f(x)+3
        except KeyError:
            return -1
    t = Translator(g)
    a = t.annotate([int])
    a.simplify()
    t.specialize()
    inline_function(t, f, t.flowgraphs[g])
    interp = LLInterpreter(t.flowgraphs, t.rtyper)
    result = interp.eval_function(g, [100])
    assert result == 106
    result = interp.eval_function(g, [-100])
    assert result == -1

def FAILING_test_for_loop():
    def f(x):
        result = 0
        for i in range(0, x):
            result += i
        return result
    t = Translator(f)
    a = t.annotate([int])
    a.simplify()
    t.specialize()
    for graph in t.flowgraphs.values():
        if graph.name.startswith('ll_rangenext'):
            break
    inline_function(t, graph, t.flowgraphs[f])
    t.view()
    interp = LLInterpreter(t.flowgraphs, t.rtyper)
    result = interp.eval_function(g, [10])
    assert result == 45


def check_malloc_removed(fn, signature, expected_remaining_mallocs):
    t = Translator(fn)
    t.annotate(signature)
    t.specialize()
    graph = t.getflowgraph()
    remove_simple_mallocs(graph)
    checkgraph(graph)
    count = 0
    for node in flatten(graph):
        if isinstance(node, Block):
            for op in node.operations:
                if op.opname == 'malloc':
                    count += 1
    assert count == expected_remaining_mallocs

def test_remove_mallocs():
    def fn1(x, y):
        s, d = x+y, x-y
        return s*d
    yield check_malloc_removed, fn1, [int, int], 0
    #
    class T:
        pass
    def fn2(x, y):
        t = T()
        t.x = x
        t.y = y
        if x > 0:
            return t.x + t.y
        else:
            return t.x - t.y
    yield check_malloc_removed, fn2, [int, int], 0
    #
    def fn3(x):
        a, ((b, c), d, e) = x+1, ((x+2, x+3), x+4, x+5)
        return a+b+c+d+e
    yield check_malloc_removed, fn3, [int], 0
    #
    class A:
        pass
    class B(A):
        pass
    def fn4(i):
        a = A()
        b = B()
        a.b = b
        b.i = i
        return a.b.i
    yield check_malloc_removed, fn4, [int], 0
