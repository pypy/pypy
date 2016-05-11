from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rtyper.test.test_llinterp import gengraph
from rpython.conftest import option
from rpython.memory.gctransform.shadowcolor import *
from hypothesis import given, strategies


def make_graph(f, argtypes):
    t, rtyper, graph = gengraph(f, argtypes, viewbefore=False)
    if getattr(option, 'view', False):
        graph.show()
    return graph

def nameof(v):
    return v._name.rstrip('_')

def summary(interesting_vars):
    result = {}
    for v in interesting_vars:
        name = nameof(v)
        result[name] = result.get(name, 0) + 1
    return result

def summary_regalloc(regalloc):
    result = []
    for block in regalloc.graph.iterblocks():
        print block.inputargs
        for op in block.operations:
            print '\t', op
        blockvars = block.inputargs + [op.result for op in block.operations]
        for v in blockvars:
            if regalloc.consider_var(v):
                result.append((nameof(v), regalloc.getcolor(v)))
                print '\t\t%s: %s' % (v, regalloc.getcolor(v))
    result.sort()
    return result


def test_find_predecessors_1():
    def f(a, b):
        c = a + b
        return c
    graph = make_graph(f, [int, int])
    pred = find_predecessors(graph, [(graph.returnblock, graph.getreturnvar())])
    assert summary(pred) == {'c': 1, 'v': 1}

def test_find_predecessors_2():
    def f(a, b):
        c = a + b
        while a > 0:
            a -= 2
        return c
    graph = make_graph(f, [int, int])
    pred = find_predecessors(graph, [(graph.returnblock, graph.getreturnvar())])
    assert summary(pred) == {'c': 3, 'v': 1}

def test_find_predecessors_3():
    def f(a, b):
        while b > 100:
            b -= 2
        if b > 10:
            c = a + b      # 'c' created in this block
        else:
            c = a - b      # 'c' created in this block
        return c           # 'v' is the return var
    graph = make_graph(f, [int, int])
    pred = find_predecessors(graph, [(graph.returnblock, graph.getreturnvar())])
    assert summary(pred) == {'c': 2, 'v': 1}

def test_find_predecessors_4():
    def f(a, b):           # 'a' in the input block
        while b > 100:     # 'a' in the loop header block
            b -= 2         # 'a' in the loop body block
        if b > 10:         # 'a' in the condition block
            while b > 5:   # nothing
                b -= 2     # nothing
            c = a + b      # 'c' created in this block
        else:
            c = a
        return c           # 'v' is the return var
    graph = make_graph(f, [int, int])
    pred = find_predecessors(graph, [(graph.returnblock, graph.getreturnvar())])
    assert summary(pred) == {'a': 4, 'c': 1, 'v': 1}

def test_find_predecessors_trivial_rewrite():
    def f(a, b):                              # 'b' in empty startblock
        while a > 100:                        # 'b'
            a -= 2                            # 'b'
        c = llop.same_as(lltype.Signed, b)    # 'c', 'b'
        while b > 10:                         # 'c'
            b -= 2                            # 'c'
        d = llop.same_as(lltype.Signed, c)    # 'd', 'c'
        return d           # 'v' is the return var
    graph = make_graph(f, [int, int])
    pred = find_predecessors(graph, [(graph.returnblock, graph.getreturnvar())])
    assert summary(pred) == {'b': 4, 'c': 4, 'd': 1, 'v': 1}

def test_find_successors_1():
    def f(a, b):
        return a + b
    graph = make_graph(f, [int, int])
    succ = find_successors(graph, [(graph.startblock, graph.getargs()[0])])
    assert summary(succ) == {'a': 1}

def test_find_successors_2():
    def f(a, b):
        if b > 10:
            return a + b
        else:
            return a - b
    graph = make_graph(f, [int, int])
    succ = find_successors(graph, [(graph.startblock, graph.getargs()[0])])
    assert summary(succ) == {'a': 3}

def test_find_successors_3():
    def f(a, b):
        if b > 10:      # 'a' condition block
            a = a + b   # 'a' input
            while b > 100:
                b -= 2
        while b > 5:    # 'a' in loop header
            b -= 2      # 'a' in loop body
        return a * b    # 'a' in product
    graph = make_graph(f, [int, int])
    succ = find_successors(graph, [(graph.startblock, graph.getargs()[0])])
    assert summary(succ) == {'a': 5}

def test_find_successors_trivial_rewrite():
    def f(a, b):                              # 'b' in empty startblock
        while a > 100:                        # 'b'
            a -= 2                            # 'b'
        c = llop.same_as(lltype.Signed, b)    # 'c', 'b'
        while b > 10:                         # 'c', 'b'
            b -= 2                            # 'c', 'b'
        d = llop.same_as(lltype.Signed, c)    # 'd', 'c'
        return d           # 'v' is the return var
    graph = make_graph(f, [int, int])
    pred = find_successors(graph, [(graph.startblock, graph.getargs()[1])])
    assert summary(pred) == {'b': 6, 'c': 4, 'd': 1, 'v': 1}


