from pypy.rpython.l3interp import convertgraph, l3interp
from pypy.translator.translator import Translator

def test_convert_add():
    def f(x):
        return x + 4
    t = Translator(f)
    t.annotate([int])
    t.specialize()
    globals = convertgraph.convert(t)
    interp = l3interp.LLInterpreter(globals)
    graph = globals.graphs[0]
    result = interp.eval_graph_int(graph, [0])
    assert result == 4
