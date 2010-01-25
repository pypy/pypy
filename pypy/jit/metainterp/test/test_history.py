from pypy.jit.metainterp.history import *
from pypy.rpython.lltypesystem import lltype, llmemory


def test_repr():
    S = lltype.GcStruct('S')
    T = lltype.GcStruct('T', ('header', S))
    t = lltype.malloc(T)
    s = lltype.cast_pointer(lltype.Ptr(S), t)
    const = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, s))
    assert const._getrepr_() == "*T"

def test_slicing():
    h = History()
    h.operations = [1, 2, 3, 4, 5]
    rest = h.slice_history_at(2)
    assert rest == [4, 5]
    assert h.operations == [1, 2]
