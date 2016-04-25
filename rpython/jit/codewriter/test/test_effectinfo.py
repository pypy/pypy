import pytest

from rpython.jit.codewriter.effectinfo import (effectinfo_from_writeanalyze,
    EffectInfo, VirtualizableAnalyzer, expand_descr_list)
from rpython.rlib import jit
from rpython.rtyper.lltypesystem import lltype
from rpython.rtyper.rclass import OBJECT
from rpython.translator.translator import TranslationContext, graphof


class FakeDescr(tuple):
    pass


class FakeCPU(object):
    def fielddescrof(self, T, fieldname):
        return FakeDescr(('fielddescr', T, fieldname))

    def arraydescrof(self, A):
        return FakeDescr(('arraydescr', A))


def test_no_oopspec_duplicate():
    # check that all the various EffectInfo.OS_* have unique values
    oopspecs = set()
    for name, value in EffectInfo.__dict__.iteritems():
        if name.startswith('OS_'):
            assert value not in oopspecs
            oopspecs.add(value)


def test_include_read_field():
    S = lltype.GcStruct("S", ("a", lltype.Signed))
    effects = frozenset([("readstruct", lltype.Ptr(S), "a")])
    cpu = FakeCPU()
    effectinfo = effectinfo_from_writeanalyze(effects, cpu)
    assert (expand_descr_list(cpu, effectinfo.readonly_descrs_fields) ==
                [('fielddescr', S, "a")])
    assert expand_descr_list(cpu, effectinfo.write_descrs_fields) == []
    assert expand_descr_list(cpu, effectinfo.write_descrs_arrays) == []


def test_include_write_field():
    S = lltype.GcStruct("S", ("a", lltype.Signed))
    effects = frozenset([("struct", lltype.Ptr(S), "a")])
    cpu = FakeCPU()
    effectinfo = effectinfo_from_writeanalyze(effects, cpu)
    assert (expand_descr_list(cpu, effectinfo.write_descrs_fields) ==
                [('fielddescr', S, "a")])
    assert expand_descr_list(cpu, effectinfo.readonly_descrs_fields) == []
    assert expand_descr_list(cpu, effectinfo.write_descrs_arrays) == []


def test_include_read_array():
    A = lltype.GcArray(lltype.Signed)
    effects = frozenset([("readarray", lltype.Ptr(A))])
    cpu = FakeCPU()
    effectinfo = effectinfo_from_writeanalyze(effects, cpu)
    assert expand_descr_list(cpu, effectinfo.readonly_descrs_fields) == []
    assert (expand_descr_list(cpu, effectinfo.readonly_descrs_arrays) ==
                [('arraydescr', A)])
    assert expand_descr_list(cpu, effectinfo.write_descrs_fields) == []
    assert expand_descr_list(cpu, effectinfo.write_descrs_arrays) == []


def test_include_write_array():
    A = lltype.GcArray(lltype.Signed)
    effects = frozenset([("array", lltype.Ptr(A))])
    cpu = FakeCPU()
    effectinfo = effectinfo_from_writeanalyze(effects, cpu)
    assert expand_descr_list(cpu, effectinfo.readonly_descrs_fields) == []
    assert expand_descr_list(cpu, effectinfo.write_descrs_fields) == []
    assert (expand_descr_list(cpu, effectinfo.write_descrs_arrays) ==
                [('arraydescr', A)])


def test_dont_include_read_and_write_field():
    S = lltype.GcStruct("S", ("a", lltype.Signed))
    effects = frozenset([("readstruct", lltype.Ptr(S), "a"),
                         ("struct", lltype.Ptr(S), "a")])
    cpu = FakeCPU()
    effectinfo = effectinfo_from_writeanalyze(effects, cpu)
    assert expand_descr_list(cpu, effectinfo.readonly_descrs_fields) == []
    assert (expand_descr_list(cpu, effectinfo.write_descrs_fields) ==
                [('fielddescr', S, "a")])
    assert expand_descr_list(cpu, effectinfo.write_descrs_arrays) == []


def test_dont_include_read_and_write_array():
    A = lltype.GcArray(lltype.Signed)
    effects = frozenset([("readarray", lltype.Ptr(A)),
                         ("array", lltype.Ptr(A))])
    cpu = FakeCPU()
    effectinfo = effectinfo_from_writeanalyze(effects, cpu)
    assert expand_descr_list(cpu, effectinfo.readonly_descrs_fields) == []
    assert expand_descr_list(cpu, effectinfo.readonly_descrs_arrays) == []
    assert expand_descr_list(cpu, effectinfo.write_descrs_fields) == []
    assert (expand_descr_list(cpu, effectinfo.write_descrs_arrays) ==
                [('arraydescr', A)])


def test_filter_out_typeptr():
    effects = frozenset([("struct", lltype.Ptr(OBJECT), "typeptr")])
    cpu = FakeCPU()
    effectinfo = effectinfo_from_writeanalyze(effects, cpu)
    assert expand_descr_list(cpu, effectinfo.readonly_descrs_fields) == []
    assert expand_descr_list(cpu, effectinfo.write_descrs_fields) == []
    assert expand_descr_list(cpu, effectinfo.write_descrs_arrays) == []


def test_filter_out_array_of_void():
    effects = frozenset([("array", lltype.Ptr(lltype.GcArray(lltype.Void)))])
    cpu = FakeCPU()
    effectinfo = effectinfo_from_writeanalyze(effects, cpu)
    assert expand_descr_list(cpu, effectinfo.readonly_descrs_fields) == []
    assert expand_descr_list(cpu, effectinfo.write_descrs_fields) == []
    assert expand_descr_list(cpu, effectinfo.write_descrs_arrays) == []


def test_filter_out_struct_with_void():
    effects = frozenset([("struct", lltype.Ptr(lltype.GcStruct("x", ("a", lltype.Void))), "a")])
    cpu = FakeCPU()
    effectinfo = effectinfo_from_writeanalyze(effects, cpu)
    assert expand_descr_list(cpu, effectinfo.readonly_descrs_fields) == []
    assert expand_descr_list(cpu, effectinfo.write_descrs_fields) == []
    assert expand_descr_list(cpu, effectinfo.write_descrs_arrays) == []


class TestVirtualizableAnalyzer(object):
    def analyze(self, func, sig):
        t = TranslationContext()
        t.buildannotator().build_types(func, sig)
        t.buildrtyper().specialize()
        fgraph = graphof(t, func)
        return VirtualizableAnalyzer(t).analyze(fgraph.startblock.operations[0])

    def test_constructor(self):
        class A(object):
            x = 1

        class B(A):
            x = 2

        @jit.elidable
        def g(cls):
            return cls()

        def f(x):
            if x:
                cls = A
            else:
                cls = B
            return g(cls).x

        def entry(x):
            return f(x)

        res = self.analyze(entry, [int])
        assert not res
