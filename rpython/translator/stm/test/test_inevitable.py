from rpython.rtyper.lltypesystem import lltype, llmemory, rffi, lloperation
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rtyper.llinterp import LLFrame
from rpython.rtyper.test import test_llinterp
from rpython.rtyper.test.test_llinterp import get_interpreter, clear_tcache
from rpython.translator.stm.inevitable import insert_turn_inevitable
from rpython.translator.stm.breakfinder import TransactionBreakAnalyzer
from rpython.translator.stm import inevitable
from rpython.rlib.rstm import stm_ignored
from rpython.conftest import option
import py

CATEGORIES = [inevitable.ALWAYS_ALLOW_OPERATIONS,
              inevitable.CALLS,
              inevitable.GETTERS, inevitable.SETTERS,
              inevitable.MALLOCS, inevitable.FREES,
              inevitable.INCOMPATIBLE_OPS,
              inevitable.TURN_INEVITABLE_OPS]

KNOWN_OPERATIONS = set()
for _cat in CATEGORIES:
    KNOWN_OPERATIONS |= _cat

def test_defined_operations():
    for opname in KNOWN_OPERATIONS:
        getattr(llop, opname)   # the opname must exist!

def test_no_duplicate_operations():
    for i in range(len(CATEGORIES)):
        for j in range(i):
            common = (CATEGORIES[i] & CATEGORIES[j])
            assert not common

def test_no_missing_operation():
    ALL_OPERATIONS = set(lloperation.LL_OPERATIONS)
    MISSING_OPERATIONS = ALL_OPERATIONS - KNOWN_OPERATIONS
    assert not sorted(MISSING_OPERATIONS)


class LLSTMInevFrame(LLFrame):
    def op_stm_become_inevitable(self, info):
        assert info is not None
        self.llinterpreter.inevitable_cause.append(info)

    def op_gc_dump_rpy_heap(self):
        pass    # for test_unsupported_op

    def op_do_malloc_fixedsize(self):
        pass
    def op_do_malloc_fixedsize_clear(self):
        pass
    def op_do_malloc_varsize(self):
        pass
    def op_do_malloc_varsize_clear(self):
        pass


