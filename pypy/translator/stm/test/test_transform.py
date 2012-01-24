from pypy.rpython.lltypesystem import lltype, llmemory, rstr
from pypy.rpython.test.test_llinterp import get_interpreter
from pypy.objspace.flow.model import summary
from pypy.translator.stm.llstminterp import eval_stm_graph
from pypy.translator.stm.transform import transform_graph
from pypy.conftest import option


def eval_stm_func(func, arguments, stm_mode="regular_transaction",
                  final_stm_mode="regular_transaction"):
    interp, graph = get_interpreter(func, arguments)
    transform_graph(graph)
    #if option.view:
    #    graph.show()
    return eval_stm_graph(interp, graph, arguments, stm_mode=stm_mode,
                          final_stm_mode=final_stm_mode,
                          automatic_promotion=True)

# ____________________________________________________________

def test_simple():
    S = lltype.GcStruct('S', ('x', lltype.Signed))
    p = lltype.malloc(S, immortal=True)
    p.x = 42
    def func(p):
        return p.x
    interp, graph = get_interpreter(func, [p])
    transform_graph(graph)
    assert summary(graph) == {'stm_getfield': 1}
    res = eval_stm_graph(interp, graph, [p], stm_mode="regular_transaction")
    assert res == 42

def test_setfield():
    S = lltype.GcStruct('S', ('x', lltype.Signed))
    p = lltype.malloc(S, immortal=True)
    p.x = 42
    def func(p):
        p.x = 43
    interp, graph = get_interpreter(func, [p])
    transform_graph(graph)
    assert summary(graph) == {'stm_setfield': 1}
    eval_stm_graph(interp, graph, [p], stm_mode="regular_transaction")

def test_immutable_field():
    S = lltype.GcStruct('S', ('x', lltype.Signed), hints = {'immutable': True})
    p = lltype.malloc(S, immortal=True)
    p.x = 42
    def func(p):
        return p.x
    interp, graph = get_interpreter(func, [p])
    transform_graph(graph)
    assert summary(graph) == {'getfield': 1}
    res = eval_stm_graph(interp, graph, [p], stm_mode="regular_transaction")
    assert res == 42

def test_void_field():
    S = lltype.GcStruct('S', ('v', lltype.Void))
    p = lltype.malloc(S, immortal=True)
    def func(p):
        p.v = None
        return p.v
    interp, graph = get_interpreter(func, [p])
    transform_graph(graph)
    assert summary(graph) == {'getfield': 1, 'setfield': 1}

def test_getarraysize():
    A = lltype.GcArray(lltype.Signed)
    p = lltype.malloc(A, 100, immortal=True)
    p[42] = 666
    def func(p):
        return len(p)
    interp, graph = get_interpreter(func, [p])
    transform_graph(graph)
    assert summary(graph) == {'getarraysize': 1}
    res = eval_stm_graph(interp, graph, [p], stm_mode="regular_transaction")
    assert res == 100

def test_getarrayitem():
    A = lltype.GcArray(lltype.Signed)
    p = lltype.malloc(A, 100, immortal=True)
    p[42] = 666
    def func(p):
        return p[42]
    interp, graph = get_interpreter(func, [p])
    transform_graph(graph)
    assert summary(graph) == {'stm_getarrayitem': 1}
    res = eval_stm_graph(interp, graph, [p], stm_mode="regular_transaction")
    assert res == 666

def test_setarrayitem():
    A = lltype.GcArray(lltype.Signed)
    p = lltype.malloc(A, 100, immortal=True)
    p[42] = 666
    def func(p):
        p[42] = 676
    interp, graph = get_interpreter(func, [p])
    transform_graph(graph)
    assert summary(graph) == {'stm_setarrayitem': 1}
    eval_stm_graph(interp, graph, [p], stm_mode="regular_transaction")

STRLIKE = lltype.GcStruct('STRLIKE',    # no 'immutable' in this version
                          ('chars', lltype.Array(lltype.Char)))

def test_getinteriorfield():
    p = lltype.malloc(STRLIKE, 100, immortal=True)
    p.chars[42] = 'X'
    def func(p):
        return p.chars[42]
    interp, graph = get_interpreter(func, [p])
    transform_graph(graph)
    assert summary(graph) == {'stm_getinteriorfield': 1}
    res = eval_stm_graph(interp, graph, [p], stm_mode="regular_transaction")
    assert res == 'X'

def test_setinteriorfield():
    p = lltype.malloc(STRLIKE, 100, immortal=True)
    def func(p):
        p.chars[42] = 'Y'
    interp, graph = get_interpreter(func, [p])
    transform_graph(graph)
    assert summary(graph) == {'stm_setinteriorfield': 1}
    res = eval_stm_graph(interp, graph, [p], stm_mode="regular_transaction")

