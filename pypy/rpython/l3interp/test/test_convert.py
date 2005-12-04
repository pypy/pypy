import py
from pypy.rpython.l3interp import convertgraph, l3interp
from pypy.translator.translator import TranslationContext

def test_convert_add():
    def f(x):
        return x + 4
    t = TranslationContext()
    t.buildannotator().build_types(f, [int])
    t.buildrtyper().specialize()
    conv = convertgraph.LL2L3Converter()
    l3graph = conv.convert_graph(t.graphs[0])
    result = l3interp.l3interpret(l3graph, [42], [], [])
    assert isinstance(result, l3interp.L3Integer)
    assert result.intval == 46
