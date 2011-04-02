from pypy.rpython.lltypesystem import lltype, llmemory, rclass
from pypy.rpython.rclass import FieldListAccessor, IR_QUASI_IMMUTABLE
from pypy.jit.metainterp import typesystem
from pypy.jit.metainterp.quasiimmut import SlowMutate
from pypy.jit.metainterp.quasiimmut import get_current_mutate_instance
from pypy.jit.metainterp.test.test_basic import LLJitMixin
from pypy.rlib.jit import JitDriver, dont_look_inside


def test_get_current_mutate_instance():
    accessor = FieldListAccessor()
    accessor.initialize(None, {'inst_x': IR_QUASI_IMMUTABLE})
    STRUCT = lltype.GcStruct('Foo', ('inst_x', lltype.Signed),
                             ('mutate_x', rclass.OBJECTPTR),
                             hints={'immutable_fields': accessor})
    foo = lltype.malloc(STRUCT, zero=True)
    foo.inst_x = 42
    assert not foo.mutate_x

    class FakeCPU:
        ts = typesystem.llhelper

        def bh_getfield_gc_r(self, gcref, fielddescr):
            assert fielddescr == mutatefielddescr
            foo = lltype.cast_opaque_ptr(lltype.Ptr(STRUCT), gcref)
            result = foo.mutate_x
            return lltype.cast_opaque_ptr(llmemory.GCREF, result)

        def bh_setfield_gc_r(self, gcref, fielddescr, newvalue_gcref):
            assert fielddescr == mutatefielddescr
            foo = lltype.cast_opaque_ptr(lltype.Ptr(STRUCT), gcref)
            newvalue = lltype.cast_opaque_ptr(rclass.OBJECTPTR, newvalue_gcref)
            foo.mutate_x = newvalue

    cpu = FakeCPU()
    mutatefielddescr = ('fielddescr', STRUCT, 'mutate_x')

    foo_gcref = lltype.cast_opaque_ptr(llmemory.GCREF, foo)
    sm1 = get_current_mutate_instance(cpu, foo_gcref, mutatefielddescr)
    assert isinstance(sm1, SlowMutate)
    sm2 = get_current_mutate_instance(cpu, foo_gcref, mutatefielddescr)
    assert sm1 is sm2


class QuasiImmutTests:

    def test_simple_1(self):
        myjitdriver = JitDriver(greens=['foo'], reds=['x', 'total'])
        class Foo:
            _immutable_fields_ = ['a?']
            def __init__(self, a):
                self.a = a
        def f(a, x):
            foo = Foo(a)
            total = 0
            while x > 0:
                myjitdriver.jit_merge_point(foo=foo, x=x, total=total)
                # read a quasi-immutable field out of a Constant
                total += foo.a
                x -= 1
            return total
        #
        res = self.meta_interp(f, [100, 7])
        assert res == 700
        self.check_loops(getfield_gc=0, everywhere=True)

    def test_change_during_tracing(self):
        myjitdriver = JitDriver(greens=['foo'], reds=['x', 'total'])
        class Foo:
            _immutable_fields_ = ['a?']
            def __init__(self, a):
                self.a = a
        @dont_look_inside
        def residual_call(foo):
            foo.a += 1
        def f(a, x):
            foo = Foo(a)
            total = 0
            while x > 0:
                myjitdriver.jit_merge_point(foo=foo, x=x, total=total)
                # read a quasi-immutable field out of a Constant
                total += foo.a
                residual_call(foo)
                x -= 1
            return total
        #
        assert f(100, 7) == 721
        res = self.meta_interp(f, [100, 7])
        assert res == 721
        self.check_loops(getfield_gc=1)


class TestLLtypeGreenFieldsTests(QuasiImmutTests, LLJitMixin):
    pass
