import py
from pypy.translator.translator import TranslationContext, graphof
from pypy.translator.backendopt.propagate import *
from pypy.translator.backendopt.all import backend_optimizations
from pypy.rpython.llinterp import LLInterpreter
from pypy.rpython.memory.test.test_gctransform import getops
from pypy import conftest

def get_graph(fn, signature, inline_threshold=True, all_opts=True):
    t = TranslationContext()
    t.buildannotator().build_types(fn, signature)
    t.buildrtyper().specialize()
    if all_opts:
        backend_optimizations(t, inline_threshold=inline_threshold,
                              ssa_form=False, propagate=False) 
    graph = graphof(t, fn)
    if conftest.option.view:
        t.view()
    return graph, t

def check_graph(graph, args, expected_result, t):
    interp = LLInterpreter(t.rtyper)
    res = interp.eval_graph(graph, args)
    assert res == expected_result

def check_get_graph(fn, signature, args, expected_result):
    graph, t = get_graph(fn, signature)
    check_graph(graph, args, expected_result, t)
    return graph

def test_inline_and():
    def f(x):
        return x != 1 and x != 5 and x != 42
    def g(x):
        ret = 0
        for i in range(x):
            if f(x):
                ret += x
            else:
                ret += x + 1
        return ret
    graph, t = get_graph(g, [int])
    propagate_consts(graph)
    if conftest.option.view:
        t.view()
    assert len(graph.startblock.exits[0].args) == 4
    check_graph(graph, [100], g(100), t)

def test_rewire_links():
    def f(x):
        return x != 1 and x != 5 and x != 42
    def g(x):
        ret = x
        if f(x):
            ret += 1
        else:
            ret += 2
        return ret
    graph, t = get_graph(g, [int])
    rewire_links(graph)
    if conftest.option.view:
        t.view()
    block = graph.startblock
    for i in range(3):
        op = block.exits[False].target.operations[0]
        assert op.opname == "int_add"
        assert op.args[1].value == 2
        block = block.exits[True].target
    assert block.operations[0].opname == "int_add"
    assert block.operations[0].args[1].value == 1
    check_graph(graph, [0], g(0), t)
    check_graph(graph, [1], g(1), t)
    check_graph(graph, [5], g(5), t)
    check_graph(graph, [42], g(42), t)

def test_dont_fold_return():
    def f(x):
        return
    graph, t = get_graph(f, [int])
    propagate_consts(graph)
    assert len(graph.startblock.exits[0].args) == 1
    check_graph(graph, [1], None, t)

def test_propagate_despite_vars():
    patterns = [1, 1, 2, 3, 5, 7, 12]
    class A(object): pass
    global_a = A()
    global_a.x = 10
    global_a.y = 20
    def f(x):
        a = A()
        a.x = 10
        a.y = 20
        result = 0
        i = 0
        for i in range(a.x):
            j = 0
            for i in range(global_a.y):
                result += i * j
                j += 1
        return result
    graph, t = get_graph(f, [int])
    if conftest.option.view:
        t.view()
    while propagate_consts(graph):
        pass
    assert len(graph.startblock.exits[0].args) == 2
    innerloopblock = graph.startblock.exits[0].target.exits[0].target.exits[0].target
    assert len(innerloopblock.inputargs) == 4
    assert len(innerloopblock.exits[0].args) == 4
    check_graph(graph, [0], f(0), t)

def test_constant_fold():
    def f(x):
        return 1
    def g(x):
        return 1 + f(x)
    graph, t = get_graph(g, [int])
    constant_folding(graph, t)
    if conftest.option.view:
        t.view()
    assert len(graph.startblock.operations) == 0
    check_graph(graph, [1], g(1), t)

def test_constant_fold_call():
    def s(x):
        res = 0
        i = 1
        while i <= x:
            res += i
            i += 1
        return res
    def g(x):
        return s(100) + s(1) + x
    graph, t = get_graph(g, [int], inline_threshold=0)
    while constant_folding(graph, t):
        pass
    if conftest.option.view:
        t.view()
    assert len(graph.startblock.operations) == 1
    check_graph(graph, [10], g(10), t)