class TestTransform:

    def interpret_inevitable(self, fn, args):
        clear_tcache()
        interp, self.graph = get_interpreter(fn, args, view=False)
        interp.frame_class = LLSTMInevFrame
        self.translator = interp.typer.annotator.translator
        self.break_analyzer = TransactionBreakAnalyzer(self.translator)
        insert_turn_inevitable(self, self.graph)
        if option.view:
            self.translator.view()
        #
        interp.inevitable_cause = []
        result = interp.eval_graph(self.graph, args)
        return interp.inevitable_cause


    def test_simple_no_inevitable(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        x1 = lltype.malloc(X, immortal=True)
        x1.foo = 42

        def f1(n):
            x1.foo = n

        res = self.interpret_inevitable(f1, [4])
        assert res == []

    def test_unsupported_op(self):
        X = lltype.Struct('X', ('foo', lltype.Signed))
        addr = llmemory.raw_malloc(llmemory.sizeof(X))

        def f1():
            llop.gc_dump_rpy_heap(lltype.Void)

        res = self.interpret_inevitable(f1, [])
        assert res == ['gc_dump_rpy_heap']

    def test_raw_getfield(self):
        X = lltype.Struct('X', ('foo', lltype.Signed))
        x1 = lltype.malloc(X, immortal=True)
        x1.foo = 42

        def f1():
            return x1.foo

        res = self.interpret_inevitable(f1, [])
        assert res == ['getfield']

    def test_raw_getfield_immutable(self):
        X = lltype.Struct('X', ('foo', lltype.Signed),
                          hints={'immutable': True})
        x1 = lltype.malloc(X, immortal=True)
        x1.foo = 42

        def f1():
            return x1.foo

        res = self.interpret_inevitable(f1, [])
        assert res == []

    def test_raw_getfield_with_hint(self):
        X = lltype.Struct('X', ('foo', lltype.Signed),
                          hints={'stm_dont_track_raw_accesses': True})
        x1 = lltype.malloc(X, immortal=True)
        x1.foo = 42

        def f1():
            return x1.foo

        res = self.interpret_inevitable(f1, [])
        assert res == []

    def test_raw_setfield(self):
        X = lltype.Struct('X', ('foo', lltype.Signed))
        x1 = lltype.malloc(X, immortal=True)
        x1.foo = 42

        def f1(n):
            x1.foo = n

        res = self.interpret_inevitable(f1, [43])
        assert res == ['setfield']

    def test_raw_setfield_with_hint(self):
        X = lltype.Struct('X', ('foo', lltype.Signed),
                          hints={'stm_dont_track_raw_accesses': True})
        x1 = lltype.malloc(X, immortal=True)

        def f1():
            x1.foo = 42

        res = self.interpret_inevitable(f1, [])
        assert res == []

    def test_raw_getarrayitem_with_hint(self):
        X = lltype.Array(lltype.Signed,
                         hints={'nolength': True,
                                'stm_dont_track_raw_accesses': True})
        x1 = lltype.malloc(X, 1, immortal=True)
        x1[0] = 42

        def f1():
            return x1[0]

        res = self.interpret_inevitable(f1, [])
        assert res == []

    def test_raw_setarrayitem_with_hint(self):
        X = lltype.Array(lltype.Signed,
                         hints={'nolength': True,
                                'stm_dont_track_raw_accesses': True})
        x1 = lltype.malloc(X, 1, immortal=True)

        def f1():
            x1[0] = 42

        res = self.interpret_inevitable(f1, [])
        assert res == []

    def test_malloc_no_inevitable(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))

        def f1():
            return lltype.malloc(X)

        res = self.interpret_inevitable(f1, [])
        assert res == []

    def test_raw_malloc_1(self):
        X = lltype.Struct('X', ('foo', lltype.Signed))

        def f1():
            p = lltype.malloc(X, flavor='raw')
            lltype.free(p, flavor='raw')

        res = self.interpret_inevitable(f1, [])
        assert res == []

    def test_raw_malloc_2(self):
        X = lltype.Struct('X', ('foo', lltype.Signed))

        def f1():
            addr = llmemory.raw_malloc(llmemory.sizeof(X))
            llmemory.raw_free(addr)

        res = self.interpret_inevitable(f1, [])
        assert res == []

    def test_unknown_raw_free(self):
        X = lltype.Struct('X', ('foo', lltype.Signed))
        def f2(p):
            lltype.free(p, flavor='raw')

        res = self.interpret_inevitable(f2, [lltype.malloc(X, flavor='raw')])
        assert res == []


    def test_ext_direct_call_safe(self):
        TYPE = lltype.FuncType([], lltype.Void)
        extfunc = lltype.functionptr(TYPE, 'extfunc',
                                     external='C',
                                     transactionsafe=True,
                                     _callable=lambda:0)
        def f1():
            extfunc()

        res = self.interpret_inevitable(f1, [])
        assert res == []


    def test_ext_direct_call_unsafe(self):
        TYPE = lltype.FuncType([], lltype.Void)
        extfunc = lltype.functionptr(TYPE, 'extfunc',
                                     external='C',
                                     _callable=lambda:0)
        def f1():
            extfunc()

        res = self.interpret_inevitable(f1, [])
        assert res == ['extfunc()']

    def test_rpy_direct_call(self):
        def f2():
            pass
        def f1():
            f2()

        res = self.interpret_inevitable(f1, [])
        assert res == []

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
        assert res == []

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
        assert res == ['indirect_call']

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
        assert res == []

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
        assert res == []   # not setfield or getfield or free

    def test_do_malloc_llops(self):
        def f(i):
            # just to check that it doesn't turn inevitable
            llop.do_malloc_fixedsize_clear(lltype.Void)
            llop.do_malloc_varsize_clear(lltype.Void)
            return i

        res = self.interpret_inevitable(f, [2])
        assert res == []

    def test_raw_load_nonpure(self):
        X = lltype.Struct('X', ('foo', lltype.Signed))
        x1 = lltype.malloc(X, immortal=True)
        x1.foo = 42

        def f1():
            return llop.raw_load(
                lltype.Signed, llmemory.cast_ptr_to_adr(x1), 0, False)

        res = self.interpret_inevitable(f1, [])
        assert res == ['raw_load']

    def test_raw_load_pure(self):
        X = lltype.Struct('X', ('foo', lltype.Signed))
        x1 = lltype.malloc(X, immortal=True)
        x1.foo = 42

        def f1():
            return llop.raw_load(
                lltype.Signed, llmemory.cast_ptr_to_adr(x1), 0, True)

        res = self.interpret_inevitable(f1, [])
        assert res == []

    def test_threadlocal(self):
        from rpython.rlib.rthread import ThreadLocalField
        from rpython.rlib.rthread import _threadlocalref_seeme
        from rpython.rlib.rthread import _field2structptr
        foobar = ThreadLocalField(lltype.Signed, 'foobar')
        offset = foobar.offset
        PSTRUCTTYPE = _field2structptr(lltype.Signed)
        def f1():
            addr = llop.threadlocalref_addr(llmemory.Address)
            # ...The rest of this test does not run on the llinterp so far...
            #p = llmemory.cast_adr_to_ptr(addr + offset, PSTRUCTTYPE)
            #p.c_value = 42
            #x = llop.threadlocalref_get(lltype.Signed, offset)
            #assert x == 42

        res = self.interpret_inevitable(f1, [])
        assert res == []



    def test_only_one_inev(self):
        X = lltype.Struct('X', ('foo', lltype.Signed))
        x1 = lltype.malloc(X, immortal=True)
        x1.foo = 42

        def f1():
            r = 0
            r += x1.foo
            r += x1.foo
            return r

        res = self.interpret_inevitable(f1, [])
        assert res == ['getfield']

    def test_only_one_inev2(self):
        X = lltype.Struct('X', ('foo', lltype.Signed))
        x1 = lltype.malloc(X, immortal=True)
        x1.foo = 42

        def f1(i):
            r = 0
            if i:
                r += x1.foo
            else:
                r += x1.foo
            r += x1.foo
            return r

        res = self.interpret_inevitable(f1, [1])
        assert res == ['getfield']

    def test_partially_redundant_inev3(self):
        X = lltype.Struct('X', ('foo', lltype.Signed))
        x1 = lltype.malloc(X, immortal=True)
        x1.foo = 42

        def f1(i):
            r = 0
            if i:
                r += x1.foo
            r += x1.foo
            return r

        res = self.interpret_inevitable(f1, [1])
        assert res == ['getfield', 'getfield']

    def test_with_break_inev(self):
        X = lltype.Struct('X', ('foo', lltype.Signed))
        x1 = lltype.malloc(X, immortal=True)
        x1.foo = 42
        import time
        def f1():
            r = 0
            r += x1.foo
            time.sleep(0)
            r += x1.foo
            return r

        res = self.interpret_inevitable(f1, [])
        assert res == ['getfield', 'getfield']

    def test_with_inev_inev(self):
        from rpython.rtyper.lltypesystem.lloperation import llop
        X = lltype.Struct('X', ('foo', lltype.Signed))
        x1 = lltype.malloc(X, immortal=True)
        x1.foo = 42
        def f1():
            r = 0
            llop.stm_become_inevitable(lltype.Void, "inev")
            r += x1.foo
            return r

        res = self.interpret_inevitable(f1, [])
        # weird check ahead:
        assert len(res) == 1 and isinstance(res[0]._T, lltype.GcStruct)


    def test_not_for_local_raw(self):
        X = lltype.Struct('X', ('foo', lltype.Signed))
        A = lltype.Array(lltype.Signed)
        #
        def f1(i):
            x1 = lltype.malloc(X, flavor='raw')
            x1.foo = 42 # ok
            r = x1.foo # ok
            x = lltype.malloc(A, i, flavor='raw', zero=True)
            x[i-1] = i # ok
            lltype.free(x1, flavor='raw')
            lltype.free(x, flavor='raw')
            return r
        #
        res = self.interpret_inevitable(f1, [1])
        assert res == []


    def test_for_local_raw_with_break(self):
        X = lltype.Struct('X', ('foo', lltype.Signed))
        import time
        def f1(i):
            x1 = lltype.malloc(X, flavor='raw')
            x1.foo = 42 # ok
            time.sleep(0) # gil rel
            r = x1.foo # inev
            x1.foo = 8 # ok
            if i:
                lltype.free(x1, flavor='raw')
            return r

        res = self.interpret_inevitable(f1, [1])
        assert res == ['getfield',]

    def test_for_local_raw_no_free(self):
        X = lltype.Struct('X', ('foo', lltype.Signed))

        def f1(i):
            x1 = lltype.malloc(X, flavor='raw')
            x1.foo = 42 # ok
            r = x1.foo # ok
            if i:
                lltype.free(x1, flavor='raw')
            return r

        res = self.interpret_inevitable(f1, [1])
        assert res == []


    def test_for_unknown_raw(self):
        X = lltype.Struct('X', ('foo', lltype.Signed))

        def g(r):
            r.foo = 28 # inev bc. unknown
        def f1(i):
            x1 = lltype.malloc(X, flavor='raw')
            x1.foo = 42 # ok
            if i:
                g(x1) # no break
            r = x1.foo # ok
            lltype.free(x1, flavor='raw')
            return r

        res = self.interpret_inevitable(f1, [1])
        assert res == []
        res = self.interpret_inevitable(g, [lltype.malloc(X, flavor='raw', immortal=True)])
        assert res == ['setfield']


    def test_local_raw_in_same_transaction(self):
        X = lltype.Struct('X', ('foo', lltype.Signed))
        #
        for ts in [True, False]:
            TYPE = lltype.FuncType([], lltype.Void)
            extfunc = lltype.functionptr(TYPE, 'extfunc',
                                         external='C',
                                         transactionsafe=ts,
                                         _callable=lambda:0)
            def f1(i):
                x1 = lltype.malloc(X, flavor='raw')
                x1.foo = 42
                extfunc()
                r = x1.foo
                lltype.free(x1, flavor='raw')
                return r

            res = self.interpret_inevitable(f1, [1])
            if not ts:
                assert res == ['extfunc()']
            else:
                assert res == []


    def test_stm_ignored(self):
        X = lltype.Struct('X', ('foo', lltype.Signed))
        x1 = lltype.malloc(X, flavor='raw', immortal=True)

        def f1():
            return x1.foo
        res = self.interpret_inevitable(f1, [])
        assert res == ['getfield']

        def f2():
            with stm_ignored:
                return x1.foo
        res = self.interpret_inevitable(f2, [])
        assert res == []

    def test_gc_load_indexed(self):
        from rpython.rtyper.annlowlevel import llstr
        from rpython.rtyper.lltypesystem.rstr import STR

        s = "hi"
        def f(byte_offset):
            lls = llstr(s)
            base_ofs = (llmemory.offsetof(STR, 'chars') +
                        llmemory.itemoffsetof(STR.chars, 0))
            scale_factor = llmemory.sizeof(lltype.Char)
            return llop.gc_load_indexed(rffi.SHORT, lls, byte_offset,
                                        scale_factor, base_ofs)
        res = self.interpret_inevitable(f, [1])
        assert res == []
