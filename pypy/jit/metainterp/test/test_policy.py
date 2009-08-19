from pypy.jit.metainterp import policy, support
from pypy.rlib.jit import purefunction, dont_look_inside

def test_all_graphs():
    def f(x):
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
    res = jitpolicy.all_graphs(rtyper.annotator.translator)

    funcs = [graph.func for graph in res]
    assert funcs[:2] == [i, f]
    assert g not in funcs
    assert h not in funcs
