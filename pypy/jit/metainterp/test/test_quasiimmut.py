from pypy.rpython.lltypesystem import lltype, llmemory, rclass
from pypy.rpython.rclass import FieldListAccessor, IR_QUASI_IMMUTABLE
from pypy.jit.metainterp import typesystem
from pypy.jit.metainterp.quasiimmut import SlowMutate
from pypy.jit.metainterp.quasiimmut import get_current_mutate_instance


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
