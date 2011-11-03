from pypy.rpython.lltypesystem import lltype
from pypy.rlib.rarithmetic import r_longlong, r_singlefloat
from pypy.translator.stm.test.test_transform import CompiledSTMTests
from pypy.translator.stm import rstm


A = lltype.Struct('A', ('x', lltype.Signed), ('y', lltype.Signed),
                       ('c1', lltype.Char), ('c2', lltype.Char),
                       ('c3', lltype.Char), ('l', lltype.SignedLongLong),
                       ('f', lltype.Float), ('sa', lltype.SingleFloat),
                       ('sb', lltype.SingleFloat))
rll1 = r_longlong(-10000000000003)
rll2 = r_longlong(-300400500600700)
rf1 = -12.38976129
rf2 = 52.1029
rs1a = r_singlefloat(-0.598127)
rs2a = r_singlefloat(0.017634)
rs1b = r_singlefloat(40.121)
rs2b = r_singlefloat(-9e9)

def make_a_1():
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
    return a
make_a_1._dont_inline_ = True

def do_stm_getfield(argv):
    a = make_a_1()
    #
    assert a.x == -611
    assert a.c1 == '/'
    assert a.c2 == '\\'
    assert a.c3 == '!'
    assert a.y == 0
    assert a.l == rll1
    assert a.f == rf1
    assert float(a.sa) == float(rs1a)
    assert float(a.sb) == float(rs1b)
    #
    lltype.free(a, flavor='raw')
    return 0

def do_stm_setfield(argv):
    a = make_a_1()
    #
    a.x = 12871981
    a.c1 = '('
    assert a.c1 == '('
    assert a.c2 == '\\'
    assert a.c3 == '!'
    a.c2 = '?'
    assert a.c1 == '('
    assert a.c2 == '?'
    assert a.c3 == '!'
    a.c3 = ')'
    a.l = rll2
    a.f = rf2
    a.sa = rs2a
    a.sb = rs2b
    #
    assert a.x == 12871981
    assert a.c1 == '('
    assert a.c2 == '?'
    assert a.c3 == ')'
    assert a.l == rll2
    assert a.f == rf2
    assert float(a.sa) == float(rs2a)
    assert float(a.sb) == float(rs2b)
    #
    rstm.transaction_boundary()
    #
    assert a.x == 12871981
    assert a.c1 == '('
    assert a.c2 == '?'
    assert a.c3 == ')'
    assert a.l == rll2
    assert a.f == rf2
    assert float(a.sa) == float(rs2a)
    assert float(a.sb) == float(rs2b)
    #
    lltype.free(a, flavor='raw')
    return 0


class TestFuncGen(CompiledSTMTests):

    def test_getfield_all_sizes(self):
        t, cbuilder = self.compile(do_stm_getfield)
        cbuilder.cmdexec('')

    def test_setfield_all_sizes(self):
        t, cbuilder = self.compile(do_stm_setfield)
        cbuilder.cmdexec('')
