import py
from pypy.rpython.l3interp import convertgraph, l3interp
from pypy.translator.translator import TranslationContext

def l3ify(f, inputargs):
    t = TranslationContext()
    t.buildannotator().build_types(f, inputargs)
    t.buildrtyper().specialize()
    conv = convertgraph.LL2L3Converter()
    return conv.convert_graph(t.graphs[0])


def test_convert_add():
    def f(x):
        return x + 4
    l3graph = l3ify(f, [int])
    result = l3interp.l3interpret(l3graph, [42], [], [])
    assert isinstance(result, l3interp.L3Integer)
    assert result.intval == 46

def test_convert_simple():
    def f():
        return 3 + 4
    l3graph = l3ify(f, [])
    result = l3interp.l3interpret(l3graph, [], [], [])
    assert isinstance(result, l3interp.L3Integer)
    assert result.intval == 7

def test_convert_branch():
    def f(x):
        if x:
            return x
        return 1
    l3graph = l3ify(f, [int])
    result = l3interp.l3interpret(l3graph, [2], [], [])
    assert isinstance(result, l3interp.L3Integer)
    assert result.intval == 2

    result = l3interp.l3interpret(l3graph, [0], [], [])
    assert isinstance(result, l3interp.L3Integer)
    assert result.intval == 1
    
def dont_test_convert_getfield():
    class C:
        def __init__(self, x):
            self.x = x
    one = C(1)
    two = C(2)

    def f(n):
        if n:
            return one.x
        else:
            return two.x
    l3graph = l3ify(f, [int])
    result = l3interp.l3interpret(l3graph, [3], [], [])
    assert isinstance(result, l3interp.L3Integer)
    assert result.intval == 1

    result = l3interp.l3interpret(l3graph, [0], [], [])
    assert isinstance(result, l3interp.L3Integer)
    assert result.intval == 2

