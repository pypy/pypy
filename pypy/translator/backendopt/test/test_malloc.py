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

def check(fn, signature, args, expected_result, must_be_removed=True):
    t = Translator(fn)
    t.annotate(signature)
    t.specialize()
    graph = t.getflowgraph()
    remove_simple_mallocs(graph)
    if must_be_removed:
        check_malloc_removed(graph)
    interp = LLInterpreter(t.flowgraphs, t.rtyper)
    res = interp.eval_function(fn, args)
    assert res == expected_result


def test_fn1():
    def fn1(x, y):
        if x > 0:
            t = x+y, x-y
        else:
            t = x-y, x+y
        s, d = t
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

def test_aliasing():
    class A:
        pass
    def fn6(n):
        a1 = A()
        a1.x = 5
        a2 = A()
        a2.x = 6
        if n > 0:
            a = a1
        else:
            a = a2
        a.x = 12
        return a1.x
    check(fn6, [int], [1], 12, must_be_removed=False)

def test_with_keepalive():
    from pypy.rpython.objectmodel import keepalive
    def fn1(x, y):
        if x > 0:
            t = x+y, x-y
        else:
            t = x-y, x+y
        s, d = t
        keepalive(t)
        return s*d
    check(fn1, [int, int], [15, 10], 125)
