from pypy.rpython.lltypesystem import lltype
from pypy.rpython.test.test_llinterp import get_interpreter
from pypy.translator.stm.llstminterp import eval_stm_graph
from pypy.translator.stm.transform import transform_graph


def test_simple():
    S = lltype.GcStruct('S', ('x', lltype.Signed))
    p = lltype.malloc(S, immortal=True)
    p.x = 42
    def func(p):
        return p.x
    interp, graph = get_interpreter(func, [p])
    transform_graph(graph)
    res = eval_stm_graph(interp, graph, [p], stm_mode="regular_transaction")
    assert res == 42
