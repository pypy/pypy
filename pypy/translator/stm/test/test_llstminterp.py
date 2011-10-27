import py
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.test.test_llinterp import get_interpreter
from pypy.translator.stm.llstminterp import eval_stm_graph
from pypy.translator.stm.llstminterp import ForbiddenInstructionInSTMMode
from pypy.translator.stm.llstminterp import ReturnWithTransactionActive
from pypy.translator.stm import rstm


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
                   eval_stm_graph, interp, graph, [p],
                   stm_mode="regular_transaction")

def test_stm_getfield():
    S = lltype.GcStruct('S', ('x', lltype.Signed))
    p = lltype.malloc(S, immortal=True)
    p.x = 42
    def func(p):
        return rstm.stm_getfield(p, 'x')
    interp, graph = get_interpreter(func, [p])
    # forbidden in "not_in_transaction" mode
    py.test.raises(ForbiddenInstructionInSTMMode,
                   eval_stm_graph, interp, graph, [p])
    # works in "regular_transaction" mode
    res = eval_stm_graph(interp, graph, [p], stm_mode="regular_transaction")
    assert res == 42
    # works in "inevitable_transaction" mode
    res = eval_stm_graph(interp, graph, [p], stm_mode="inevitable_transaction")
    assert res == 42

def test_begin_commit_transaction():
    S = lltype.GcStruct('S', ('x', lltype.Signed))
    p = lltype.malloc(S, immortal=True)
    p.x = 42
    def func(p):
        rstm.begin_transaction()
        res = rstm.stm_getfield(p, 'x')
        rstm.commit_transaction()
        return res
    interp, graph = get_interpreter(func, [p])
    res = eval_stm_graph(interp, graph, [p])
    assert res == 42

def test_call_and_return_with_regular_transaction():
    def g():
        pass
    g._dont_inline_ = True
    def func():
        rstm.begin_transaction()
        g()
        rstm.commit_transaction()
    interp, graph = get_interpreter(func, [])
    eval_stm_graph(interp, graph, [])

def test_cannot_return_with_regular_transaction():
    def g():
        rstm.begin_transaction()
    g._dont_inline_ = True
    def func():
        g()
        rstm.commit_transaction()
    interp, graph = get_interpreter(func, [])
    py.test.raises(ReturnWithTransactionActive,
                   eval_stm_graph, interp, graph, [])
