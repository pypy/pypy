from rpython.rtyper.lltypesystem import lltype
from rpython.jit.codewriter import heaptracker


def fielddescrs(STRUCT):
    # all_fielddescrs() with the backend descr factory replaced by the
    # (PARENT, name) pair it would have built a FieldDescr for, so that the
    # test does not need a gccache.
    return heaptracker.all_fielddescrs(
        None, STRUCT, get_field_descr=lambda gccache, PARENT, name: (PARENT, name))


def names(STRUCT):
    return [name for _, name in fielddescrs(STRUCT)]


def check_indexes_match_all_fielddescrs(STRUCT):
    # get_fielddescr_index_in() computes the index that get_field_descr()
    # stores in FieldDescr, for the STRUCT it was called with, and
    # optimizeopt/info.py addresses that field's parent descr with it:
    # AbstractStructPtrInfo.init_fields() sizes _fields from
    # get_all_fielddescrs(), and its setfield()/getfield() index into that
    # list with get_index().  So for every field descr all_fielddescrs()
    # builds directly for STRUCT, the index must be the position that descr
    # has in the list.
    lst = fielddescrs(STRUCT)
    for expected, (PARENT, name) in enumerate(lst):
        if PARENT is not STRUCT:
            continue        # checked by recursing on PARENT instead
        got = heaptracker.get_fielddescr_index_in(STRUCT, name)
        assert got == expected, (
            "%s.%s is at position %d of all_fielddescrs() but "
            "get_fielddescr_index_in() says %d" %
            (STRUCT._name, name, expected, got))


INNER = lltype.Struct('INNER', ('x', lltype.Signed), ('y', lltype.Signed))
INNER2 = lltype.Struct('INNER2', ('p', lltype.Signed), ('q', lltype.Signed))


def test_index_of_inlined_struct_at_the_front():
    S = lltype.GcStruct('S', ('inner', INNER), ('c', lltype.Signed))
    assert names(S) == ['x', 'y', 'c']
    check_indexes_match_all_fielddescrs(S)
    check_indexes_match_all_fielddescrs(INNER)


def test_index_after_an_inlined_struct_that_is_not_first():
    # the fields before 'inner' must not be counted a second time
    S = lltype.GcStruct('S', ('a', lltype.Signed), ('inner', INNER),
                             ('c', lltype.Signed))
    assert names(S) == ['a', 'x', 'y', 'c']
    assert heaptracker.get_fielddescr_index_in(S, 'c') == 3
    check_indexes_match_all_fielddescrs(S)


def test_index_after_two_inlined_structs():
    S = lltype.GcStruct('S', ('a', lltype.Signed), ('i1', INNER),
                             ('b', lltype.Signed), ('i2', INNER2),
                             ('c', lltype.Signed))
    assert names(S) == ['a', 'x', 'y', 'b', 'p', 'q', 'c']
    assert heaptracker.get_fielddescr_index_in(S, 'b') == 3
    assert heaptracker.get_fielddescr_index_in(S, 'c') == 6
    check_indexes_match_all_fielddescrs(S)


def test_index_skips_void_fields():
    S = lltype.GcStruct('S', ('a', lltype.Signed), ('v', lltype.Void),
                             ('c', lltype.Signed))
    assert names(S) == ['a', 'c']
    check_indexes_match_all_fielddescrs(S)


def test_field_not_found_reports_the_number_of_fields_consumed():
    S = lltype.GcStruct('S', ('a', lltype.Signed), ('inner', INNER),
                             ('c', lltype.Signed))
    r = heaptracker.get_fielddescr_index_in(S, 'nonexistent')
    assert r < 0
    assert -r - 1 == len(fielddescrs(S))
