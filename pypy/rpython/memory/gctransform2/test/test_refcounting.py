from pypy.rpython.memory.gctransform2.test.test_transform import rtype
from pypy.rpython.memory.gctransform2.refcounting import RefcountingGCTransformer
from pypy.translator.c.database import LowLevelDatabase
from pypy.translator.c.gc import RefcountingGcPolicy
from pypy import conftest

class RefcountingGcPolicy2(RefcountingGcPolicy):
    transformerclass = RefcountingGCTransformer

def llinterpreter_for_refcounted_graph(f, args_s):
    from pypy.rpython.llinterp import LLInterpreter
    from pypy.translator.c.genc import CStandaloneBuilder
    from pypy.translator.c import gc

    t = rtype(f, args_s)
    cbuild = CStandaloneBuilder(t, f, RefcountingGcPolicy2)
    db = cbuild.generate_graphs_for_llinterp()
    graph = cbuild.getentrypointptr()._obj.graph
    llinterp = LLInterpreter(t.rtyper)
    if conftest.option.view:
        t.view()
    return llinterp, graph
    res = llinterp.eval_graph(graph, [0])
    assert res == f(0)
    res = llinterp.eval_graph(graph, [1])
    assert res == f(1)


def test_llinterp_refcounted_graph():
    from pypy.annotation.model import SomeInteger

    class C:
        pass
    c = C()
    c.x = 1
    def g(x):
        if x:
            return c
        else:
            d = C()
            d.x = 2
            return d
    def f(x):
        return g(x).x

    llinterp, graph = llinterpreter_for_refcounted_graph(f, [SomeInteger()])

    res = llinterp.eval_graph(graph, [0])
    assert res == f(0)
    res = llinterp.eval_graph(graph, [1])
    assert res == f(1)

def test_llinterp_refcounted_graph_varsize():
    from pypy.annotation.model import SomeInteger

    def f(x):
        r = []
        for i in range(x):
            if i % 2:
                r.append(x)
        return len(r)


    llinterp, graph = llinterpreter_for_refcounted_graph(f, [SomeInteger()])

    res = llinterp.eval_graph(graph, [0])
    assert res == f(0)
    res = llinterp.eval_graph(graph, [10])
    assert res == f(10)

def test_llinterp_refcounted_graph_str():
    from pypy.annotation.model import SomeString
    from pypy.rpython.lltypesystem.rstr import string_repr

    def f(x):
        return len(x + 'a')


    llinterp, graph = llinterpreter_for_refcounted_graph(f, [SomeString()])

    cc = string_repr.convert_const

    res = llinterp.eval_graph(graph, [cc('a')])
    assert res == f('a')
    res = llinterp.eval_graph(graph, [cc('brrrrrr')])
    assert res == f('brrrrrr')

def test_llinterp_refcounted_graph_with_del():
    from pypy.annotation.model import SomeInteger

    class D:
        pass

    delcounter = D()
    delcounter.dels = 0

    class C:
        def __del__(self):
            delcounter.dels += 1
    c = C()
    c.x = 1
    def h(x):
        if x:
            return c
        else:
            d = C()
            d.x = 2
            return d
    def g(x):
        return h(x).x
    def f(x):
        r = g(x)
        return r + delcounter.dels

    llinterp, graph = llinterpreter_for_refcounted_graph(f, [SomeInteger()])

    res = llinterp.eval_graph(graph, [1])
    assert res == 1
    res = llinterp.eval_graph(graph, [0])
    assert res == 3

