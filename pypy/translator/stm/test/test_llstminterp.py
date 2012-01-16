import py
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.test.test_llinterp import get_interpreter
from pypy.translator.stm.llstminterp import eval_stm_graph
from pypy.translator.stm.llstminterp import ForbiddenInstructionInSTMMode
from pypy.translator.stm.llstminterp import ReturnWithTransactionActive
from pypy.translator.stm import llstm

ALL_STM_MODES = ["not_in_transaction",
                 "regular_transaction",
                 "inevitable_transaction"]

def test_simple():
    def func(n):
        return (n+1) * (n+2)
    interp, graph = get_interpreter(func, [5])
    res = eval_stm_graph(interp, graph, [5],
                         stm_mode="not_in_transaction",
                         final_stm_mode="not_in_transaction")
    assert res == 42

def test_forbidden():
    S = lltype.GcStruct('S', ('x', lltype.Signed))
    p = lltype.malloc(S, immortal=True)
    p.x = 42
    #
    def funcget(p):
        return p.x
    interp, graph = get_interpreter(funcget, [p])
    py.test.raises(ForbiddenInstructionInSTMMode,
                   eval_stm_graph, interp, graph, [p],
                   stm_mode="regular_transaction")
    #
    def funcset(p):
        p.x = 43
    interp, graph = get_interpreter(funcset, [p])
    py.test.raises(ForbiddenInstructionInSTMMode,
                   eval_stm_graph, interp, graph, [p],
                   stm_mode="regular_transaction")

def test_stm_getfield_stm_setfield():
    S = lltype.GcStruct('S', ('x', lltype.Signed), ('y', lltype.Signed))
    p = lltype.malloc(S, immortal=True)
    p.x = 42
    def func(p):
        llstm.stm_setfield(p, 'y', 43)
        return llstm.stm_getfield(p, 'x')
    interp, graph = get_interpreter(func, [p])
    # works in all modes
    for mode in ALL_STM_MODES:
        p.y = 0
        res = eval_stm_graph(interp, graph, [p], stm_mode=mode)
        assert res == 42
        assert p.y == 43

def test_stm_getarrayitem_stm_setarrayitem():
    A = lltype.GcArray(lltype.Signed)
    p = lltype.malloc(A, 5, immortal=True)
    p[3] = 42
    def func(p):
        llstm.stm_setarrayitem(p, 2, 43)
        return llstm.stm_getarrayitem(p, 3)
    interp, graph = get_interpreter(func, [p])
    # works in all modes
    for mode in ALL_STM_MODES:
        p[2] = 0
        res = eval_stm_graph(interp, graph, [p], stm_mode=mode)
        assert res == 42
        assert p[2] == 43

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

def test_become_inevitable():
    def func():
        llstm.stm_become_inevitable("foobar!")
    interp, graph = get_interpreter(func, [])
    py.test.raises(ForbiddenInstructionInSTMMode,
                   eval_stm_graph, interp, graph, [],
                   stm_mode="not_in_transaction")
    eval_stm_graph(interp, graph, [], stm_mode="regular_transaction",
                   final_stm_mode="inevitable_transaction")
    eval_stm_graph(interp, graph, [], stm_mode="inevitable_transaction")
