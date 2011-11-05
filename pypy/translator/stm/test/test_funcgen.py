from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.rarithmetic import r_longlong, r_singlefloat
from pypy.translator.stm.test.test_transform import CompiledSTMTests
from pypy.translator.stm import rstm


A = lltype.GcStruct('A', ('x', lltype.Signed), ('y', lltype.Signed),
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
    a = lltype.malloc(A, immortal=True)
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
a_prebuilt = make_a_1()

def do_stm_getfield(argv):
    a = a_prebuilt
    assert a.x == -611
    assert a.c1 == '/'
    assert a.c2 == '\\'
    assert a.c3 == '!'
    assert a.y == 0
    assert a.l == rll1
    assert a.f == rf1
    assert float(a.sa) == float(rs1a)
    assert float(a.sb) == float(rs1b)
    return 0

def do_stm_setfield(argv):
    a = a_prebuilt
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
    return 0


def make_array(OF):
    a = lltype.malloc(lltype.GcArray(OF), 5, immortal=True)
    for i, value in enumerate([1, 10, -1, -10, 42]):
        a[i] = rffi.cast(OF, value)
    return a

prebuilt_array_signed = make_array(lltype.Signed)
prebuilt_array_char   = make_array(lltype.Char)

def check(array, expected):
    assert len(array) == len(expected)
    for i in range(len(expected)):
        assert array[i] == expected[i]
check._annspecialcase_ = 'specialize:ll'

def do_stm_getarrayitem(argv):
    check(prebuilt_array_signed, [1, 10, -1, -10, 42])
    check(prebuilt_array_char,   [chr(1), chr(10), chr(255),
                                  chr(246), chr(42)])
    return 0


class TestFuncGen(CompiledSTMTests):

    def test_getfield_all_sizes(self):
        t, cbuilder = self.compile(do_stm_getfield)
        cbuilder.cmdexec('')

    def test_setfield_all_sizes(self):
        t, cbuilder = self.compile(do_stm_setfield)
        cbuilder.cmdexec('')

    def test_getarrayitem_all_sizes(self):
        t, cbuilder = self.compile(do_stm_getarrayitem)
        cbuilder.cmdexec('')
