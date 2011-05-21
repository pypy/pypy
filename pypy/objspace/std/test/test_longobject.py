import py
import sys
from pypy.objspace.std import longobject as lobj
from pypy.objspace.std.multimethod import FailedToImplement
from pypy.interpreter.error import OperationError
from pypy.rlib.rarithmetic import r_uint
from pypy.rlib.rbigint import rbigint
from pypy.conftest import gettestobjspace

class TestW_LongObject:

    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.nofaking": True})

    def test_bigint_w(self):
        space = self.space
        fromlong = lobj.W_LongObject.fromlong
        assert isinstance(space.bigint_w(fromlong(42)), rbigint)
        assert space.bigint_w(fromlong(42)).eq(rbigint.fromint(42))
        assert space.bigint_w(fromlong(-1)).eq(rbigint.fromint(-1))
        w_obj = space.wrap("hello world")
        space.raises_w(space.w_TypeError, space.bigint_w, w_obj)
        w_obj = space.wrap(123.456)
        space.raises_w(space.w_TypeError, space.bigint_w, w_obj)

    def test_rint_variants(self):
        py.test.skip("XXX broken!")
        from pypy.rpython.tool.rfficache import platform
        space = self.space
        for r in platform.numbertype_to_rclass.values():
            if r is int:
                continue
            print r
            values = [0, -1, r.MASK>>1, -(r.MASK>>1)-1]
            for x in values:
                if not r.SIGNED:
                    x &= r.MASK
                w_obj = space.wrap(r(x))
                assert space.bigint_w(w_obj).eq(rbigint.fromint(x))


