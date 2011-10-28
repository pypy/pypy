from pypy.rpython.lltypesystem import lltype
from pypy.rpython.test.test_llinterp import get_interpreter
from pypy.objspace.flow.model import summary
from pypy.translator.stm.llstminterp import eval_stm_graph
from pypy.translator.stm.transform import transform_graph
from pypy.translator.stm import rstm
from pypy.translator.c.test.test_standalone import StandaloneTests
from pypy.rlib.debug import debug_print


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


class TestTransformSingleThread(StandaloneTests):

    def compile(self, entry_point):
        from pypy.config.pypyoption import get_pypy_config
        self.config = get_pypy_config(translating=True)
        self.config.translation.stm = True
        return StandaloneTests.compile(self, entry_point, debug=True)

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
