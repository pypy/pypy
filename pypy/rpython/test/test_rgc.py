from pypy.rpython.test.test_llinterp import gengraph, interpret
from pypy.rpython import rgc # Force registration of gc.collect
import gc

def test_collect():
    def f():
        return gc.collect()

    t, typer, graph = gengraph(f, [])
    ops = list(graph.iterblockops())
    assert len(ops) == 1
    op = ops[0][1]
    assert op.opname == 'gc__collect'


    res = interpret(f, [])
    
    assert res is None
    
