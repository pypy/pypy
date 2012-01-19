import py
from pypy.translator.stm._rffi_stm import *
from pypy.translator.stm.llstm import *
from pypy.rpython.annlowlevel import llhelper
from pypy.rlib.rarithmetic import r_longlong, r_singlefloat


A = lltype.Struct('A', ('x', lltype.Signed), ('y', lltype.Signed),
                       ('c1', lltype.Char), ('c2', lltype.Char),
                       ('c3', lltype.Char), ('l', lltype.SignedLongLong),
                       ('f', lltype.Float), ('sa', lltype.SingleFloat),
                       ('sb', lltype.SingleFloat), ('v', lltype.Void))
rll1 = r_longlong(-10000000000003)
rll2 = r_longlong(-300400500600700)
rf1 = -12.38976129
rf2 = 52.1029
rs1a = r_singlefloat(-0.598127)
rs2a = r_singlefloat(0.017634)
rs1b = r_singlefloat(40.121)
rs2b = r_singlefloat(-9e9)

def callback1(a):
    a = rffi.cast(lltype.Ptr(A), a)
    assert a.x == -611
    assert a.c1 == '/'
    assert a.c2 == '\\'
    assert a.c3 == '!'
    assert a.l == rll1
    assert a.f == rf1
    assert float(a.sa) == float(rs1a)
    assert float(a.sb) == float(rs1b)
    assert a.v == None
    assert stm_getfield(a, 'x') == -611
    assert stm_getfield(a, 'c2') == '\\'
    assert stm_getfield(a, 'c1') == '/'
    assert stm_getfield(a, 'c3') == '!'
    assert stm_getfield(a, 'l') == rll1
    assert stm_getfield(a, 'f') == rf1
    assert float(stm_getfield(a, 'sa')) == float(rs1a)
    assert float(stm_getfield(a, 'sb')) == float(rs1b)
    p = lltype.direct_fieldptr(a, 'x')
    p = rffi.cast(SignedP, p)
    stm_write_word(p, 42 * a.y)
    assert stm_getfield(a, 'x') == 42 * a.y
    assert a.x == -611 # xxx still the old value when reading non-transact.
    if a.y < 10:
        a.y += 1    # non-transactionally
        stm_abort_and_retry()
    return lltype.nullptr(rffi.VOIDP.TO)

def test_stm_getfield():
    a = lltype.malloc(A, flavor='raw')
    a.x = -611
    a.c1 = '/'
    a.c2 = '\\'
    a.c3 = '!'
    a.y = 0
    a.l = rll1
    a.f = rf1
    a.sa = rs1a
    a.sb = rs1b
    a.v = None
    stm_descriptor_init()
    stm_perform_transaction(llhelper(CALLBACK, callback1),
                        rffi.cast(rffi.VOIDP, a))
    stm_descriptor_done()
    assert a.x == 420
    assert a.c1 == '/'
    assert a.c2 == '\\'
    assert a.c3 == '!'
    assert a.l == rll1
    assert a.f == rf1
    assert float(a.sa) == float(rs1a)
    assert float(a.sb) == float(rs1b)
    assert a.v == None
    assert a.y == 10
    lltype.free(a, flavor='raw')

def callback2(a):
    a = rffi.cast(lltype.Ptr(A), a)
    assert a.x == -611
    assert a.c1 == '&'
    assert a.c2 == '*'
    assert a.c3 == '#'
    assert a.l == rll1
    assert a.f == rf1
    assert float(a.sa) == float(rs1a)
    assert float(a.sb) == float(rs1b)
    assert a.v == None
    assert stm_getfield(a, 'x') == -611
    assert stm_getfield(a, 'c1') == '&'
    assert stm_getfield(a, 'c2') == '*'
    assert stm_getfield(a, 'c3') == '#'
    assert stm_getfield(a, 'l') == rll1
    assert stm_getfield(a, 'f') == rf1
    assert float(stm_getfield(a, 'sa')) == float(rs1a)
    assert float(stm_getfield(a, 'sb')) == float(rs1b)
    stm_setfield(a, 'x', 42 * a.y)
    stm_setfield(a, 'c1', '(')
    stm_setfield(a, 'c2', '?')
    stm_setfield(a, 'c3', ')')
    stm_setfield(a, 'l', rll2)
    stm_setfield(a, 'f', rf2)
    stm_setfield(a, 'sa', rs2a)
    stm_setfield(a, 'sb', rs2b)
    assert stm_getfield(a, 'x') == 42 * a.y
    assert stm_getfield(a, 'c1') == '('
    assert stm_getfield(a, 'c2') == '?'
    assert stm_getfield(a, 'c3') == ')'
    assert stm_getfield(a, 'l') == rll2
    assert stm_getfield(a, 'f') == rf2
    assert float(stm_getfield(a, 'sa')) == float(rs2a)
    assert float(stm_getfield(a, 'sb')) == float(rs2b)
    assert a.x == -611 # xxx still the old value when reading non-transact.
    assert a.c1 == '&'
    assert a.c2 == '*'
    assert a.c3 == '#'
    assert a.l == rll1
    assert a.f == rf1
    assert float(a.sa) == float(rs1a)
    assert float(a.sb) == float(rs1b)
    assert a.v == None
    if a.y < 10:
        a.y += 1    # non-transactionally
        stm_abort_and_retry()
    return lltype.nullptr(rffi.VOIDP.TO)

def test_stm_setfield():
    a = lltype.malloc(A, flavor='raw')
    a.x = -611
    a.c1 = '&'
    a.c2 = '*'
    a.c3 = '#'
    a.y = 0
    a.l = rll1
    a.f = rf1
    a.sa = rs1a
    a.sb = rs1b
    a.v = None
    stm_descriptor_init()
    stm_perform_transaction(llhelper(CALLBACK, callback2),
                        rffi.cast(rffi.VOIDP, a))
    stm_descriptor_done()
    assert a.x == 420
    assert a.c1 == '('
    assert a.c2 == '?'
    assert a.c3 == ')'
    assert a.l == rll2
    assert a.f == rf2
    assert float(a.sa) == float(rs2a)
    assert float(a.sb) == float(rs2b)
    assert a.v == None
    assert a.y == 10
    lltype.free(a, flavor='raw')
