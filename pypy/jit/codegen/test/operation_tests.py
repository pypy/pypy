from pypy.annotation import model as annmodel
from pypy.translator.translator import TranslationContext, graphof
from pypy.jit.codegen import graph2rgenop
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rlib.rarithmetic import r_uint, intmask, ovfcheck
from ctypes import cast, c_void_p, CFUNCTYPE, c_int, c_float
from pypy import conftest

class OperationTests(object):
    @staticmethod
    def _to_ctypes(t): #limited type support for now
        if t is float:
            return c_float
        return c_int

    def rgen(self, ll_function, argtypes, rettype=int): #XXX get rettype from annotation
        t = TranslationContext()
        t.buildannotator().build_types(ll_function, argtypes)
        t.buildrtyper().specialize()
        graph = graphof(t, ll_function)
        if conftest.option.view:
            graph.show()
        rgenop = self.RGenOp()
        self.rgenop = rgenop      # keep this alive!
        gv_generated = graph2rgenop.compile_graph(rgenop, graph)
        ctypestypes = [OperationTests._to_ctypes(t) for t in argtypes]
        fp = cast(c_void_p(gv_generated.value),
                  CFUNCTYPE(OperationTests._to_ctypes(rettype), *ctypestypes))
        return fp

    def test_arithmetic(self):
        for op in ['x + y',
                   'x - y',
                   'x * y',
                   'x // y',
                   'x % y',
                   'x << y',
                   'x >> y',
                   'x ^ y',
                   'x & y',
                   'x | y',
                   '-y',
                   '~y',
                   'abs(y)',
                   'abs(-x)',
                   # and now for aliasing issues:
                   'x + x',
                   'x - x',
                   'x * x',
                   'y // y',
                   'y % y',
                   'y << y',
                   'y >> y',
                   'x ^ x',
                   'x & x',
                   'x | x',
                   # and some constant cases:
                   '17 + x',
                   'x + (-21)',
                   '(-17) - x',
                   'x - 21',
                   # '*' see below
                   '101 // y',
                   '(-983) // y',
                   '2121 % y',
                   '(-69) % y',
                   # '// constant' and '% constant' see below
                   '(-934831) << y',
                   '111 << y',
                   'y << 0',
                   'y << 1',
                   'y << 31',
                   'y << 32',
                   'y << 45',
                   '(-934831) >> y',
                   '111 >> y',
                   'y >> 0',
                   'y >> 1',
                   'y >> 31',
                   'y >> 32',
                   'y >> 45',
                   '(-123) ^ x',
                   'x ^ 644',
                   '123 & x',
                   'x & (-77)',
                   '(-145) | x',
                   'x | 598',
                   ]:
            fn = eval("lambda x, y: %s" % (op,))
            fp = self.rgen(fn, [int, int])
            print op
            assert fp(40, 2) == intmask(fn(40, 2))
            assert fp(25, 3) == intmask(fn(25, 3))
            assert fp(149, 32) == intmask(fn(149, 32))
            assert fp(149, 33) == intmask(fn(149, 33))
            assert fp(149, 65) == intmask(fn(149, 65))
            assert fp(149, 150) == intmask(fn(149, 150))
            assert fp(-40, 2) == intmask(fn(-40, 2))
            assert fp(-25, 3) == intmask(fn(-25, 3))
            assert fp(-149, 32) == intmask(fn(-149, 32))
            assert fp(-149, 33) == intmask(fn(-149, 33))
            assert fp(-149, 65) == intmask(fn(-149, 65))
            assert fp(-149, 150) == intmask(fn(-149, 150))
            try:
                fn(40, -2)
            except ValueError:
                # the shift tests with negative y are invalid
                continue
            else:
                assert fp(40, -2) == intmask(fn(40, -2))
                assert fp(25, -3) == intmask(fn(25, -3))
                assert fp(149, -32) == intmask(fn(149, -32))
                assert fp(149, -33) == intmask(fn(149, -33))
                assert fp(149, -150) == intmask(fn(149, -150))
                assert fp(-40, -2) == intmask(fn(-40, -2))
                assert fp(-25, -3) == intmask(fn(-25, -3))
                assert fp(-149, -32) == intmask(fn(-149, -32))
                assert fp(-149, -33) == intmask(fn(-149, -33))
                assert fp(-149, -150) == intmask(fn(-149, -150))

    def test_comparison(self):
        for op, fn in [('int(x <  y)', lambda x, y: int(x <  y)),
                       ('int(x <= y)', lambda x, y: int(x <= y)),
                       ('int(x == y)', lambda x, y: int(x == y)),
                       ('int(x != y)', lambda x, y: int(x != y)),
                       ('int(x >  y)', lambda x, y: int(x >  y)),
                       ('int(x >= y)', lambda x, y: int(x >= y)),
                       ]:
            fp = self.rgen(fn, [int, int])
            assert fp(12, 11) == fn(12, 11), op
            assert fp(12, 12) == fn(12, 12), op
            assert fp(12, 13) == fn(12, 13), op
            assert fp(-12, 11) == fn(-12, 11), op
            assert fp(-12, 12) == fn(-12, 12), op
            assert fp(-12, 13) == fn(-12, 13), op
            assert fp(12, -11) == fn(12, -11), op
            assert fp(12, -12) == fn(12, -12), op
            assert fp(12, -13) == fn(12, -13), op
            assert fp(-12, -11) == fn(-12, -11), op
            assert fp(-12, -12) == fn(-12, -12), op
            assert fp(-12, -13) == fn(-12, -13), op

    def test_unsigned_comparison(self):
        for op, fn in [('int(x <  y)', lambda x, y: int(x <  y)),
                       ('int(x <= y)', lambda x, y: int(x <= y)),
                       ('int(x == y)', lambda x, y: int(x == y)),
                       ('int(x != y)', lambda x, y: int(x != y)),
                       ('int(x >  y)', lambda x, y: int(x >  y)),
                       ('int(x >= y)', lambda x, y: int(x >= y)),
                       ('int(12 <  y)', lambda x, y: int(12 <  y)),
                       ('int(12 <= y)', lambda x, y: int(12 <= y)),
                       ('int(12 == y)', lambda x, y: int(12 == y)),
                       ('int(12 != y)', lambda x, y: int(12 != y)),
                       ('int(12 >  y)', lambda x, y: int(12 >  y)),
                       ('int(12 >= y)', lambda x, y: int(12 >= y)),
                       ]:
            fp = self.rgen(fn, [r_uint, r_uint])
            print op
            assert fp(r_uint(12), r_uint(11)) == fn(r_uint(12), r_uint(11))
            assert fp(r_uint(12), r_uint(12)) == fn(r_uint(12), r_uint(12))
            assert fp(r_uint(12), r_uint(13)) == fn(r_uint(12), r_uint(13))
            assert fp(r_uint(-12), r_uint(11)) == fn(r_uint(-12), r_uint(11))
            assert fp(r_uint(-12), r_uint(12)) == fn(r_uint(-12), r_uint(12))
            assert fp(r_uint(-12), r_uint(13)) == fn(r_uint(-12), r_uint(13))
            assert fp(r_uint(12), r_uint(-11)) == fn(r_uint(12), r_uint(-11))
            assert fp(r_uint(12), r_uint(-12)) == fn(r_uint(12), r_uint(-12))
            assert fp(r_uint(12), r_uint(-13)) == fn(r_uint(12), r_uint(-13))
            assert fp(r_uint(-12), r_uint(-11)) == fn(r_uint(-12), r_uint(-11))
            assert fp(r_uint(-12), r_uint(-12)) == fn(r_uint(-12), r_uint(-12))
            assert fp(r_uint(-12), r_uint(-13)) == fn(r_uint(-12), r_uint(-13))

    def test_char_comparison(self):
        for op, fn in [('int(chr(x) <  chr(y))', lambda x, y: int(chr(x) <  chr(y))),
                       ('int(chr(x) <= chr(y))', lambda x, y: int(chr(x) <= chr(y))),
                       ('int(chr(x) == chr(y))', lambda x, y: int(chr(x) == chr(y))),
                       ('int(chr(x) != chr(y))', lambda x, y: int(chr(x) != chr(y))),
                       ('int(chr(x) >  chr(y))', lambda x, y: int(chr(x) >  chr(y))),
                       ('int(chr(x) >= chr(y))', lambda x, y: int(chr(x) >= chr(y))),
                       ]:
            fp = self.rgen(fn, [int, int])
            assert fp(12, 11) == fn(12, 11), op
            assert fp(12, 12) == fn(12, 12), op
            assert fp(12, 13) == fn(12, 13), op
            assert fp(182, 11) == fn(182, 11), op
            assert fp(182, 12) == fn(182, 12), op
            assert fp(182, 13) == fn(182, 13), op
            assert fp(12, 181) == fn(12, 181), op
            assert fp(12, 182) == fn(12, 182), op
            assert fp(12, 183) == fn(12, 183), op
            assert fp(182, 181) == fn(182, 181), op
            assert fp(182, 182) == fn(182, 182), op
            assert fp(182, 183) == fn(182, 183), op

    def test_unichar_comparison(self):
        for op, fn in [('int(unichr(x) == unichr(y))', lambda x, y: int(unichr(x) == unichr(y))),
                       ('int(unichr(x) != unichr(y))', lambda x, y: int(unichr(x) != unichr(y))),
                       ]:
            fp = self.rgen(fn, [int, int])
            assert fp(12, 11) == fn(12, 11), op
            assert fp(12, 12) == fn(12, 12), op
            assert fp(12, 13) == fn(12, 13), op
            assert fp(53182, 11) == fn(53182, 11), op
            assert fp(53182, 12) == fn(53182, 12), op
            assert fp(53182, 13) == fn(53182, 13), op
            assert fp(12, 53181) == fn(12, 53181), op
            assert fp(12, 53182) == fn(12, 53182), op
            assert fp(12, 53183) == fn(12, 53183), op
            assert fp(53182, 53181) == fn(53182, 53181), op
            assert fp(53182, 53182) == fn(53182, 53182), op
            assert fp(53182, 53183) == fn(53182, 53183), op

    def test_char_array(self):
        A = lltype.GcArray(lltype.Char)
        def fn(n):
            a = lltype.malloc(A, 5) #XXX this boils down to rgenop.genop_malloc_varsize() ?
            a[4] = 'H'
            a[3] = 'e'
            a[2] = 'l'
            a[1] = 'l'
            a[0] = 'o'
            return ord(a[n])
        fp = self.rgen(fn, [int])
        for i in range(5):
            assert fp(i) == fn(i)

    def test_char_varsize_array(self):
        A = lltype.GcArray(lltype.Char)
        def fn(n):
            a = lltype.malloc(A, n)
            a[4] = 'H'
            a[3] = 'e'
            a[2] = 'l'
            a[1] = 'l'
            a[0] = 'o'
            return ord(a[n-1])
        fp = self.rgen(fn, [int])
        assert fp(5) == fn(5)

    def test_unichar_array(self):
        A = lltype.GcArray(lltype.UniChar)
        def fn(n):
            a = lltype.malloc(A, 5)
            a[4] = u'H'
            a[3] = u'e'
            a[2] = u'l'
            a[1] = u'l'
            a[0] = u'o'
            return ord(a[n])
        fp = self.rgen(fn, [int])
        for i in range(5):
            assert fp(i) == fn(i)

    def test_char_unichar_fields(self):
        S = lltype.GcStruct('S', ('a', lltype.Char),
                                 ('b', lltype.Char),
                                 ('c', lltype.UniChar),
                                 ('d', lltype.UniChar),
                                 ('e', lltype.Signed))
        def fn():
            s = lltype.malloc(S)
            s.a = 'A'
            s.b = 'b'
            s.c = unichr(0x5a6b)
            s.d = unichr(0x7c8d)
            s.e = -1612
            return ((s.a == 'A') +
                    (s.b == 'b') +
                    (s.c == unichr(0x5a6b)) +
                    (s.d == unichr(0x7c8d)) +
                    (s.e == -1612))
        fp = self.rgen(fn, [])
        res = fp()
        assert res == 5

    def test_unsigned(self):
        for op, fn in [('x + y', lambda x, y: x + y),
                       ('x - y', lambda x, y: x - y),
                       ('x * y', lambda x, y: x * y),
                       ('x // y', lambda x, y: x // y),
                       ('x % y', lambda x, y: x % y),
                       ('x << y', lambda x, y: x << y),
                       ('x >> y', lambda x, y: x >> y),
                       ('x ^ y', lambda x, y: x ^ y),
                       ('x & y', lambda x, y: x & y),
                       ('x | y', lambda x, y: x | y),
                       ('-y', lambda x, y: -y),
                       ('~y', lambda x, y: ~y),
                       ]:
            fp = self.rgen(fn, [r_uint, r_uint])
            print op
            fn1 = lambda x, y: fn(r_uint(x), r_uint(y))
            fp1 = lambda x, y: r_uint(fp(x, y))
            assert fp1(40, 2) == fn1(40, 2)
            assert fp1(25, 3) == fn1(25, 3)
            assert fp1(40, 2) == fn1(40, 2)
            assert fp1(25, 3) == fn1(25, 3)
            assert fp1(149, 32) == fn1(149, 32)
            assert fp1(149, 33) == fn1(149, 33)
            assert fp1(149, 65) == fn1(149, 65)
            assert fp1(149, 150) == fn1(149, 150)
            big = r_uint(-42)
            assert fp1(big, 3) == fn1(big, 3)
            if op not in ('x << y', 'x >> y'):
                assert fp1(38, big) == fn1(38, big)
                assert fp1(big-5, big-12) == fn1(big-5, big-12)

    def test_float_arithmetic(self):
        for op, fn in [('x + y', lambda x, y: x + y),
                       ('x - y', lambda x, y: x - y),
                       ('x * y', lambda x, y: x * y),
                       ('x / y', lambda x, y: x / y),
                       #('x % y', lambda x, y: x % y),  #not used?
                       ('-y', lambda x, y: -y),
                       #('~y', lambda x, y: ~y),    #TypeError: bad operand type for unary ~
                       ('abs(y)', lambda x, y: abs(y)),
                       ('abs(-x)', lambda x, y: abs(-x)),
                       ]:
            fp = self.rgen(fn, [float, float], float)
            assert fp(40.0, 2.0) == fn(40.0, 2.0), op
            assert fp(25.125, 1.5) == fn(25.125, 1.5), op

    def test_float_cast(self): #because of different rettype
        for op, fn in [('bool(x)', lambda x: bool(x)),
                       ('bool(2.0 - x)', lambda x: bool(x - 2.0)),
                       ]:
            fp = self.rgen(fn, [float], bool)
            assert fp(6.0) == fn(6.0), op
            assert fp(2.0) == fn(2.0), op
            assert fp(0.0) == fn(0.0), op
            assert fp(-2.0) == fn(-2.0), op

    def test_constants_in_mul(self):
        for op in ['x * y', 'y * x']:
            for constant in range(-33, 34):
                fn = eval("lambda x: " + op, {'y': constant})
                fp = self.rgen(fn, [int], int)
                for operand1 in range(-33, 34):
                    res = fp(operand1)
                    assert res == eval(op, {'x': operand1, 'y': constant})
                fp = self.rgen(fn, [r_uint], r_uint)
                for operand1 in range(-33, 34):
                    res = r_uint(fp(r_uint(operand1)))
                    assert res == eval(op, {'x': r_uint(operand1),
                                            'y': r_uint(constant)})

    def test_constants_in_divmod(self):
        for op in ['x // y', 'x % y']:
            for constant in range(1, 20) + range(-1, -20, -1):
                fn = eval("lambda x: " + op, {'y': constant})
                fp = self.rgen(fn, [int], int)
                for operand1 in range(-32, 33):
                    res = fp(operand1)
                    assert res == eval(op, {'x': operand1, 'y': constant})
                fp = self.rgen(fn, [r_uint], r_uint)
                for operand1 in range(-32, 33):
                    res = r_uint(fp(r_uint(operand1)))
                    assert res == eval(op, {'x': r_uint(operand1),
                                            'y': r_uint(constant)})

    def test_ptr_comparison(self):
        S = lltype.GcStruct('S')
        T = lltype.GcStruct('T', ('s', lltype.Ptr(S)))

        def fn():
            s1 = lltype.malloc(S)
            s2 = lltype.malloc(S)
            return bool(s1) + bool(s2)*10 + (s1==s2)*100 + (s1!=s2)*1000
        fp = self.rgen(fn, [])
        assert fp() == 1011

        def fn():
            s1 = lltype.malloc(S)
            s2 = lltype.malloc(T).s    # null
            return bool(s1) + bool(s2)*10 + (s1==s2)*100 + (s1!=s2)*1000
        fp = self.rgen(fn, [])
        assert fp() == 1001

        def fn():
            s1 = lltype.malloc(S)
            s2 = s1
            return bool(s1) + bool(s2)*10 + (s1==s2)*100 + (s1!=s2)*1000
        fp = self.rgen(fn, [])
        assert fp() == 111

    def test_is_true(self):
        for op, fn in [('bool(x)', lambda x: bool(x)),
                       ('not x',   lambda x: llop.bool_not(lltype.Bool,
                                                           bool(x))),
                       ]:
            for typ in [int, r_uint, bool]:
                fp = self.rgen(fn, [typ], bool)
                assert fp(typ(12)) == fn(typ(12)), (op, typ)
                assert fp(typ(0))  == fn(typ(0)),  (op, typ)
                assert fp(typ(-1)) == fn(typ(-1)), (op, typ)
