
from pypy.jit.backend.x86.support import NonmovableGrowableArraySigned, CHUNK_SIZE
from pypy.rpython.lltypesystem import lltype, llmemory, rffi

def test_nonmovable_growable_array():
    ar = NonmovableGrowableArraySigned()
    adr = ar.get_addr_for_num(10)
    rffi.cast(rffi.CArrayPtr(lltype.Signed), adr)[0] = 42
    assert ar.getitem(10) == 42
    ar.setitem(42, 38)
    adr = ar.get_addr_for_num(42)
    assert rffi.cast(rffi.CArrayPtr(lltype.Signed), adr)[0] == 38
    adr = ar.get_addr_for_num(CHUNK_SIZE + 10)
    rffi.cast(rffi.CArrayPtr(lltype.Signed), adr)[0] = 42
    assert ar.getitem(CHUNK_SIZE + 10) == 42
    ar.setitem(CHUNK_SIZE + 42, 38)
    adr = ar.get_addr_for_num(CHUNK_SIZE + 42)
    assert rffi.cast(rffi.CArrayPtr(lltype.Signed), adr)[0] == 38
    adr = ar.get_addr_for_num(3 * CHUNK_SIZE + 10)
    rffi.cast(rffi.CArrayPtr(lltype.Signed), adr)[0] = 42
    assert ar.getitem(3 * CHUNK_SIZE + 10) == 42
    ar.setitem(3 * CHUNK_SIZE + 42, 38)
    adr = ar.get_addr_for_num(3 * CHUNK_SIZE + 42)
    assert rffi.cast(rffi.CArrayPtr(lltype.Signed), adr)[0] == 38
    ar.setitem(8*CHUNK_SIZE, 13)
    assert ar.getitem(8*CHUNK_SIZE) == 13
    
