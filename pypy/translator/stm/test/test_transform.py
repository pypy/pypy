from pypy.rpython.lltypesystem import lltype, llmemory, rstr
from pypy.rpython.test.test_llinterp import get_interpreter
from pypy.objspace.flow.model import summary
from pypy.translator.stm.llstminterp import eval_stm_graph
from pypy.translator.stm.transform import transform_graph
from pypy.translator.stm import rstm
from pypy.translator.c.test.test_standalone import StandaloneTests
from pypy.rlib.debug import debug_print
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

def test_getinteriorfield():
    p = lltype.malloc(rstr.STR, 100, immortal=True)
    p.chars[42] = 'X'
    def func(p):
        return p.chars[42]
    interp, graph = get_interpreter(func, [p])
    transform_graph(graph)
    assert summary(graph) == {'stm_getinteriorfield': 1}
    res = eval_stm_graph(interp, graph, [p], stm_mode="regular_transaction")
    assert res == 'X'

def test_setinteriorfield():
    p = lltype.malloc(rstr.STR, 100, immortal=True)
    def func(p):
        p.chars[42] = 'Y'
    interp, graph = get_interpreter(func, [p])
    transform_graph(graph)
    assert summary(graph) == {'stm_setinteriorfield': 1}
    res = eval_stm_graph(interp, graph, [p], stm_mode="regular_transaction")

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
    assert summary(graph) == {'stm_try_inevitable': 1, 'getfield': 1}
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
    assert summary(graph) == {'stm_try_inevitable': 1, 'setfield': 1}
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
    assert summary(graph) == {'stm_try_inevitable': 1, 'getarrayitem': 1}
    res = eval_stm_graph(interp, graph, [p], stm_mode="regular_transaction",
                         final_stm_mode="inevitable_transaction")
    assert res == 42

# ____________________________________________________________

class CompiledSTMTests(StandaloneTests):
    gc = "none"

    def compile(self, entry_point):
        from pypy.config.pypyoption import get_pypy_config
        self.config = get_pypy_config(translating=True)
        self.config.translation.stm = True
        self.config.translation.gc = self.gc
        #
        # Prevent the RaiseAnalyzer from just emitting "WARNING: Unknown
        # operation".  We want instead it to crash.
        from pypy.translator.backendopt.canraise import RaiseAnalyzer
        RaiseAnalyzer.fail_on_unknown_operation = True
        try:
            res = StandaloneTests.compile(self, entry_point, debug=True)
        finally:
            del RaiseAnalyzer.fail_on_unknown_operation
        return res


class TestTransformSingleThread(CompiledSTMTests):

    def test_no_pointer_operations(self):
        def simplefunc(argv):
            i = 0
            while i < 100:
                i += 3
            debug_print(i)
            return 0
        t, cbuilder = self.compile(simplefunc)
        dataout, dataerr = cbuilder.cmdexec('', err=True)
        assert dataout == ''
        assert '102' in dataerr.splitlines()

    def test_fails_when_nonbalanced_begin(self):
        def simplefunc(argv):
            rstm.begin_transaction()
            return 0
        t, cbuilder = self.compile(simplefunc)
        cbuilder.cmdexec('', expect_crash=True)

    def test_fails_when_nonbalanced_commit(self):
        def simplefunc(argv):
            rstm.commit_transaction()
            rstm.commit_transaction()
            return 0
        t, cbuilder = self.compile(simplefunc)
        cbuilder.cmdexec('', expect_crash=True)

    def test_begin_inevitable_transaction(self):
        def simplefunc(argv):
            rstm.commit_transaction()
            rstm.begin_inevitable_transaction()
            return 0
        t, cbuilder = self.compile(simplefunc)
        cbuilder.cmdexec('')

    def test_transaction_boundary_1(self):
        def simplefunc(argv):
            rstm.transaction_boundary()
            return 0
        t, cbuilder = self.compile(simplefunc)
        cbuilder.cmdexec('')

    def test_transaction_boundary_2(self):
        def simplefunc(argv):
            rstm.transaction_boundary()
            rstm.transaction_boundary()
            rstm.transaction_boundary()
            return 0
        t, cbuilder = self.compile(simplefunc)
        cbuilder.cmdexec('')

    def test_transaction_boundary_3(self):
        def simplefunc(argv):
            s1 = argv[0]
            debug_print('STEP1:', len(s1))
            rstm.transaction_boundary()
            rstm.transaction_boundary()
            rstm.transaction_boundary()
            debug_print('STEP2:', len(s1))
            return 0
        t, cbuilder = self.compile(simplefunc)
        data, err = cbuilder.cmdexec('', err=True)
        lines = err.splitlines()
        steps = [(line[:6], line[6:])
                 for line in lines if line.startswith('STEP')]
        steps = zip(*steps)
        assert steps[0] == ('STEP1:', 'STEP2:')
        assert steps[1][0] == steps[1][1]
