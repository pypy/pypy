from pypy.objspace.flow.model import checkgraph, Constant, summary
from pypy.translator.translator import TranslationContext, graphof
from pypy.rpython.llinterp import LLInterpreter
from pypy.rpython.lltypesystem import lltype
from pypy.translator.backendopt.constfold import constant_fold_graph
from pypy import conftest

def get_graph(fn, signature):
    t = TranslationContext()
    t.buildannotator().build_types(fn, signature)
    t.buildrtyper().specialize()
    graph = graphof(t, fn)
    if conftest.option.view:
        t.view()
    return graph, t

def check_graph(graph, args, expected_result, t):
    if conftest.option.view:
        t.view()
    checkgraph(graph)
    interp = LLInterpreter(t.rtyper)
    res = interp.eval_graph(graph, args)
    assert res == expected_result


def test_simple():
    S1 = lltype.GcStruct('S1', ('x', lltype.Signed), hints={'immutable': True})
    s1 = lltype.malloc(S1)
    s1.x = 123
    def g(y):
        return y + 1
    def fn():
        return g(s1.x)

    graph, t = get_graph(fn, [])
    assert summary(graph) == {'getfield': 1, 'direct_call': 1}
    constant_fold_graph(graph)
    assert summary(graph) == {'direct_call': 1}
    check_graph(graph, [], 124, t)


def test_along_link():
    S1 = lltype.GcStruct('S1', ('x', lltype.Signed), hints={'immutable': True})
    s1 = lltype.malloc(S1)
    s1.x = 123
    s2 = lltype.malloc(S1)
    s2.x = 60
    def fn(x):
        if x:
            x = s1.x
        else:
            x = s2.x
        return x+1

    graph, t = get_graph(fn, [int])
    assert summary(graph) == {'int_is_true': 1,
                              'getfield': 2,
                              'int_add': 1}
    constant_fold_graph(graph)
    assert summary(graph) == {'int_is_true': 1}
    check_graph(graph, [-1], 124, t)
    check_graph(graph, [0], 61, t)


def test_multiple_incoming_links():
    S1 = lltype.GcStruct('S1', ('x', lltype.Signed), hints={'immutable': True})
    s1 = lltype.malloc(S1)
    s1.x = 123
    s2 = lltype.malloc(S1)
    s2.x = 60
    s3 = lltype.malloc(S1)
    s3.x = 15
    def fn(x):
        y = x * 10
        if x == 1:
            x = s1.x
        elif x == 2:
            x = s2.x
        elif x == 3:
            x = s3.x
            y = s1.x
        return (x+1) + y

    graph, t = get_graph(fn, [int])
    constant_fold_graph(graph)
    assert summary(graph) == {'int_mul': 1, 'int_eq': 3, 'int_add': 2}
    for link in graph.iterlinks():
        if Constant(139) in link.args:
            break
    else:
        raise AssertionError("139 not found in the graph as a constant")
    for i in range(4):
        check_graph(graph, [i], fn(i), t)


def test_fold_exitswitch():
    S1 = lltype.GcStruct('S1', ('x', lltype.Signed), hints={'immutable': True})
    s1 = lltype.malloc(S1)
    s1.x = 123
    s2 = lltype.malloc(S1)
    s2.x = 60
    def fn(n):
        if s1.x:
            return n * 5
        else:
            return n - 7

    graph, t = get_graph(fn, [int])
    assert summary(graph) == {'getfield': 1,
                              'int_is_true': 1,
                              'int_mul': 1,
                              'int_sub': 1}
    constant_fold_graph(graph)
    assert summary(graph) == {'int_mul': 1}
    check_graph(graph, [12], 60, t)


def test_exception():
    def g():
        return 15
    def fn(n):
        try:
            g()
        except ValueError:
            pass
        return n

    graph, t = get_graph(fn, [int])
    constant_fold_graph(graph)
    check_graph(graph, [12], 12, t)


def xxx_test_later_along_link():
    S1 = lltype.GcStruct('S1', ('x', lltype.Signed), hints={'immutable': True})
    s1 = lltype.malloc(S1)
    s1.x = 123
    s2 = lltype.malloc(S1)
    s2.x = 60
    def fn(x, y):
        if x:
            x = s1.x
        else:
            x = s2.x
        y *= 2
        return (x+1) - y

    graph, t = get_graph(fn, [int, int])
    assert summary(graph) == {'int_is_true': 1,
                              'getfield': 2,
                              'int_mul': 1,
                              'int_add': 1,
                              'int_sub': 1}
    constant_fold_graph(graph)
    assert summary(graph) == {'int_is_true': 1,
                              'int_mul': 1,
                              'int_sub': 1}
    check_graph(graph, [-1], 124, t)
    check_graph(graph, [0], 61, t)
