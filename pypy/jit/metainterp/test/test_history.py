from pypy.jit.metainterp.history import *
from pypy.rpython.lltypesystem import lltype, llmemory, rffi


def test_repr():
    S = lltype.GcStruct('S')
    T = lltype.GcStruct('T', ('header', S))
    t = lltype.malloc(T)
    s = lltype.cast_pointer(lltype.Ptr(S), t)
    const = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, s))
    assert const._getrepr_() == "*T"

def test_repr_ll2ctypes():
    ptr = lltype.malloc(rffi.VOIDPP.TO, 10, flavor='raw')
    # force it to be a ll2ctypes object
    ptr = rffi.cast(rffi.VOIDPP, rffi.cast(rffi.LONG, ptr))
    adr = llmemory.cast_ptr_to_adr(ptr)
    lltype.free(ptr, flavor='raw')
    intval = llmemory.cast_adr_to_int(adr, 'symbolic')
    box = BoxInt(intval)
    s = box.repr_rpython()
    assert s.startswith('12345/') # the arbitrary hash value used by
                                  # make_hashable_int
