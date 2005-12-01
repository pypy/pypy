from pypy.rpython.l3interp import convertgraph, l3interp
from pypy.translator.translator import TranslationContext

def test_convert_add():
    def f(x):
        return x + 4
    t = TranslationContext()
    t.buildannotator().build_types(f, [int])
    t.buildrtyper().specialize()
    globals = convertgraph.convert(t.graphs[0])
    interp = l3interp.LLInterpreter(globals)
    graph = globals.graphs[0]
    result = interp.eval_graph_int(graph, [0])
    assert result == 4
