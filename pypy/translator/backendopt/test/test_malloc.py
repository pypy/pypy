from pypy.translator.backendopt.malloc import remove_simple_mallocs
from pypy.translator.backendopt.inline import inline_function
from pypy.translator.translator import Translator
from pypy.objspace.flow.model import checkgraph, flatten, Block
from pypy.rpython.llinterp import LLInterpreter

def check_malloc_removed(graph):
    checkgraph(graph)
    count1 = count2 = 0
    for node in flatten(graph):
        if isinstance(node, Block):
            for op in node.operations:
                if op.opname == 'malloc':
                    count1 += 1
                if op.opname == 'direct_call':
                    count2 += 1
    assert count1 == 0   # number of mallocs left
    assert count2 == 0   # number of direct_calls left

def check(fn, signature, args, expected_result):
    t = Translator(fn)
    t.annotate(signature)
    t.specialize()
    graph = t.getflowgraph()
    remove_simple_mallocs(graph)
    check_malloc_removed(graph)
    interp = LLInterpreter(t.flowgraphs, t.rtyper)
    res = interp.eval_function(fn, args)
    assert res == expected_result


def test_fn1():
    def fn1(x, y):
        s, d = x+y, x-y
        return s*d
    check(fn1, [int, int], [15, 10], 125)

def test_fn2():
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
    check(fn2, [int, int], [-6, 7], -13)

def test_fn3():
    def fn3(x):
        a, ((b, c), d, e) = x+1, ((x+2, x+3), x+4, x+5)
        return a+b+c+d+e
    check(fn3, [int], [10], 65)

def test_fn4():
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
    check(fn4, [int], [42], 42)

def test_fn5():
    class A:
        attr = 666
    class B(A):
        attr = 42
    def fn5():
        b = B()
        return b.attr
    check(fn5, [], [], 42)
