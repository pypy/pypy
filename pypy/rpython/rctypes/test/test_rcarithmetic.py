import py.test
from pypy.rpython.rctypes.rcarithmetic import *
from pypy.rpython.lltypesystem import lltype
from pypy.rpython import rarithmetic

def test_signedness():
    assert rcbyte(-1) < 0
    assert rcubyte(-1) > 0

def test_promotion():
    assert type(rcbyte(1) + 1) is rcbyte
    assert type(1 + rcbyte(1)) is rcbyte
    
    assert type(rcbyte(1) + rcshort(1)) is rcshort
    assert type(rcshort(1) + rcbyte(1)) is rcshort

    py.test.raises(TypeError, 'rcubyte(1) + rcshort(1)')
    py.test.raises(TypeError, 'rcshort(1) + rcubyte(1)')

    
def test_typeof():
    assert lltype.typeOf(rarithmetic.r_int(0)) == lltype.Signed
    assert lltype.typeOf(rclong(0)) == lltype.Signed
    assert lltype.Signed == CLong
    assert lltype.typeOf(rarithmetic.r_uint(0)) == lltype.Unsigned
    assert lltype.typeOf(rculong(0)) == lltype.Unsigned
    assert lltype.Unsigned == CULong

    assert lltype.typeOf(rcbyte(0)) == CByte
    assert lltype.typeOf(rcshort(0)) == CShort

    assert lltype.typeOf(rcushort(0)) == CUShort