def test_getstrchar():
    p = lltype.malloc(rstr.STR, 100, immortal=True)
    p.chars[42] = 'X'
    def func(p):
        return p.chars[42]
    interp, graph = get_interpreter(func, [p])
    transform_graph(graph)
    assert summary(graph) == {'getinteriorfield': 1}
    res = eval_stm_graph(interp, graph, [p], stm_mode="regular_transaction")
    assert res == 'X'

def test_setstrchar():
    p = lltype.malloc(rstr.STR, 100, immortal=True)
    def func(p):
        p.chars[42] = 'Y'
    interp, graph = get_interpreter(func, [p])
    transform_graph(graph)
    assert summary(graph) == {'setinteriorfield': 1}
    res = eval_stm_graph(interp, graph, [p], stm_mode="regular_transaction")

def test_getfield_setfield_access_directly():
    class P:
        x = 42
        _stm_access_directly_ = True
    def func():
        p = P()
        p.x += 1
    interp, graph = get_interpreter(func, [])
    transform_graph(graph)
    assert summary(graph) == {'malloc': 1, 'cast_pointer': 1,
                              'getfield': 1, 'setfield': 3, 'int_add': 1}
    res = eval_stm_graph(interp, graph, [], stm_mode="regular_transaction")

def test_arrayitem_access_directly():
    class P1:
        pass
    class P2:
        _stm_access_directly_ = True
    class P3:
        _stm_access_directly_ = True
        _immutable_fields_ = ['lst->...']
    for P in [P1, P2, P2]:
        def func(n):
            p = P()
            p.lst = [0]
            p.lst[0] = n
            return p.lst[0]
        interp, graph = get_interpreter(func, [42])
        #
        from pypy.translator.backendopt.inline import auto_inline_graphs
        translator = interp.typer.annotator.translator
        auto_inline_graphs(translator, translator.graphs, 16.0)
        if option.view:
            graph.show()
        #
        transform_graph(graph)
        assert ('stm_getfield' in summary(graph)) == (P is P1)
        assert ('stm_setfield' in summary(graph)) == (P is P1)
        assert ('stm_getarrayitem' in summary(graph)) == (P is not P3)
        #assert ('stm_setarrayitem' in summary(graph)) == (P is not P3) -- xxx
        res = eval_stm_graph(interp, graph, [42],
                             stm_mode="regular_transaction")
        assert res == 42

def test_unsupported_operation():
    def func(n):
        n += 1
        if n > 5:
            p = llmemory.raw_malloc(llmemory.sizeof(lltype.Signed))
            llmemory.raw_free(p)
        return n
    res = eval_stm_func(func, [3], final_stm_mode="regular_transaction")
    assert res == 4
    res = eval_stm_func(func, [13], final_stm_mode="inevitable_transaction")
    assert res == 14

def test_supported_malloc():
    S = lltype.GcStruct('S', ('x', lltype.Signed))   # GC structure
    def func():
        lltype.malloc(S)
    eval_stm_func(func, [], final_stm_mode="regular_transaction")

def test_supported_malloc_varsize():
    A = lltype.GcArray(lltype.Signed)
    def func():
        lltype.malloc(A, 5)
    eval_stm_func(func, [], final_stm_mode="regular_transaction")

def test_unsupported_malloc():
    S = lltype.Struct('S', ('x', lltype.Signed))   # non-GC structure
    def func():
        lltype.malloc(S, flavor='raw')
    eval_stm_func(func, [], final_stm_mode="inevitable_transaction")
test_unsupported_malloc.dont_track_allocations = True

def test_unsupported_getfield_raw():
    S = lltype.Struct('S', ('x', lltype.Signed))
    p = lltype.malloc(S, immortal=True)
    p.x = 42
    def func(p):
        return p.x
    interp, graph = get_interpreter(func, [p])
    transform_graph(graph)
    assert summary(graph) == {'stm_become_inevitable': 1, 'getfield': 1}
    res = eval_stm_graph(interp, graph, [p], stm_mode="regular_transaction",
                         final_stm_mode="inevitable_transaction")
    assert res == 42

def test_unsupported_setfield_raw():
    S = lltype.Struct('S', ('x', lltype.Signed))
    p = lltype.malloc(S, immortal=True)
    p.x = 42
    def func(p):
        p.x = 43
    interp, graph = get_interpreter(func, [p])
    transform_graph(graph)
    assert summary(graph) == {'stm_become_inevitable': 1, 'setfield': 1}
    eval_stm_graph(interp, graph, [p], stm_mode="regular_transaction",
                   final_stm_mode="inevitable_transaction")

def test_unsupported_getarrayitem_raw():
    A = lltype.Array(lltype.Signed)
    p = lltype.malloc(A, 5, immortal=True)
    p[3] = 42
    def func(p):
        return p[3]
    interp, graph = get_interpreter(func, [p])
    transform_graph(graph)
    assert summary(graph) == {'stm_become_inevitable': 1, 'getarrayitem': 1}
    res = eval_stm_graph(interp, graph, [p], stm_mode="regular_transaction",
                         final_stm_mode="inevitable_transaction")
    assert res == 42
