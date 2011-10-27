import py
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.test.test_llinterp import get_interpreter
from pypy.translator.stm.llstminterp import eval_stm_graph
from pypy.translator.stm.llstminterp import ForbiddenInstructionInSTMMode


def test_simple():
    def func(n):
        return (n+1) * (n+2)
    interp, graph = get_interpreter(func, [5])
    res = eval_stm_graph(interp, graph, [5])
    assert res == 42

def test_forbidden():
    S = lltype.GcStruct('S', ('x', lltype.Signed))
    p = lltype.malloc(S, immortal=True)
    p.x = 42
    def func(p):
        return p.x
    interp, graph = get_interpreter(func, [p])
    py.test.raises(ForbiddenInstructionInSTMMode,
                   eval_stm_graph, interp, graph, [p])
