
from pypy.jit.backend.x86.support import values_array
from pypy.rpython.lltypesystem import lltype, llmemory, rffi

def test_values_array_signed():
    ar = values_array(lltype.Signed, 50)
    adr = ar.get_addr_for_num(10)
    rffi.cast(rffi.CArrayPtr(lltype.Signed), adr)[0] = 42
    assert ar.getitem(10) == 42
    ar.setitem(42, 38)
    adr = ar.get_addr_for_num(42)
    assert rffi.cast(rffi.CArrayPtr(lltype.Signed), adr)[0] == 38

def test_values_array_float():
    ar = values_array(lltype.Float, 50)
    adr = ar.get_addr_for_num(10)
    rffi.cast(rffi.CArrayPtr(lltype.Float), adr)[0] = 42.5
    assert ar.getitem(10) == 42.5
    ar.setitem(42, 38.5)
    adr = ar.get_addr_for_num(42)
    assert rffi.cast(rffi.CArrayPtr(lltype.Float), adr)[0] == 38.5
