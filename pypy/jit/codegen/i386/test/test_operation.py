import py
from pypy.rlib.objectmodel import specialize
from pypy.annotation import model as annmodel
from pypy.rpython.lltypesystem import lltype
from pypy.translator.translator import TranslationContext, graphof
from pypy.jit.codegen import graph2rgenop
from pypy.jit.codegen.i386.rgenop import RI386GenOp
from pypy.rpython.memory.lltypelayout import convert_offset_to_int
from pypy.rlib.rarithmetic import r_uint
from ctypes import cast, c_void_p, CFUNCTYPE, c_int


class RGenOpPacked(RI386GenOp):
    """Like RI386GenOp, but produces concrete offsets in the tokens
    instead of llmemory.offsets.  These numbers may not agree with
    your C compiler's.
    """

    @staticmethod
    @specialize.memo()
    def fieldToken(T, name):
        return convert_offset_to_int(RI386GenOp.fieldToken(T, name))

    @staticmethod
    @specialize.memo()
    def arrayToken(A):
        return tuple(map(convert_offset_to_int, RI386GenOp.arrayToken(A)))

    @staticmethod
    @specialize.memo()
    def allocToken(T):
        return convert_offset_to_int(RI386GenOp.allocToken(T))

    @staticmethod
    @specialize.memo()
    def varsizeAllocToken(A):
        return tuple(map(convert_offset_to_int,
                         RI386GenOp.varsizeAllocToken(A)))


class TestBasic:

    def rgen(self, ll_function, argtypes):
        t = TranslationContext()
        t.buildannotator().build_types(ll_function, argtypes)
        t.buildrtyper().specialize()
        graph = graphof(t, ll_function)
        rgenop = RGenOpPacked()
        self.rgenop = rgenop      # keep this alive!
        gv_generated = graph2rgenop.compile_graph(rgenop, graph)
        ctypestypes = [c_int] * len(argtypes)   # for now
        fp = cast(c_void_p(gv_generated.value), CFUNCTYPE(c_int, *ctypestypes))
        return fp

    def test_arithmetic(self):
        for fn in [lambda x, y: x + y,
                   lambda x, y: x - y,
                   lambda x, y: x * y,
                   lambda x, y: x // y,
                   lambda x, y: x % y,
                   lambda x, y: x << y,
                   lambda x, y: x >> y,
                   lambda x, y: x ^ y,
                   lambda x, y: x & y,
                   lambda x, y: x | y,
                   lambda x, y: -y,
                   lambda x, y: ~y,
                   lambda x, y: abs(y),
                   lambda x, y: abs(-x),
                   ]:
            fp = self.rgen(fn, [int, int])
            assert fp(40, 2) == fn(40, 2)
            assert fp(25, 3) == fn(25, 3)

    def test_comparison(self):
        for fn in [lambda x, y: int(x <  y),
                   lambda x, y: int(x <= y),
                   lambda x, y: int(x == y),
                   lambda x, y: int(x != y),
                   lambda x, y: int(x >  y),
                   lambda x, y: int(x >= y),
                   ]:
            fp = self.rgen(fn, [int, int])
            assert fp(12, 11) == fn(12, 11)
            assert fp(12, 12) == fn(12, 12)
            assert fp(12, 13) == fn(12, 13)
            assert fp(-12, 11) == fn(-12, 11)
            assert fp(-12, 12) == fn(-12, 12)
            assert fp(-12, 13) == fn(-12, 13)
            assert fp(12, -11) == fn(12, -11)
            assert fp(12, -12) == fn(12, -12)
            assert fp(12, -13) == fn(12, -13)
            assert fp(-12, -11) == fn(-12, -11)
            assert fp(-12, -12) == fn(-12, -12)
            assert fp(-12, -13) == fn(-12, -13)

    def test_char_comparison(self):
        for fn in [lambda x, y: int(chr(x) <  chr(y)),
                   lambda x, y: int(chr(x) <= chr(y)),
                   lambda x, y: int(chr(x) == chr(y)),
                   lambda x, y: int(chr(x) != chr(y)),
                   lambda x, y: int(chr(x) >  chr(y)),
                   lambda x, y: int(chr(x) >= chr(y)),
                   ]:
            fp = self.rgen(fn, [int, int])
            assert fp(12, 11) == fn(12, 11)
            assert fp(12, 12) == fn(12, 12)
            assert fp(12, 13) == fn(12, 13)
            assert fp(182, 11) == fn(182, 11)
            assert fp(182, 12) == fn(182, 12)
            assert fp(182, 13) == fn(182, 13)
            assert fp(12, 181) == fn(12, 181)
            assert fp(12, 182) == fn(12, 182)
            assert fp(12, 183) == fn(12, 183)
            assert fp(182, 181) == fn(182, 181)
            assert fp(182, 182) == fn(182, 182)
            assert fp(182, 183) == fn(182, 183)

    def test_unichar_comparison(self):
        for fn in [lambda x, y: int(unichr(x) == unichr(y)),
                   lambda x, y: int(unichr(x) != unichr(y)),
                   ]:
            fp = self.rgen(fn, [int, int])
            assert fp(12, 11) == fn(12, 11)
            assert fp(12, 12) == fn(12, 12)
            assert fp(12, 13) == fn(12, 13)
            assert fp(53182, 11) == fn(53182, 11)
            assert fp(53182, 12) == fn(53182, 12)
            assert fp(53182, 13) == fn(53182, 13)
            assert fp(12, 53181) == fn(12, 53181)
            assert fp(12, 53182) == fn(12, 53182)
            assert fp(12, 53183) == fn(12, 53183)
            assert fp(53182, 53181) == fn(53182, 53181)
            assert fp(53182, 53182) == fn(53182, 53182)
            assert fp(53182, 53183) == fn(53182, 53183)

    def test_char_array(self):
        A = lltype.GcArray(lltype.Char)
        def fn(n):
            a = lltype.malloc(A, 5)
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

    def test_unsigned(self):
        for fn in [lambda x, y: x + y,
                   lambda x, y: x - y,
                   lambda x, y: x * y,
                   lambda x, y: x // y,
                   lambda x, y: x % y,
                   lambda x, y: x << y,
                   lambda x, y: x >> y,
                   lambda x, y: x ^ y,
                   lambda x, y: x & y,
                   lambda x, y: x | y,
                   lambda x, y: -y,
                   lambda x, y: ~y,
                   ]:
            fp = self.rgen(fn, [r_uint, r_uint])
            assert fp(40, 2) == fn(40, 2)
            assert fp(25, 3) == fn(25, 3)

    def test_float_arithmetic(self):
        py.test.skip("floats in codegen/i386")
        for fn in [lambda x, y: bool(y),
                   lambda x, y: bool(y - 2.0),
                   lambda x, y: x + y,
                   lambda x, y: x - y,
                   lambda x, y: x * y,
                   lambda x, y: x / y,
                   #lambda x, y: x % y,     not used?
                   lambda x, y: x ** y,
                   lambda x, y: -y,
                   lambda x, y: ~y,
                   lambda x, y: abs(y),
                   lambda x, y: abs(-x),
                   ]:
            fp = self.rgen(fn, [float, float])
            assert fp(40.0, 2.0) == fn(40.0, 2.0)
            assert fp(25.125, 1.5) == fn(25.125, 1.5)
