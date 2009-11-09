from pypy.rpython.lltypesystem.rclass import OBJECT
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype
from pypy.jit.metainterp.effectinfo import effectinfo_from_writeanalyze

def test_filter_out_typeptr():
    effects = frozenset([("struct", lltype.Ptr(OBJECT), "typeptr")])
    effectinfo = effectinfo_from_writeanalyze(effects, None)
    assert not effectinfo.write_descrs_fields
    assert not effectinfo.write_descrs_arrays

def test_filter_out_array_of_void():
    effects = frozenset([("array", lltype.Ptr(lltype.GcArray(lltype.Void)))])
    effectinfo = effectinfo_from_writeanalyze(effects, None)
    assert not effectinfo.write_descrs_fields
    assert not effectinfo.write_descrs_arrays

def test_filter_out_struct_with_void():
    effects = frozenset([("struct", lltype.Ptr(lltype.GcStruct("x", ("a", lltype.Void))), "a")])
    effectinfo = effectinfo_from_writeanalyze(effects, None)
    assert not effectinfo.write_descrs_fields
    assert not effectinfo.write_descrs_arrays

def test_filter_out_ooarray_of_void():
    effects = frozenset([("array", ootype.Array(ootype.Void))])
    effectinfo = effectinfo_from_writeanalyze(effects, None)
    assert not effectinfo.write_descrs_fields
    assert not effectinfo.write_descrs_arrays

def test_filter_out_instance_with_void():
    effects = frozenset([("struct", ootype.Instance("x", ootype.ROOT, {"a": ootype.Void}), "a")])
    effectinfo = effectinfo_from_writeanalyze(effects, None)
    assert not effectinfo.write_descrs_fields
    assert not effectinfo.write_descrs_arrays
