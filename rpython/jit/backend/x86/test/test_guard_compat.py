from rpython.jit.backend.x86.guard_compat import *


def test_invalidate_cache():
    b = lltype.malloc(BACKEND_CHOICES, 4)
    invalidate_pair(b, BCMOSTRECENT)
    x = b.bc_most_recent.gcref
    assert rffi.cast(lltype.Unsigned, x) == r_uint(-1)

def check_bclist(bchoices, expected):
    assert len(bchoices.bc_list) == len(expected)
    for i in range(len(bchoices.bc_list)):
        pair = bchoices.bc_list[i]
        if lltype.typeOf(expected[i][0]) == llmemory.GCREF:
            assert pair.gcref == expected[i][0]
        else:
            assert rffi.cast(lltype.Signed, pair.gcref) == expected[i][0]
        assert pair.asmaddr == expected[i][1]

def test_add_in_tree():
    b = lltype.malloc(BACKEND_CHOICES, 3, zero=True)    # 3 * null
    check_bclist(b, [
        (0, 0),    # null
        (0, 0),    # null
        (0, 0),    # null
        ])
    new_gcref = rffi.cast(llmemory.GCREF, 717344)
    new_asmaddr = 1234567
    b2 = add_in_tree(b, new_gcref, new_asmaddr)
    check_bclist(b2, [
        (0, 0),    # null
        (0, 0),    # null
        (0, 0),    # null
        (new_gcref, new_asmaddr),
        (-1, 0),   # invalid
        (-1, 0),   # invalid
        (-1, 0),   # invalid
        ])
    new_gcref_2 = rffi.cast(llmemory.GCREF, 717000)   # lower than before
    new_asmaddr_2 = 2345678
    b3 = add_in_tree(b2, new_gcref_2, new_asmaddr_2)
    assert b3 == b2     # was still large enough
    check_bclist(b2, [
        (0, 0),    # null
        (0, 0),    # null
        (0, 0),    # null
        (new_gcref_2, new_asmaddr_2),
        (new_gcref,   new_asmaddr),
        (-1, 0),   # invalid
        (-1, 0),   # invalid
        ])
    new_gcref_3 = rffi.cast(llmemory.GCREF, 717984)   # higher than before
    new_asmaddr_3 = 3456789
    b4 = add_in_tree(b3, new_gcref_3, new_asmaddr_3)
    assert b4 == b2     # was still large enough
    check_bclist(b2, [
        (0, 0),    # null
        (0, 0),    # null
        (0, 0),    # null
        (new_gcref_2, new_asmaddr_2),
        (new_gcref,   new_asmaddr),
        (new_gcref_3, new_asmaddr_3),
        (-1, 0),   # invalid
        ])