def test_dont_constant_fold_call():
    class A(object):
        pass
    global_a = A()
    global_a.x = 1
    def g():
        return global_a.x
    def f(x):
        global_a.x = x
        return g()
    graph, t = get_graph(f, [int], inline_threshold=0)
    while constant_folding(graph, t):
        pass
    check_graph(graph, [10], 10, t)

def test_dont_fold_getfield():
    # must not constant fold this, because the container might be collected
    string = "blablabla"
    def f(x):
        return string[abs(x)]
    graph, t = get_graph(f, [int])
    res = constant_folding(graph, t)
    assert not res
    if conftest.option.view:
        t.view()
    print graph.startblock.operations[1]
    check_graph(graph, [0], "b", t)


def test_fold_const_blocks():
    def s(x):
        res = 0
        i = 1
        while i < x:
            res += i
            i += 1
        return res
    def g(x):
        return s(100) + s(99) + x
    graph, t = get_graph(g, [int])
    partial_folding(graph, t)
    constant_folding(graph, t)
    if conftest.option.view:
        t.view()
    assert len(graph.startblock.operations) == 1
    check_graph(graph, [10], g(10), t)

def test_coalesce_links():
    def f(x):
        y = 1
        if x:
            y += 1
        else:
            y += 2
        return 4
    graph, t = get_graph(f, [int])
    simplify.eliminate_empty_blocks(graph)
    coalesce_links(graph)
    if conftest.option.view:
        t.view()
    assert len(graph.startblock.exits) == 1

def getitem(l, i):  #LookupError, KeyError
    if not isinstance(i, int):
        raise TypeError
    if i < 0:
        i = len(l) - i
    if i>= len(l):
        raise IndexError
    return l[i]

def test_dont_coalesce_except():
    def fn(n):
        lst = range(10)
        try:
            getitem(lst,n)
        except:
            pass
        return 4
    graph, t = get_graph(fn, [int])
    coalesce_links(graph)
    if conftest.option.view:
        t.view()
    check_graph(graph, [-1], fn(-1), t)

def list_default_argument(i1, l1=[0]):
    l1.append(i1)
    return len(l1) + l1[-2]

def call_list_default_argument(i1):
    return list_default_argument(i1)
    
def test_call_list_default_argument():
    graph, t = get_graph(call_list_default_argument, [int])
    backend_optimizations(t, propagate=True, ssa_form=False) 
    for i in range(10):
        check_graph(graph, [i], call_list_default_argument(i), t)
    if conftest.option.view:
        t.view()

def test_remove_getfield_after_setfield():
    class A(object):
        def __init__(self, x=42):
            self.x = x
    class B(object):
        pass
    global_b = B()
    global_b.a = None
    def f(x):
        a = A(x)
        global_b.a = a
        global_b.a.x += 1
        return global_b.a.x
    graph, t = get_graph(f, [int], all_opts=False)
    assert len(graph.startblock.operations) == 11
    count = remove_all_getfields(graph, t)
    if conftest.option.view:
        t.view()
    assert len(graph.startblock.operations) == 8
    check_graph(graph, [42], 43, t)

def test_remove_getfield_after_getfield():
    class A(object):
        def __init__(self, x=42):
            self.x = x
    class B(object):
        def __init__(self, a):
            self.a = a
    class C:
        pass
    global_c = C()
    global_c.b1 = None
    global_c.b2 = None
    def f(x):
        a = A(x)
        b = B(a)
        global_c.b1 = b
        a1 = global_c.b1.a
        global_c.b2 = B(a1)
        return global_c.b1.a.x
    graph, t = get_graph(f, [int])
    assert len(graph.startblock.operations) == 23
    count = remove_all_getfields(graph, t)
    assert count
    if conftest.option.view:
        t.view()
    assert len(graph.startblock.operations) == 20
    check_graph(graph, [42], 42, t)
    
def test_getfield_nonmatching_types():
    class A(object):
        pass
    class B(object):
        pass
    global_a = A()
    global_b = B()
    def f(x):
        global_a.x = x
        global_b.x = 2 * x
        return global_a.x + global_b.x
    graph, t = get_graph(f, [int])
    count = remove_all_getfields(graph, t)
    assert count == 2
    if conftest.option.view:
        t.view()
    check_graph(graph, [42], 3 * 42, t)

