from pypy.translator.translator import TranslationContext, graphof
from pypy.translator.backendopt.all import backend_optimizations
from pypy.objspace.flow.model import traverse, Block

def translate(func, argtypes):
    t = TranslationContext()
    t.buildannotator().build_types(func, argtypes)
    t.buildrtyper().specialize()
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
