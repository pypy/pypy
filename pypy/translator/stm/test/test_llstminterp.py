import py
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.test.test_llinterp import get_interpreter
from pypy.translator.stm.llstminterp import eval_stm_graph
from pypy.translator.stm.llstminterp import ForbiddenInstructionInSTMMode
from pypy.translator.stm.llstminterp import ReturnWithTransactionActive
from pypy.translator.stm import rstm

ALL_STM_MODES = ["not_in_transaction",
                 "regular_transaction",
                 "inevitable_transaction"]

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
                   eval_stm_graph, interp, graph, [p],
                   stm_mode="not_in_transaction")
    # works in "regular_transaction" mode
    res = eval_stm_graph(interp, graph, [p], stm_mode="regular_transaction")
    assert res == 42
    # works in "inevitable_transaction" mode
    res = eval_stm_graph(interp, graph, [p], stm_mode="inevitable_transaction")
    assert res == 42

def test_stm_getarrayitem():
    A = lltype.GcArray(lltype.Signed)
    p = lltype.malloc(A, 5, immortal=True)
    p[3] = 42
    def func(p):
        return rstm.stm_getarrayitem(p, 3)
    interp, graph = get_interpreter(func, [p])
    # forbidden in "not_in_transaction" mode
    py.test.raises(ForbiddenInstructionInSTMMode,
                   eval_stm_graph, interp, graph, [p],
                   stm_mode="not_in_transaction")
    # works in "regular_transaction" mode
    res = eval_stm_graph(interp, graph, [p], stm_mode="regular_transaction")
    assert res == 42
    # works in "inevitable_transaction" mode
    res = eval_stm_graph(interp, graph, [p], stm_mode="inevitable_transaction")
    assert res == 42

def test_getfield_immutable():
    S = lltype.GcStruct('S', ('x', lltype.Signed), hints = {'immutable': True})
    p = lltype.malloc(S, immortal=True)
    p.x = 42
    def func(p):
        return p.x
    interp, graph = get_interpreter(func, [p])
    # a plain 'getfield' of an immutable field works in all modes
    for mode in ALL_STM_MODES:
        res = eval_stm_graph(interp, graph, [p], stm_mode=mode)
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

def test_cannot_raise_with_regular_transaction():
    def g():
        rstm.begin_transaction()
        raise ValueError
    g._dont_inline_ = True
    def func():
        try:
            g()
        except ValueError:
            pass
        rstm.commit_transaction()
    interp, graph = get_interpreter(func, [])
    py.test.raises(ReturnWithTransactionActive,
                   eval_stm_graph, interp, graph, [])

def test_transaction_boundary():
    def func(n):
        if n > 5:
            rstm.transaction_boundary()
    interp, graph = get_interpreter(func, [2])
    eval_stm_graph(interp, graph, [10],
                   stm_mode="regular_transaction",
                   final_stm_mode="inevitable_transaction",
                   automatic_promotion=True)
    eval_stm_graph(interp, graph, [1],
                   stm_mode="regular_transaction",
                   final_stm_mode="regular_transaction",
                   automatic_promotion=True)
