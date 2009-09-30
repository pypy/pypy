import py
from pypy.jit.metainterp import support, typesystem
from pypy.jit.metainterp.policy import JitPolicy
from pypy.jit.metainterp.codewriter import CodeWriter
from pypy.jit.metainterp.test.test_basic import LLJitMixin, OOJitMixin


class SomeLabel(object):
    def __eq__(self, other):
        return repr(other).startswith('label')    # :-/


class TestCodeWriter:
    type_system = 'lltype'

    def setup_method(self, _):
        class FakeMetaInterpSd:
            def find_opcode(self, name):
                default = len(self.opname_to_index)
                return self.opname_to_index.setdefault(name, default)
            def _register_indirect_call_target(self, fnaddress, jitcode):
                self.indirectcalls.append((fnaddress, jitcode))

        class FakeCPU:
            ts = typesystem.llhelper
            supports_floats = False

        self.metainterp_sd = FakeMetaInterpSd()
        self.metainterp_sd.opcode_implementations = None
        self.metainterp_sd.opname_to_index = {}
        self.metainterp_sd.indirectcalls = []
        self.metainterp_sd.cpu = FakeCPU()

    def getgraph(self, func, values):
        rtyper = support.annotate(func, values,
                                  type_system=self.type_system)
        self.metainterp_sd.cpu.rtyper = rtyper
        return rtyper.annotator.translator.graphs[0]

    def test_basic(self):
        def f(n):
            return n + 10
        graph = self.getgraph(f, [5])
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
        graph = self.getgraph(f, [5])
        cw = CodeWriter(self.metainterp_sd, JitPolicy())
        jitcode = cw.make_one_bytecode((graph, None), False)
        assert len(self.metainterp_sd.indirectcalls) == 2
        names = [jitcode.name for (fnaddress, jitcode)
                               in self.metainterp_sd.indirectcalls]
        assert dict.fromkeys(names) == {'g': None, 'h': None}


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
