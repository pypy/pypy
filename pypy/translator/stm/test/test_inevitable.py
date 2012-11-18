from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.llinterp import LLFrame
from pypy.rpython.test import test_llinterp
from pypy.rpython.test.test_llinterp import get_interpreter, clear_tcache
from pypy.translator.stm.inevitable import insert_turn_inevitable
from pypy.conftest import option


class LLSTMInevFrame(LLFrame):
    def op_stm_become_inevitable(self, info):
        assert info is not None
        if self.llinterpreter.inevitable_cause is None:
            self.llinterpreter.inevitable_cause = info


class TestTransform:

    def interpret_inevitable(self, fn, args):
        clear_tcache()
        interp, self.graph = get_interpreter(fn, args, view=False)
        interp.frame_class = LLSTMInevFrame
        self.translator = interp.typer.annotator.translator
        insert_turn_inevitable(self.translator, self.graph)
        if option.view:
            self.translator.view()
        #
        interp.inevitable_cause = None
        result = interp.eval_graph(self.graph, args)
        return interp.inevitable_cause


    def test_simple_no_inevitable(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        x1 = lltype.malloc(X, immortal=True)
        x1.foo = 42

        def f1(n):
            x1.foo = n

        res = self.interpret_inevitable(f1, [4])
        assert res is None

    def test_unsupported_op(self):
        X = lltype.Struct('X', ('foo', lltype.Signed))

        def f1():
            addr = llmemory.raw_malloc(llmemory.sizeof(X))
            llmemory.raw_free(addr)

        res = self.interpret_inevitable(f1, [])
        assert res == 'raw_malloc'

    def test_raw_getfield(self):
        X = lltype.Struct('X', ('foo', lltype.Signed))
        x1 = lltype.malloc(X, immortal=True)
        x1.foo = 42

        def f1():
            return x1.foo

        res = self.interpret_inevitable(f1, [])
        assert res == 'getfield'

    def test_raw_getfield_immutable(self):
        X = lltype.Struct('X', ('foo', lltype.Signed),
                          hints={'immutable': True})
        x1 = lltype.malloc(X, immortal=True)
        x1.foo = 42

        def f1():
            return x1.foo

        res = self.interpret_inevitable(f1, [])
        assert res is None

    def test_raw_getfield_with_hint(self):
        X = lltype.Struct('X', ('foo', lltype.Signed),
                          hints={'stm_dont_track_raw_accesses': True})
        x1 = lltype.malloc(X, immortal=True)
        x1.foo = 42

        def f1():
            return x1.foo

        res = self.interpret_inevitable(f1, [])
        assert res is None

    def test_raw_setfield(self):
        X = lltype.Struct('X', ('foo', lltype.Signed))
        x1 = lltype.malloc(X, immortal=True)
        x1.foo = 42

        def f1(n):
            x1.foo = n

        res = self.interpret_inevitable(f1, [43])
        assert res == 'setfield'

    def test_malloc_no_inevitable(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))

        def f1():
            return lltype.malloc(X)

        res = self.interpret_inevitable(f1, [])
        assert res is None

    def test_raw_malloc(self):
        X = lltype.Struct('X', ('foo', lltype.Signed))

        def f1():
            p = lltype.malloc(X, flavor='raw')
            lltype.free(p, flavor='raw')

        res = self.interpret_inevitable(f1, [])
        assert res == 'malloc'
