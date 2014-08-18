from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rtyper.llinterp import LLFrame
from rpython.rtyper.test import test_llinterp
from rpython.rtyper.test.test_llinterp import get_interpreter, clear_tcache
from rpython.translator.stm.inevitable import insert_turn_inevitable
from rpython.conftest import option


class LLSTMInevFrame(LLFrame):
    def op_stm_become_inevitable(self, info):
        assert info is not None
        if self.llinterpreter.inevitable_cause is None:
            self.llinterpreter.inevitable_cause = info

    def op_do_malloc_fixedsize_clear(self):
        pass   # just to check that it doesn't turn inevitable

    def op_do_malloc_varsize_clear(self):
        pass   # just to check that it doesn't turn inevitable


class TestTransform:

    def interpret_inevitable(self, fn, args):
        clear_tcache()
        interp, self.graph = get_interpreter(fn, args, view=False)
        interp.frame_class = LLSTMInevFrame
        self.translator = interp.typer.annotator.translator
        insert_turn_inevitable(self.graph)
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
        addr = llmemory.raw_malloc(llmemory.sizeof(X))

        def f1():
            llmemory.raw_free(addr)

        res = self.interpret_inevitable(f1, [])
        assert res == 'raw_free'

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

    def test_raw_malloc_1(self):
        X = lltype.Struct('X', ('foo', lltype.Signed))

        def f1():
            p = lltype.malloc(X, flavor='raw')
            lltype.free(p, flavor='raw')

        res = self.interpret_inevitable(f1, [])
        assert res == 'free'

    def test_raw_malloc_2(self):
        X = lltype.Struct('X', ('foo', lltype.Signed))

        def f1():
            addr = llmemory.raw_malloc(llmemory.sizeof(X))
            llmemory.raw_free(addr)

        res = self.interpret_inevitable(f1, [])
        assert res == 'raw_free'

    def test_unknown_raw_free(self):
        X = lltype.Struct('X', ('foo', lltype.Signed))
        def f2(p):
            lltype.free(p, flavor='raw')

        res = self.interpret_inevitable(f2, [lltype.malloc(X, flavor='raw')])
        assert res == 'free'


    def test_ext_direct_call_safe(self):
        TYPE = lltype.FuncType([], lltype.Void)
        extfunc = lltype.functionptr(TYPE, 'extfunc',
                                     external='C',
                                     transactionsafe=True,
                                     _callable=lambda:0)
        def f1():
            extfunc()

        res = self.interpret_inevitable(f1, [])
        assert res is None


    def test_ext_direct_call_unsafe(self):
        TYPE = lltype.FuncType([], lltype.Void)
        extfunc = lltype.functionptr(TYPE, 'extfunc',
                                     external='C',
                                     _callable=lambda:0)
        def f1():
            extfunc()

        res = self.interpret_inevitable(f1, [])
        assert res == 'extfunc()'

    def test_rpy_direct_call(self):
        def f2():
            pass
        def f1():
            f2()

        res = self.interpret_inevitable(f1, [])
        assert res is None

    def test_rpy_indirect_call(self):
        def f2():
            pass
        def f3():
            pass
        def f1(i):
            if i:
                f = f2
            else:
                f = f3
            f()

        res = self.interpret_inevitable(f1, [True])
        assert res is None

    def test_ext_indirect_call(self):
        TYPE = lltype.FuncType([], lltype.Void)
        extfunc = lltype.functionptr(TYPE, 'extfunc',
                                     external='C',
                                     _callable=lambda:0)
        rpyfunc = lltype.functionptr(TYPE, 'rpyfunc',
                                     _callable=lambda:0)


        def f1(i):
            if i:
                f = extfunc
            else:
                f = rpyfunc
            f()

        res = self.interpret_inevitable(f1, [True])
        assert res == 'indirect_call'

    def test_instantiate_indirect_call(self):
        # inits are necessary to generate indirect_call
        class A:
            def __init__(self): pass
        class B(A):
            def __init__(self): pass
        class C(A):
            def __init__(self): pass

        def f1(i):
            if i:
                c = B
            else:
                c = C
            c()

        res = self.interpret_inevitable(f1, [True])
        assert res is None

    def test_raw_class_hint(self):
        class A:
            _alloc_flavor_ = "raw"
            _stm_dont_track_raw_accesses_ = True
            def __init__(self): self.x = 1

        def f2():
            return A()

        def f(i):
            a = f2()
            a.x = i
            i = a.x
            lltype.free(a, flavor='raw')
            return i

        res = self.interpret_inevitable(f, [2])
        assert res == 'free' # not setfield or getfield

    def test_do_malloc_llops(self):
        def f(i):
            # just to check that it doesn't turn inevitable
            llop.do_malloc_fixedsize_clear(lltype.Void)
            llop.do_malloc_varsize_clear(lltype.Void)
            return i

        res = self.interpret_inevitable(f, [2])
        assert res is None

    def test_raw_load_nonpure(self):
        X = lltype.Struct('X', ('foo', lltype.Signed))
        x1 = lltype.malloc(X, immortal=True)
        x1.foo = 42

        def f1():
            return llop.raw_load(
                lltype.Signed, llmemory.cast_ptr_to_adr(x1), 0, False)

        res = self.interpret_inevitable(f1, [])
        assert res == 'raw_load'

    def test_raw_load_pure(self):
        X = lltype.Struct('X', ('foo', lltype.Signed))
        x1 = lltype.malloc(X, immortal=True)
        x1.foo = 42

        def f1():
            return llop.raw_load(
                lltype.Signed, llmemory.cast_ptr_to_adr(x1), 0, True)

        res = self.interpret_inevitable(f1, [])
        assert res is None

    def test_threadlocal(self):
        from rpython.rlib.rthread import ThreadLocalReference
        opaque_id = lltype.opaqueptr(ThreadLocalReference.OPAQUEID, "foobar")
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        def f1():
            x = lltype.malloc(X)
            llop.threadlocalref_set(lltype.Void, opaque_id, x)
            y = llop.threadlocalref_get(lltype.Ptr(X), opaque_id)
            return x == y

        res = self.interpret_inevitable(f1, [])
        assert res is None