def test_interesting_vars_0():
    def f(a, b):
        pass
    graph = make_graph(f, [llmemory.GCREF, int])
    assert not find_interesting_variables(graph)

def test_interesting_vars_1():
    def f(a, b):
        llop.gc_push_roots(lltype.Void, a)
        llop.gc_pop_roots(lltype.Void, a)
    graph = make_graph(f, [llmemory.GCREF, int])
    assert summary(find_interesting_variables(graph)) == {'a': 1}

def test_interesting_vars_2():
    def f(a, b, c):
        llop.gc_push_roots(lltype.Void, a)
        llop.gc_pop_roots(lltype.Void, a)
        while b > 0:
            b -= 5
        llop.gc_push_roots(lltype.Void, c)
        llop.gc_pop_roots(lltype.Void, c)
    graph = make_graph(f, [llmemory.GCREF, int, llmemory.GCREF])
    assert summary(find_interesting_variables(graph)) == {'a': 1, 'c': 1}

def test_interesting_vars_3():
    def f(a, b):
        llop.gc_push_roots(lltype.Void, a)
        llop.gc_pop_roots(lltype.Void, a)
        while b > 0:   # 'a' remains interesting across the blocks of this loop
            b -= 5
        llop.gc_push_roots(lltype.Void, a)
        llop.gc_pop_roots(lltype.Void, a)
    graph = make_graph(f, [llmemory.GCREF, int])
    assert summary(find_interesting_variables(graph)) == {'a': 4}

def test_allocate_registers_1():
    def f(a, b):
        llop.gc_push_roots(lltype.Void, a)
        llop.gc_pop_roots(lltype.Void, a)
        while b > 0:   # 'a' remains interesting across the blocks of this loop
            b -= 5
        llop.gc_push_roots(lltype.Void, a)
        llop.gc_pop_roots(lltype.Void, a)
    graph = make_graph(f, [llmemory.GCREF, int])
    regalloc = allocate_registers(graph)
    assert summary_regalloc(regalloc) == [('a', 0)] * 4

def test_allocate_registers_2():
    def f(a, b, c):
        llop.gc_push_roots(lltype.Void, a)
        llop.gc_pop_roots(lltype.Void, a)
        while b > 0:
            b -= 5
        llop.gc_push_roots(lltype.Void, c)
        llop.gc_pop_roots(lltype.Void, c)
    graph = make_graph(f, [llmemory.GCREF, int, llmemory.GCREF])
    regalloc = allocate_registers(graph)
    assert summary_regalloc(regalloc) == [('a', 0), ('c', 0)]

def test_allocate_registers_3():
    def f(a, b, c):
        llop.gc_push_roots(lltype.Void, c, a)
        llop.gc_pop_roots(lltype.Void, c, a)
        while b > 0:
            b -= 5
        llop.gc_push_roots(lltype.Void, a)
        llop.gc_pop_roots(lltype.Void, a)
    graph = make_graph(f, [llmemory.GCREF, int, llmemory.GCREF])
    regalloc = allocate_registers(graph)
    assert summary_regalloc(regalloc) == [('a', 1)] * 4 + [('c', 0)]

def test_allocate_registers_4():
    def g(a, x):
        return x   # (or something different)
    def f(a, b, c):
        llop.gc_push_roots(lltype.Void, a, c) # 'a', 'c'
        llop.gc_pop_roots(lltype.Void, a, c)
        while b > 0:                          # 'a' only; 'c' not in push_roots
            b -= 5
            llop.gc_push_roots(lltype.Void, a)# 'a'
            d = g(a, c)
            llop.gc_pop_roots(lltype.Void, a)
            c = d
        return c
    graph = make_graph(f, [llmemory.GCREF, int, llmemory.GCREF])
    regalloc = allocate_registers(graph)
    assert summary_regalloc(regalloc) == [('a', 1)] * 3 + [('c', 0)]

def test_allocate_registers_5():
    def g(a, x):
        return x   # (or something different)
    def f(a, b, c):
        while b > 0:                          # 'a', 'c'
            b -= 5
            llop.gc_push_roots(lltype.Void, a, c)  # 'a', 'c'
            g(a, c)
            llop.gc_pop_roots(lltype.Void, a, c)
        while b < 10:
            b += 2
        return c
    graph = make_graph(f, [llmemory.GCREF, int, llmemory.GCREF])
    regalloc = allocate_registers(graph)
    assert summary_regalloc(regalloc) == [('a', 1)] * 2 + [('c', 0)] * 2

@given(strategies.lists(strategies.booleans()))
def test_make_bitmask(boollist):
    index, c = make_bitmask(boollist)
    if index is None:
        assert c is None
    else:
        assert 0 <= index < len(boollist)
        assert boollist[index] == False
        if c == c_NULL:
            bitmask = 1
        else:
            assert c.concretetype == lltype.Signed
            bitmask = c.value
        while bitmask:
            if bitmask & 1:
                assert index >= 0
                assert boollist[index] == False
                boollist[index] = True
            bitmask >>= 1
            index -= 1
    assert boollist == [True] * len(boollist)