class AppTestLong:

    def test_trunc(self):
        import math
        assert math.trunc(1L) == 1L
        assert math.trunc(-1L) == -1L

    def test_add(self):
        x = 123L
        assert int(x + 12443L) == 123 + 12443
        x = -20
        assert x + 2 + 3L + True == -14L

    def test_sub(self):
        x = 58543L
        assert int(x - 12332L) == 58543 - 12332
        x = 237123838281233L
        assert x * 12 == x * 12L

    def test_mul(self):
        x = 363L
        assert x * 2 ** 40 == x << 40

    def test_truediv(self):
        exec "from __future__ import division; a = 31415926L / 10000000L"
        assert a == 3.1415926

    def test_floordiv(self):
        x = 31415926L
        a = x // 10000000L
        assert a == 3L

    def test_numerator_denominator(self):
        assert (1L).numerator == 1L
        assert (1L).denominator == 1L
        assert (42L).numerator == 42L
        assert (42L).denominator == 1L

    def test_compare(self):
        Z = 0
        ZL = 0L
        for BIG in (1L, 1L << 62, 1L << 9999):
            assert Z == ZL
            assert not (Z != ZL)
            assert ZL == Z
            assert not (ZL != Z)
            assert not (Z == BIG)
            assert Z != BIG
            assert not (BIG == Z)
            assert BIG != Z
            assert not (ZL == BIG)
            assert ZL != BIG
            assert Z <= ZL
            assert not (Z < ZL)
            assert Z <= BIG
            assert Z < BIG
            assert not (BIG <= Z)
            assert not (BIG < Z)
            assert ZL <= ZL
            assert not (ZL < ZL)
            assert ZL <= BIG
            assert ZL < BIG
            assert not (BIG <= ZL)
            assert not (BIG < ZL)
            assert not (Z <= -BIG)
            assert not (Z < -BIG)
            assert -BIG <= Z
            assert -BIG < Z
            assert not (ZL <= -BIG)
            assert not (ZL < -BIG)
            assert -BIG <= ZL
            assert -BIG < ZL
            #
            assert not (BIG <  int(BIG))
            assert     (BIG <= int(BIG))
            assert     (BIG == int(BIG))
            assert not (BIG != int(BIG))
            assert not (BIG >  int(BIG))
            assert     (BIG >= int(BIG))
            #
            assert     (BIG <  int(BIG)+1)
            assert     (BIG <= int(BIG)+1)
            assert not (BIG == int(BIG)+1)
            assert     (BIG != int(BIG)+1)
            assert not (BIG >  int(BIG)+1)
            assert not (BIG >= int(BIG)+1)
            #
            assert not (BIG <  int(BIG)-1)
            assert not (BIG <= int(BIG)-1)
            assert not (BIG == int(BIG)-1)
            assert     (BIG != int(BIG)-1)
            assert     (BIG >  int(BIG)-1)
            assert     (BIG >= int(BIG)-1)
            #
            assert not (int(BIG) <  BIG)
            assert     (int(BIG) <= BIG)
            assert     (int(BIG) == BIG)
            assert not (int(BIG) != BIG)
            assert not (int(BIG) >  BIG)
            assert     (int(BIG) >= BIG)
            #
            assert not (int(BIG)+1 <  BIG)
            assert not (int(BIG)+1 <= BIG)
            assert not (int(BIG)+1 == BIG)
            assert     (int(BIG)+1 != BIG)
            assert     (int(BIG)+1 >  BIG)
            assert     (int(BIG)+1 >= BIG)
            #
            assert     (int(BIG)-1 <  BIG)
            assert     (int(BIG)-1 <= BIG)
            assert not (int(BIG)-1 == BIG)
            assert     (int(BIG)-1 != BIG)
            assert not (int(BIG)-1 >  BIG)
            assert not (int(BIG)-1 >= BIG)

    def test_conversion(self):
        class long2(long):
            pass
        x = 1L
        x = long2(x<<100)
        y = int(x)
        assert type(y) == long
        assert type(+long2(5)) is long
        assert type(long2(5) << 0) is long
        assert type(long2(5) >> 0) is long
        assert type(long2(5) + 0) is long
        assert type(long2(5) - 0) is long
        assert type(long2(5) * 1) is long
        assert type(1 * long2(5)) is long
        assert type(0 + long2(5)) is long
        assert type(-long2(0)) is long
        assert type(long2(5) // 1) is long

    def test_pow(self):
        x = 0L
        assert pow(x, 0L, 1L) == 0L

    def test_getnewargs(self):
        assert  0L .__getnewargs__() == (0L,)
        assert  (-1L) .__getnewargs__() == (-1L,)

    def test_divmod(self):
        def check_division(x, y):
            q, r = divmod(x, y)
            pab, pba = x*y, y*x
            assert pab == pba
            assert q == x//y
            assert r == x%y
            assert x == q*y + r
            if y > 0:
                assert 0 <= r < y
            else:
                assert y < r <= 0
        for x in [-1L, 0L, 1L, 2L ** 100 - 1, -2L ** 100 - 1]:
            for y in [-105566530L, -1L, 1L, 1034522340L]:
                print "checking division for %s, %s" % (x, y)
                check_division(x, y)
        # special case from python tests:
        s1 = 33
        s2 = 2
        x = 16565645174462751485571442763871865344588923363439663038777355323778298703228675004033774331442052275771343018700586987657790981527457655176938756028872904152013524821759375058141439
        x >>= s1*16
        y = 10953035502453784575
        y >>= s2*16
        x = 0x3FE0003FFFFC0001FFFL
        y = 0x9800FFC1L
        check_division(x, y)
        raises(ZeroDivisionError, "x // 0L")

    def test_format(self):
        assert repr(12345678901234567890) == '12345678901234567890L'
        assert str(12345678901234567890) == '12345678901234567890'
        assert hex(0x1234567890ABCDEFL) == '0x1234567890abcdefL'
        assert oct(01234567012345670L) == '01234567012345670L'

    def test_bits(self):
        x = 0xAAAAAAAAL
        assert x | 0x55555555L == 0xFFFFFFFFL
        assert x & 0x55555555L == 0x00000000L
        assert x ^ 0x55555555L == 0xFFFFFFFFL
        assert -x | 0x55555555L == -0xAAAAAAA9L
        assert x | 0x555555555L == 0x5FFFFFFFFL
        assert x & 0x555555555L == 0x000000000L
        assert x ^ 0x555555555L == 0x5FFFFFFFFL

    def test_hash(self):
        # ints have the same hash as equal longs
        for i in range(-4, 14):
            assert hash(i) == hash(long(i))
        # might check too much -- it's ok to change the hashing algorithm
        assert hash(123456789L) == 123456789
        assert hash(1234567890123456789L) in (
            -1895067127,            # with 32-bit platforms
            1234567890123456789)    # with 64-bit platforms

    def test_math_log(self):
        import math
        raises(ValueError, math.log, 0L) 
        raises(ValueError, math.log, -1L) 
        raises(ValueError, math.log, -2L) 
        raises(ValueError, math.log, -(1L << 10000))
        #raises(ValueError, math.log, 0) 
        raises(ValueError, math.log, -1) 
        raises(ValueError, math.log, -2) 

    def test_long(self):
        import sys
        n = -sys.maxint-1
        assert long(n) == n
        assert str(long(n)) == str(n)

    def test_huge_longs(self):
        import operator
        x = 1L
        huge = x << 40000L
        raises(OverflowError, float, huge)
        raises(OverflowError, operator.truediv, huge, 3)
        raises(OverflowError, operator.truediv, huge, 3L)

    def test_just_trunc(self):
        class myint(object):
            def __trunc__(self):
                return 42
        assert long(myint()) == 42

    def test_override___long__(self):
        class mylong(long):
            def __long__(self):
                return 42L
        assert long(mylong(21)) == 42L
        class myotherlong(long):
            pass
        assert long(myotherlong(21)) == 21L

    def test___long__(self):
        class A(object):
            def __long__(self):
                return 42
        assert long(A()) == 42L
        class B(object):
            def __int__(self):
                return 42
        raises(TypeError, long, B())
        # but!: (blame CPython 2.7)
        class Integral(object):
            def __int__(self):
                return 42
        class TruncReturnsNonLong(object):
            def __trunc__(self):
                return Integral()
        assert long(TruncReturnsNonLong()) == 42

    def test_conjugate(self):
        assert (7L).conjugate() == 7L
        assert (-7L).conjugate() == -7L

        class L(long):
            pass

        assert type(L(7).conjugate()) is long

    def test_bit_length(self):
        assert 8L.bit_length() == 4
        assert (-1<<40).bit_length() == 41
        assert ((2**31)-1).bit_length() == 31


    def test_negative_zero(self):
        x = eval("-0L")
        assert x == 0L

    def test_mix_int_and_long(self):
        class IntLongMixClass(object):
            def __int__(self):
                return 42L

            def __long__(self):
                return 64

        mixIntAndLong = IntLongMixClass()
        as_long = long(mixIntAndLong)
        assert type(as_long) is long
        assert as_long == 64

    def test_long_real(self):
        class A(long): pass
        b = A(5).real
        assert type(b) is long
