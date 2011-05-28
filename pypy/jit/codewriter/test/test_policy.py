import sys
import py
from pypy.jit.codewriter.policy import contains_unsupported_variable_type
from pypy.jit.codewriter.policy import JitPolicy
from pypy.jit.codewriter import support
from pypy.rlib.rarithmetic import r_singlefloat, r_longlong
from pypy.rlib import jit

def test_contains_unsupported_variable_type():
    def f(x):
        return x
    graph = support.getgraph(f, [5])
    for sf in [False, True]:
        for sll in [False, True]:
            assert not contains_unsupported_variable_type(graph, sf, sll)
    #
    graph = support.getgraph(f, [5.5])
    for sf in [False, True]:
        for sll in [False, True]:
            res = contains_unsupported_variable_type(graph, sf, sll)
            assert res is not sf
    #
    graph = support.getgraph(f, [r_singlefloat(5.5)])
    for sf in [False, True]:
        for sll in [False, True]:
            assert contains_unsupported_variable_type(graph, sf, sll)
    #
    graph = support.getgraph(f, [r_longlong(5)])
    for sf in [False, True]:
        for sll in [False, True]:
            res = contains_unsupported_variable_type(graph, sf, sll)
            assert res == (sys.maxint == 2147483647 and not sll)


def test_regular_function():
    graph = support.getgraph(lambda x: x+3, [5])
    assert JitPolicy().look_inside_graph(graph)

def test_without_floats():
    graph = support.getgraph(lambda x: x+3.2, [5.4])
    policy = JitPolicy()
    policy.set_supports_floats(True)
    assert policy.look_inside_graph(graph)
    policy = JitPolicy()
    policy.set_supports_floats(False)
    assert not policy.look_inside_graph(graph)

def test_purefunction():
    @jit.purefunction
    def g(x):
        return x + 2
    graph = support.getgraph(g, [5])
    assert not JitPolicy().look_inside_graph(graph)

def test_dont_look_inside():
    @jit.dont_look_inside
    def h(x):
        return x + 3
    graph = support.getgraph(h, [5])
    assert not JitPolicy().look_inside_graph(graph)

def test_loops():
    def g(x):
        i = 0
        while i < x:
            i += 1
        return i
    graph = support.getgraph(g, [5])
    assert not JitPolicy().look_inside_graph(graph)

def test_unroll_safe():
    @jit.unroll_safe
    def h(x):
        i = 0
        while i < x:
            i += 1
        return i
    graph = support.getgraph(h, [5])
    assert JitPolicy().look_inside_graph(graph)

def test_unroll_safe_and_inline():
    @jit.unroll_safe
    def h(x):
        i = 0
        while i < x:
            i += 1
        return i
    h._always_inline_ = True

    def g(x):
        return h(x)

    graph = support.getgraph(h, [5])
    assert JitPolicy().look_inside_graph(graph)

def test_str_join():
    def f(x, y):
        return "hello".join([str(x), str(y), "bye"])

    graph = support.getgraph(f, [5, 83])
    for block in graph.iterblocks():
        for op in block.operations:
            if op.opname == 'direct_call':
                funcptr = op.args[0].value
                called_graph = funcptr._obj.graph
                if JitPolicy().look_inside_graph(called_graph):
                    # the calls to join() and str() should be residual
                    mod = called_graph.func.__module__
                    assert (mod == 'pypy.rpython.rlist' or
                            mod == 'pypy.rpython.lltypesystem.rlist')

def test_access_directly_but_not_seen():
    class X:
        _virtualizable2_ = ["a"]
    def h(x, y):
        w = 0
        for i in range(y):
            w += 4
        return w
    def f(y):
        x = jit.hint(X(), access_directly=True)
        h(x, y)
    rtyper = support.annotate(f, [3])
    h_graph = rtyper.annotator.translator.graphs[1]
    assert h_graph.func is h
    py.test.raises(ValueError, JitPolicy().look_inside_graph, h_graph)
