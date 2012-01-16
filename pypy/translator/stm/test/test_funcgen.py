from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.rarithmetic import r_longlong, r_singlefloat
from pypy.translator.stm.test.test_transform import CompiledSTMTests
#from pypy.rlib import rstm
from pypy.translator.c.test.test_standalone import StandaloneTests
from pypy.rlib.debug import debug_print


class TestRStm(object):

    def compile(self, entry_point):
        from pypy.translator.translator import TranslationContext
        from pypy.annotation.listdef import s_list_of_strings
        from pypy.translator.c.genc import CStandaloneBuilder
        from pypy.translator.tool.cbuild import ExternalCompilationInfo
        t = TranslationContext()
        t.config.translation.gc = 'boehm'
        t.buildannotator().build_types(entry_point, [s_list_of_strings])
        t.buildrtyper().specialize()
        t.stm_transformation_applied = True   # not really, but for these tests
        cbuilder = CStandaloneBuilder(t, entry_point, t.config)
        force_debug = ExternalCompilationInfo(pre_include_bits=[
            "#define RPY_ASSERT 1\n"
            "#define RPY_LL_ASSERT 1\n"
            ])
        cbuilder.eci = cbuilder.eci.merge(force_debug)
        cbuilder.generate_source()
        cbuilder.compile()
        return t, cbuilder

    def test_compiled_stm_getfield(self):
        from pypy.translator.stm.test import test_llstm
        def entry_point(argv):
            test_llstm.test_stm_getfield()
            debug_print('ok!')
            return 0
        t, cbuilder = self.compile(entry_point)
        _, data = cbuilder.cmdexec('', err=True)
        assert data.endswith('ok!\n')

    def test_compiled_stm_setfield(self):
        from pypy.translator.stm.test import test_llstm
        def entry_point(argv):
            test_llstm.test_stm_setfield()
            debug_print('ok!')
            return 0
        t, cbuilder = self.compile(entry_point)
        _, data = cbuilder.cmdexec('', err=True)
        assert data.endswith('ok!\n')

# ____________________________________________________________

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

def change(array, newvalues):
    assert len(newvalues) <= len(array)
    for i in range(len(newvalues)):
        array[i] = rffi.cast(lltype.typeOf(array).TO.OF, newvalues[i])
change._annspecialcase_ = 'specialize:ll'

def do_stm_getarrayitem(argv):
    check(prebuilt_array_signed, [1, 10, -1, -10, 42])
    check(prebuilt_array_char,   [chr(1), chr(10), chr(255),
                                  chr(246), chr(42)])
    return 0

def do_stm_setarrayitem(argv):
    change(prebuilt_array_signed, [500000, -10000000, 3])
    check(prebuilt_array_signed,  [500000, -10000000, 3, -10, 42])
    prebuilt_array_char[0] = 'A'
    check(prebuilt_array_char,    ['A', chr(10), chr(255), chr(246), chr(42)])
    prebuilt_array_char[3] = 'B'
    check(prebuilt_array_char,    ['A', chr(10), chr(255), 'B', chr(42)])
    prebuilt_array_char[4] = 'C'
    check(prebuilt_array_char,    ['A', chr(10), chr(255), 'B', 'C'])
    #
    rstm.transaction_boundary()
    #
    check(prebuilt_array_char,    ['A', chr(10), chr(255), 'B', 'C'])
    prebuilt_array_char[1] = 'D'
    check(prebuilt_array_char,    ['A', 'D', chr(255), 'B', 'C'])
    prebuilt_array_char[2] = 'E'
    check(prebuilt_array_char,    ['A', 'D', 'E', 'B', 'C'])
    #
    rstm.transaction_boundary()
    #
    check(prebuilt_array_char,    ['A', 'D', 'E', 'B', 'C'])
    return 0


def make_array_of_structs(T1, T2):
    S = lltype.Struct('S', ('x', T1), ('y', T2))
    a = lltype.malloc(lltype.GcArray(S), 3, immortal=True)
    for i, (value1, value2) in enumerate([(1, 10), (-1, 20), (-50, -30)]):
        a[i].x = rffi.cast(T1, value1)
        a[i].y = rffi.cast(T2, value2)
    return a

prebuilt_array_signed_signed = make_array_of_structs(lltype.Signed,
                                                     lltype.Signed)
prebuilt_array_char_char = make_array_of_structs(lltype.Char,
                                                 lltype.Char)

def check2(array, expected1, expected2):
    assert len(array) == len(expected1) == len(expected2)
    for i in range(len(expected1)):
        assert array[i].x == expected1[i]
        assert array[i].y == expected2[i]
check2._annspecialcase_ = 'specialize:ll'

def change2(array, newvalues1, newvalues2):
    assert len(newvalues1) <= len(array)
    assert len(newvalues2) <= len(array)
    for i in range(len(newvalues1)):
        array[i].x = rffi.cast(lltype.typeOf(array).TO.OF.x, newvalues1[i])
    for i in range(len(newvalues2)):
        array[i].y = rffi.cast(lltype.typeOf(array).TO.OF.y, newvalues2[i])
change2._annspecialcase_ = 'specialize:ll'

def do_stm_getinteriorfield(argv):
    check2(prebuilt_array_signed_signed, [1, -1, -50], [10, 20, -30])
    check2(prebuilt_array_char_char, [chr(1), chr(255), chr(206)],
                                     [chr(10), chr(20), chr(226)])
    return 0

def do_stm_setinteriorfield(argv):
    change2(prebuilt_array_signed_signed, [500000, -10000000], [102101202])
    check2(prebuilt_array_signed_signed, [500000, -10000000, -50],
                                         [102101202, 20, -30])
    change2(prebuilt_array_char_char, ['a'], ['b'])
    check2(prebuilt_array_char_char, ['a', chr(255), chr(206)],
                                     ['b', chr(20), chr(226)])
    #
    rstm.transaction_boundary()
    #
    check2(prebuilt_array_signed_signed, [500000, -10000000, -50],
                                         [102101202, 20, -30])
    check2(prebuilt_array_char_char, ['a', chr(255), chr(206)],
                                     ['b', chr(20), chr(226)])
    return 0


# ____________________________________________________________


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

    def test_setarrayitem_all_sizes(self):
        t, cbuilder = self.compile(do_stm_setarrayitem)
        cbuilder.cmdexec('')

    def test_getinteriorfield_all_sizes(self):
        t, cbuilder = self.compile(do_stm_getinteriorfield)
        cbuilder.cmdexec('')

    def test_setinteriorfield_all_sizes(self):
        t, cbuilder = self.compile(do_stm_setinteriorfield)
        cbuilder.cmdexec('')
