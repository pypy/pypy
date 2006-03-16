from pypy.translator.translator import TranslationContext, graphof
from pypy.translator.backendopt.all import backend_optimizations
from pypy.translator.simplify import get_graph
from pypy.objspace.flow.model import traverse, Block

def translate(func, argtypes, backend_optimize=True):
    t = TranslationContext()
    t.buildannotator().build_types(func, argtypes)
    t.buildrtyper().specialize()
    if backend_optimize:
        backend_optimizations(t)
    return graphof(t, func), t

def test_remove_direct_call_without_side_effects():
    def f(x):
        return x + 123
    def g(x):
        a = f(x)
        return x * 12
    graph, _ = translate(g, [int])
    assert len(graph.startblock.operations) == 1

def test_dont_remove_external_calls():
    import os
    def f(x):
        os.close(x)
    graph, _ = translate(f, [int])
    assert len(graph.startblock.operations) == 1

def test_remove_recursive_call():
    def rec(a):
        if a <= 1:
            return 0
        else:
            return rec(a - 1) + 1
    def f(x):
        a = rec(x)
        return x + 12
    graph, _ = translate(f, [int])
    assert len(graph.startblock.operations)

def test_dont_remove_if_exception_guarded():
    def f(x):
        a = {} #do some stuff to prevent inlining
        a['123'] = 123
        a['1123'] = 1234
        return x + 1
    def g(x):
        try:
            a = f(x)
        except OverflowError:
            raise
        else:
            return 1
    graph, _ = translate(g, [int])
    assert graph.startblock.operations[-1].opname == 'direct_call'


def test_remove_pointless_keepalive():
    from pypy.rpython import objectmodel
    class C:
        y = None
        z1 = None
        z2 = None

    def g():
        return C()

    def f(i):
        c = g()
        c.y
        if i:
            n = c.z1
        else:
            n = c.z2
        objectmodel.keepalive_until_here(c, n)

    graph, t = translate(f, [bool])

    #t.view()

    for block in graph.iterblocks():
        for op in block.operations:
            assert op.opname != 'getfield'
            if op.opname == 'keepalive':
                assert op.args[0] in graph.getargs()


def test_remove_identical_variables():
    def g(code):
        pc = 0
        while pc < len(code):
            pc += 1
        return pc

    graph = TranslationContext().buildflowgraph(g)
    for block in graph.iterblocks():
        assert len(block.inputargs) <= 2   # at most 'pc' and 'code'

def test_get_graph():
    import os
    def list_basic_ops(i, j):
        l = [1,2,3]
        l.insert(0, 42)
        del l[1]
        l.append(i)
        listlen = len(l)
        l.extend(l)
        del l[listlen:]
        l += [5,6]
        l[1] = i
        return l[j]
    def external_function():
        return os.system("ls")
    graph, t = translate(list_basic_ops, [int, int], False) 
    for block in graph.iterblocks():
        for op in block.operations:
            if op.opname == "direct_call":
                print op
                graph = get_graph(op.args[0], t)
                assert graph is not None
    graph, t = translate(external_function, [], False) 
    for block in graph.iterblocks():
        for op in block.operations:
            if op.opname == "direct_call":
                print op
                graph = get_graph(op.args[0], t)
                assert graph is None

def addone(x):
    return x + 1

def test_huge_func():
    g = None
    gstring = "def g(x):\n%s%s" % ("    x = x + 1\n" * 1000, "    return x\n")
    exec gstring 
    assert g(1) == 1001
    # does not crash: previously join_blocks would barf on this
    graph, t = translate(g, [int])
