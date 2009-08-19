from pypy.jit.metainterp import policy, support, warmspot
from pypy.rlib.jit import purefunction, dont_look_inside

def test_find_all_graphs():
    def f(x):
        if x < 0:
            return f(-x)
        return x + 1
    @purefunction
    def g(x):
        return x + 2
    @dont_look_inside
    def h(x):
        return x + 3
    def i(x):
        return f(x) * g(x) * h(x)

    rtyper = support.annotate(i, [7])

    jitpolicy = policy.JitPolicy()
    translator = rtyper.annotator.translator
    res = warmspot.find_all_graphs(translator.graphs[0], jitpolicy, translator)

    funcs = [graph.func for graph in res]
    assert funcs == [i, f]

def test_find_all_graphs_str_join():
    def i(x, y):
        return "hello".join([str(x), str(y), "bye"])

    rtyper = support.annotate(i, [7, 100])

    jitpolicy = policy.JitPolicy()
    translator = rtyper.annotator.translator
    res = warmspot.find_all_graphs(translator.graphs[0], jitpolicy, translator)

    funcs = [graph.func for graph in res]
    assert funcs[:1] == [i]
