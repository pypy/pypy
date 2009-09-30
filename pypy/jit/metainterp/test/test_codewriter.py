import py
from pypy.rlib import jit
from pypy.jit.metainterp import support, typesystem
from pypy.jit.metainterp.policy import JitPolicy
from pypy.jit.metainterp.codewriter import CodeWriter
from pypy.jit.metainterp.test.test_basic import LLJitMixin, OOJitMixin
from pypy.translator.translator import graphof
from pypy.rpython.lltypesystem.rbuiltin import ll_instantiate


class SomeLabel(object):
    def __eq__(self, other):
        return repr(other).startswith('label')    # :-/


class TestCodeWriter:
    type_system = 'lltype'

    def setup_method(self, _):
        class FakeMetaInterpSd:
            virtualizable_info = None
            def find_opcode(self, name):
                default = len(self.opname_to_index)
                return self.opname_to_index.setdefault(name, default)
            def _register_indirect_call_target(self, fnaddress, jitcode):
                self.indirectcalls.append((fnaddress, jitcode))

        class FakeCPU:
            ts = typesystem.llhelper
            supports_floats = False
            def fielddescrof(self, STRUCT, fieldname):
                return ('fielddescr', STRUCT, fieldname)
            def calldescrof(self, FUNC, NON_VOID_ARGS, RESULT):
                return ('calldescr', FUNC, NON_VOID_ARGS, RESULT)

        self.metainterp_sd = FakeMetaInterpSd()
        self.metainterp_sd.opcode_implementations = None
        self.metainterp_sd.opname_to_index = {}
        self.metainterp_sd.indirectcalls = []
        self.metainterp_sd.cpu = FakeCPU()

    def make_graph(self, func, values):
        rtyper = support.annotate(func, values,
                                  type_system=self.type_system)
        self.metainterp_sd.cpu.rtyper = rtyper
        return rtyper.annotator.translator.graphs[0]

    def graphof(self, func):
        rtyper = self.metainterp_sd.cpu.rtyper
        return graphof(rtyper.annotator.translator, func)

    def test_basic(self):
        def f(n):
            return n + 10
        graph = self.make_graph(f, [5])
        cw = CodeWriter(self.metainterp_sd, JitPolicy())
        jitcode = cw.make_one_bytecode((graph, None), False)
        assert jitcode._source == [
            SomeLabel(),
            'int_add', 0, 1, '# => r1',
            'make_new_vars_1', 2,
            'return']

    def test_indirect_call_target(self):
        def g(m):
            return 123
        def h(m):
            return 456
        def f(n):
            if n > 3:
                call = g
            else:
                call = h
            return call(n+1) + call(n+2)
        graph = self.make_graph(f, [5])
        cw = CodeWriter(self.metainterp_sd, JitPolicy())
        jitcode = cw.make_one_bytecode((graph, None), False)
        assert len(self.metainterp_sd.indirectcalls) == 2
        names = [jitcode.name for (fnaddress, jitcode)
                               in self.metainterp_sd.indirectcalls]
        assert dict.fromkeys(names) == {'g': None, 'h': None}

    def test_indirect_look_inside_only_one(self):
        def g(m):
            return 123
        @jit.dont_look_inside
        def h(m):
            return 456
        def f(n):
            if n > 3:
                call = g
            else:
                call = h
            return call(n+1) + call(n+2)
        graph = self.make_graph(f, [5])
        cw = CodeWriter(self.metainterp_sd, JitPolicy())
        jitcode = cw.make_one_bytecode((graph, None), False)
        assert len(self.metainterp_sd.indirectcalls) == 1
        names = [jitcode.name for (fnaddress, jitcode)
                               in self.metainterp_sd.indirectcalls]
        assert dict.fromkeys(names) == {'g': None}

    def test_instantiate(self):
        py.test.skip("in-progress")
        class A1:     id = 651
        class A2(A1): id = 652
        class B1:     id = 661
        class B2(B1): id = 662
        def f(n):
            if n > 5:
                x, y = A1, B1
            else:
                x, y = A2, B2
            n += 1
            return x().id + y().id + n
        graph = self.make_graph(f, [5])
        cw = CodeWriter(self.metainterp_sd, JitPolicy())
        cw.make_one_bytecode((graph, None), False)
        graph2 = self.graphof(ll_instantiate)
        jitcode = cw.make_one_bytecode((graph2, None), False)
        assert 'residual_call' not in jitcode._source
        xxx


class ImmutableFieldsTests:

    def test_fields(self):
        class X(object):
            _immutable_fields_ = ["x"]

            def __init__(self, x):
                self.x = x

        def f(x):
            y = X(x)
            return y.x + 5
        res = self.interp_operations(f, [23])
        assert res == 28
        self.check_history_(getfield_gc=0, getfield_gc_pure=1, int_add=1)

    def test_array(self):
        class X(object):
            _immutable_fields_ = ["y[*]"]

            def __init__(self, x):
                self.y = x
        def f(index):
            l = [1, 2, 3, 4]
            l[2] = 30
            a = X(l)
            return a.y[index]
        res = self.interp_operations(f, [2], listops=True)
        assert res == 30
        self.check_history_(getfield_gc=0, getfield_gc_pure=1,
                            getarrayitem_gc=0, getarrayitem_gc_pure=1)


    def test_array_in_immutable(self):
        class X(object):
            _immutable_ = True
            _immutable_fields_ = ["lst[*]"]

            def __init__(self, lst, y):
                self.lst = lst
                self.y = y

        def f(x, index):
            y = X([x], x+1)
            return y.lst[index] + y.y + 5
        res = self.interp_operations(f, [23, 0], listops=True)
        assert res == 23 + 24 + 5
        self.check_history_(getfield_gc=0, getfield_gc_pure=2,
                            getarrayitem_gc=0, getarrayitem_gc_pure=1,
                            int_add=3)


class TestLLtypeImmutableFieldsTests(ImmutableFieldsTests, LLJitMixin):
    pass

class TestOOtypeImmutableFieldsTests(ImmutableFieldsTests, OOJitMixin):
   pass
