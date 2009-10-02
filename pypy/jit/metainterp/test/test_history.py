from pypy.jit.metainterp.history import *
from pypy.rpython.lltypesystem import lltype, llmemory


def test_repr():
    S = lltype.GcStruct('S')
    T = lltype.GcStruct('T', ('header', S))
    t = lltype.malloc(T)
    s = lltype.cast_pointer(lltype.Ptr(S), t)
    const = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, s))
    assert const._getrepr_() == "*T"

def test_constint_sharing():
    for val in [-1, 0, 1, 5, 99]:
        c1 = constint(val)
        c2 = constint(val)
        assert c1 is c2
    for val in [100000, -10000]:
        c1 = constint(val)
        c2 = constint(val)
        assert c1 is not c2
