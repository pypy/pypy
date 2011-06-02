from pypy.objspace.std import floatobject as fobj
from pypy.objspace.std.multimethod import FailedToImplement
import py, sys

class TestW_FloatObject:

    def test_pow_fff(self):
        x = 10.0
        y = 2.0
        z = 13.0
        f1 = fobj.W_FloatObject(x)
        f2 = fobj.W_FloatObject(y)
        f3 = fobj.W_FloatObject(z)
        self.space.raises_w(self.space.w_TypeError,
                            fobj.pow__Float_Float_ANY,
                            self.space, f1, f2, f3)

    def test_pow_ffn(self):
        x = 10.0
        y = 2.0
        f1 = fobj.W_FloatObject(x)
        f2 = fobj.W_FloatObject(y)
        v = fobj.pow__Float_Float_ANY(self.space, f1, f2, self.space.w_None)
        assert v.floatval == x ** y
        f1 = fobj.W_FloatObject(-1.23)
        f2 = fobj.W_FloatObject(-4.56)
        self.space.raises_w(self.space.w_ValueError,
                            fobj.pow__Float_Float_ANY,
                            self.space, f1, f2,
                            self.space.w_None)
        x = -10
        y = 2.0
        f1 = fobj.W_FloatObject(x)
        f2 = fobj.W_FloatObject(y)
        v = fobj.pow__Float_Float_ANY(self.space, f1, f2, self.space.w_None)
        assert v.floatval == x**y

    def test_dont_use_long_impl(self):
        from pypy.objspace.std.longobject import W_LongObject
        space = self.space
        saved = W_LongObject.__dict__['fromfloat']
        W_LongObject.fromfloat = lambda space, x: disabled
        try:
            w_i = space.wrap(12)
            w_f = space.wrap(12.3)
            assert space.unwrap(space.eq(w_f, w_i)) is False
            assert space.unwrap(space.eq(w_i, w_f)) is False
            assert space.unwrap(space.ne(w_f, w_i)) is True
            assert space.unwrap(space.ne(w_i, w_f)) is True
            assert space.unwrap(space.lt(w_f, w_i)) is False
            assert space.unwrap(space.lt(w_i, w_f)) is True
            assert space.unwrap(space.le(w_f, w_i)) is False
            assert space.unwrap(space.le(w_i, w_f)) is True
            assert space.unwrap(space.gt(w_f, w_i)) is True
            assert space.unwrap(space.gt(w_i, w_f)) is False
            assert space.unwrap(space.ge(w_f, w_i)) is True
            assert space.unwrap(space.ge(w_i, w_f)) is False
        finally:
            W_LongObject.fromfloat = saved


class AppTestAppFloatTest:
    def setup_class(cls):
        cls.w_py26 = cls.space.wrap(sys.version_info >= (2, 6))

    def test_conjugate(self):
        assert (1.).conjugate() == 1.
        assert (-1.).conjugate() == -1.

        class F(float):
            pass
        assert F(1.).conjugate() == 1.

    def test_negatives(self):
        assert -1.1 < 0
        assert -0.1 < 0

    def test_float_callable(self):
        assert 0.125 == float(0.125)

    def test_float_int(self):
        assert 42.0 == float(42)

    def test_float_hash(self):
        # these are taken from standard Python, which produces
        # the same but for -1.
        import math
        assert hash(42.0) == 42
        assert hash(42.125) == 1413677056
        assert hash(math.ldexp(0.125, 1000)) in (
            32,              # answer on 32-bit machines
            137438953472)    # answer on 64-bit machines
        # testing special overflow values
        inf = 1e200 * 1e200
        assert hash(inf) == 314159
        assert hash(-inf) == -271828
        assert hash(inf/inf) == 0

    def test_int_float(self):
        assert int(42.1234) == 42
        assert int(4e10) == 40000000000L

        raises(OverflowError, int, float('inf'))
        raises(OverflowError, long, float('inf'))
        raises(ValueError, int, float('nan'))
        raises(ValueError, long, float('nan'))

    def test_float_string(self):
        assert 42 == float("42")
        assert 42.25 == float("42.25")
        inf = 1e200*1e200
        assert float("inf")  == inf
        assert float("+inf") == inf
        assert float("-INf") == -inf
        assert str(inf) == "inf"
        assert str(-inf) == "-inf"
        assert str(float("infinity")) == 'inf'
        assert str(float("+infinity")) == 'inf'
        assert str(float("-infinity")) == '-inf'
        assert str(float("nan")) == "nan"
        assert str(float("-nAn")) == "nan"
        assert repr(inf) == "inf"
        assert repr(-inf) == "-inf"
        assert repr(float("nan")) == "nan"
        assert repr(float("+nan")) == "nan"
        assert repr(float("-nAn")) == "nan"

    def test_float_unicode(self):
        # u00A0 and u2000 are some kind of spaces
        assert 42.75 == float(unichr(0x00A0)+unicode("42.75")+unichr(0x2000))
        class FloatUnicode(unicode):
            def __float__(self):
                return float(unicode(self)) + 1
        assert float(FloatUnicode("8")) == 9.0

    def test_float_long(self):
        assert 42.0 == float(42L)
        assert 10000000000.0 == float(10000000000L)
        raises(OverflowError, float, 10**400)

    def test_as_integer_ratio(self):
        for f, ratio in [
                (0.875, (7, 8)),
                (-0.875, (-7, 8)),
                (0.0, (0, 1)),
                (11.5, (23, 2)),
            ]:
            assert f.as_integer_ratio() == ratio

        raises(OverflowError, float('inf').as_integer_ratio)
        raises(OverflowError, float('-inf').as_integer_ratio)
        raises(ValueError, float('nan').as_integer_ratio)

    def test_float_conversion(self):
        class X(float):
            def __float__(self):
                return 42.
        assert float(X()) == 42.

    def test_round(self):
        import math
        assert 1.0 == round(1.0)
        assert 1.0 == round(1.1)
        assert 2.0 == round(1.9)
        assert 2.0 == round(1.5)
        assert -2.0 == round(-1.5)
        assert -2.0 == round(-1.5)
        assert -2.0 == round(-1.5, 0)
        assert -2.0 == round(-1.5, 0)
        assert 22.2 == round(22.222222, 1)
        assert 20.0 == round(22.22222, -1)
        assert 0.0 == round(22.22222, -2)
        #
        assert round(123.456, -308) == 0.0
        assert round(123.456, -700) == 0.0
        assert round(123.456, -2**100) == 0.0
        assert math.copysign(1., round(-123.456, -700)) == -1.

    def test_special_float_method(self):
        class a(object):
            def __float__(self):
                self.ar = True
                return None
        inst = a()
        raises(TypeError, float, inst)
        assert inst.ar

        class b(object):
            pass
        raises((AttributeError, TypeError), float, b())

    def test_getnewargs(self):
        assert  0.0 .__getnewargs__() == (0.0,)

    def test_pow(self):
        import math

        def pw(x, y):
            return x ** y
        def espeq(x, y):
            return not abs(x-y) > 1e05
        raises(ZeroDivisionError, pw, 0.0, -1)
        assert pw(0, 0.5) == 0.0
        assert espeq(pw(4.0, 0.5), 2.0)
        assert pw(4.0, 0) == 1.0
        assert pw(-4.0, 0) == 1.0
        raises(ValueError, pw, -1.0, 0.5)
        assert pw(-1.0, 2.0) == 1.0
        assert pw(-1.0, 3.0) == -1.0
        assert pw(-1.0, 1e200) == 1.0
        if self.py26:
            assert pw(0.0, float("-inf")) == float("inf")
            assert math.isnan(pw(-3, float("nan")))
            assert math.isnan(pw(-3., float("nan")))
            assert pw(-1.0, -float('inf')) == 1.0
            assert pw(-1.0, float('inf')) == 1.0
            assert pw(float('inf'), 0) == 1.0
            assert pw(float('nan'), 0) == 1.0

            assert math.isinf(pw(-0.5, float('-inf')))
            assert math.isinf(pw(+0.5, float('-inf')))
            assert pw(-1.5, float('-inf')) == 0.0
            assert pw(+1.5, float('-inf')) == 0.0

            assert str(pw(float('-inf'), -0.5)) == '0.0'
            assert str(pw(float('-inf'), -2.0)) == '0.0'
            assert str(pw(float('-inf'), -1.0)) == '-0.0'
            assert str(pw(float('-inf'), 1.0)) == '-inf'
            assert str(pw(float('-inf'), 2.0)) == 'inf'

    def test_pow_neg_base(self):
        import math
        def pw(x, y):
            return x ** y
        assert pw(-2.0, 2.0) == 4
        res = pw(-2.0, -2001.0)
        assert res == -0.0
        assert math.copysign(1., res) == -1.
        assert pw(-1.0, -1e15) == 1.0

    def test_float_cmp(self):
        assert 12.5 == 12.5
        assert 12.5 != -3.2
        assert 12.5 < 123.4
        assert .25 <= .25
        assert -5744.23 <= -51.2
        assert 4.3 > 2.3
        assert 0.01 >= -0.01
        # float+long
        verylonglong = 10L**400
        infinite = 1e200*1e200
        assert 12.0 == 12L
        assert 1e300 == long(1e300)
        assert 12.1 != 12L
        assert infinite != 123456789L
        assert 12.9 < 13L
        assert -infinite < -13L
        assert 12.9 <= 13L
        assert 13.0 <= 13L
        assert 13.01 > 13L
        assert 13.0 >= 13L
        assert 13.01 >= 13L
        assert 12.0 == 12
        assert 12.1 != 12
        assert infinite != 123456789
        assert 12.9 < 13
        assert -infinite < -13
        assert 12.9 <= 13
        assert 13.0 <= 13
        assert 13.01 > 13
        assert 13.0 >= 13
        assert 13.01 >= 13
        assert infinite > verylonglong
        assert infinite >= verylonglong
        assert 1234.56 < verylonglong
        assert 1234.56 <= verylonglong
        # long+float
        assert 12L == 12.0
        assert long(1e300) == 1e300
        assert 12L != 12.1
        assert 123456789L != infinite
        assert 13L > 12.9
        assert -13L > -infinite
        assert 13L >= 12.9
        assert 13L >= 13.0
        assert 13L < 13.01
        assert 13L <= 13.0
        assert 13L <= 13.01
        assert verylonglong < infinite
        assert verylonglong <= infinite
        assert verylonglong > 1234.56
        assert verylonglong >= 1234.56
        assert 13 >= 12.9
        assert 13 >= 13.0
        assert 13 < 13.01
        assert 13 <= 13.0
        assert 13 <= 13.01

    def test_comparison_more(self):
        import sys
        is_pypy = '__pypy__' in sys.builtin_module_names
        infinity = 1e200*1e200
        nan = infinity/infinity
        for x in (123, 1 << 30,
                  (1 << 33) - 1, 1 << 33, (1 << 33) + 1,
                  1 << 62, 1 << 70):
            #
            assert     (x == float(x))
            assert     (x >= float(x))
            assert     (x <= float(x))
            assert not (x != float(x))
            assert not (x >  float(x))
            assert not (x <  float(x))
            #
            assert not ((x - 1) == float(x))
            assert not ((x - 1) >= float(x))
            assert     ((x - 1) <= float(x))
            assert     ((x - 1) != float(x))
            assert not ((x - 1) >  float(x))
            assert     ((x - 1) <  float(x))
            #
            assert not ((x + 1) == float(x))
            assert     ((x + 1) >= float(x))
            assert not ((x + 1) <= float(x))
            assert     ((x + 1) != float(x))
            assert     ((x + 1) >  float(x))
            assert not ((x + 1) <  float(x))
            #
            assert not (x == infinity)
            assert not (x >= infinity)
            assert     (x <= infinity)
            assert     (x != infinity)
            assert not (x >  infinity)
            assert     (x <  infinity)
            #
            assert not (x == -infinity)
            assert     (x >= -infinity)
            assert not (x <= -infinity)
            assert     (x != -infinity)
            assert     (x >  -infinity)
            assert not (x <  -infinity)
            #
            if is_pypy:
                assert not (x == nan)
                assert not (x >= nan)
                assert not (x <= nan)
                assert     (x != nan)
                assert not (x >  nan)
                assert not (x <  nan)
            #
            assert     (float(x) == x)
            assert     (float(x) <= x)
            assert     (float(x) >= x)
            assert not (float(x) != x)
            assert not (float(x) <  x)
            assert not (float(x) >  x)
            #
            assert not (float(x) == (x - 1))
            assert not (float(x) <= (x - 1))
            assert     (float(x) >= (x - 1))
            assert     (float(x) != (x - 1))
            assert not (float(x) <  (x - 1))
            assert     (float(x) >  (x - 1))
            #
            assert not (float(x) == (x + 1))
            assert     (float(x) <= (x + 1))
            assert not (float(x) >= (x + 1))
            assert     (float(x) != (x + 1))
            assert     (float(x) <  (x + 1))
            assert not (float(x) >  (x + 1))
            #
            assert not (infinity == x)
            assert     (infinity >= x)
            assert not (infinity <= x)
            assert     (infinity != x)
            assert     (infinity >  x)
            assert not (infinity <  x)
            #
            assert not (-infinity == x)
            assert not (-infinity >= x)
            assert     (-infinity <= x)
            assert     (-infinity != x)
            assert not (-infinity >  x)
            assert     (-infinity <  x)
            #
            if is_pypy:
                assert not (nan == x)
                assert not (nan <= x)
                assert not (nan >= x)
                assert     (nan != x)
                assert not (nan <  x)
                assert not (nan >  x)

    def test___getformat__(self):
        assert float.__getformat__("float") != "unknown"
        assert float.__getformat__("double") != "unknown"
        raises(ValueError, float.__getformat__, "random")

    def test_trunc(self):
        import math
        assert math.trunc(1.5) == 1
        assert math.trunc(-1.5) == -1
        assert math.trunc(1.999999) == 1
        assert math.trunc(-1.999999) == -1
        assert math.trunc(-0.999999) == -0
        assert math.trunc(-100.999) == -100
        raises(OverflowError, math.trunc, float("inf"))


    def test_multimethod_slice(self):
        assert 5 .__add__(3.14) is NotImplemented
        assert 3.25 .__add__(5) == 8.25
        # xxx we are also a bit inconsistent about the following
        #if hasattr(int, '__eq__'):  # for py.test -A: CPython is inconsistent
        #    assert 5 .__eq__(3.14) is NotImplemented
        #    assert 3.14 .__eq__(5) is False
        #if hasattr(long, '__eq__'):  # for py.test -A: CPython is inconsistent
        #    assert 5L .__eq__(3.14) is NotImplemented
        #    assert 3.14 .__eq__(5L) is False

    def test_from_string(self):
        raises(ValueError, float, "\0")

    def test_format(self):
        f = 1.1234e200
        assert f.__format__("G") == "1.1234E+200"

    def test_float_real(self):
        class A(float): pass
        b = A(5).real
        assert type(b) is float


class AppTestFloatHex:
    def w_identical(self, x, y):
        import math
        # check that floats x and y are identical, or that both
        # are NaNs
        if math.isnan(x) or math.isnan(y):
            if math.isnan(x) == math.isnan(y):
                return
        assert (x == y and (x != 0.0 or
                            math.copysign(1.0, x) == math.copysign(1.0, y)))

    def test_from_hex(self):
        fromHex = float.fromhex
        import sys
        INF = float("inf")
        NAN = float("nan")
        MIN = sys.float_info.min
        MAX = sys.float_info.max
        TINY = fromHex('0x0.0000000000001p-1022') # min subnormal
        EPS = sys.float_info.epsilon

        # two spellings of infinity, with optional signs; case-insensitive
        self.identical(fromHex('inf'), INF)
        self.identical(fromHex('+Inf'), INF)
        self.identical(fromHex('-INF'), -INF)
        self.identical(fromHex('iNf'), INF)
        self.identical(fromHex('Infinity'), INF)
        self.identical(fromHex('+INFINITY'), INF)
        self.identical(fromHex('-infinity'), -INF)
        self.identical(fromHex('-iNFiNitY'), -INF)

        # nans with optional sign; case insensitive
        self.identical(fromHex('nan'), NAN)
        self.identical(fromHex('+NaN'), NAN)
        self.identical(fromHex('-NaN'), NAN)
        self.identical(fromHex('-nAN'), NAN)

        # variations in input format
        self.identical(fromHex('1'), 1.0)
        self.identical(fromHex('+1'), 1.0)
        self.identical(fromHex('1.'), 1.0)
        self.identical(fromHex('1.0'), 1.0)
        self.identical(fromHex('1.0p0'), 1.0)
        self.identical(fromHex('01'), 1.0)
        self.identical(fromHex('01.'), 1.0)
        self.identical(fromHex('0x1'), 1.0)
        self.identical(fromHex('0x1.'), 1.0)
        self.identical(fromHex('0x1.0'), 1.0)
        self.identical(fromHex('+0x1.0'), 1.0)
        self.identical(fromHex('0x1p0'), 1.0)
        self.identical(fromHex('0X1p0'), 1.0)
        self.identical(fromHex('0X1P0'), 1.0)
        self.identical(fromHex('0x1P0'), 1.0)
        self.identical(fromHex('0x1.p0'), 1.0)
        self.identical(fromHex('0x1.0p0'), 1.0)
        self.identical(fromHex('0x.1p4'), 1.0)
        self.identical(fromHex('0x.1p04'), 1.0)
        self.identical(fromHex('0x.1p004'), 1.0)
        self.identical(fromHex('0x1p+0'), 1.0)
        self.identical(fromHex('0x1P-0'), 1.0)
        self.identical(fromHex('+0x1p0'), 1.0)
        self.identical(fromHex('0x01p0'), 1.0)
        self.identical(fromHex('0x1p00'), 1.0)
        self.identical(fromHex(u'0x1p0'), 1.0)
        self.identical(fromHex(' 0x1p0 '), 1.0)
        self.identical(fromHex('\n 0x1p0'), 1.0)
        self.identical(fromHex('0x1p0 \t'), 1.0)
        self.identical(fromHex('0xap0'), 10.0)
        self.identical(fromHex('0xAp0'), 10.0)
        self.identical(fromHex('0xaP0'), 10.0)
        self.identical(fromHex('0xAP0'), 10.0)
        self.identical(fromHex('0xbep0'), 190.0)
        self.identical(fromHex('0xBep0'), 190.0)
        self.identical(fromHex('0xbEp0'), 190.0)
        self.identical(fromHex('0XBE0P-4'), 190.0)
        self.identical(fromHex('0xBEp0'), 190.0)
        self.identical(fromHex('0xB.Ep4'), 190.0)
        self.identical(fromHex('0x.BEp8'), 190.0)
        self.identical(fromHex('0x.0BEp12'), 190.0)

        # moving the point around
        pi = fromHex('0x1.921fb54442d18p1')
        self.identical(fromHex('0x.006487ed5110b46p11'), pi)
        self.identical(fromHex('0x.00c90fdaa22168cp10'), pi)
        self.identical(fromHex('0x.01921fb54442d18p9'), pi)
        self.identical(fromHex('0x.03243f6a8885a3p8'), pi)
        self.identical(fromHex('0x.06487ed5110b46p7'), pi)
        self.identical(fromHex('0x.0c90fdaa22168cp6'), pi)
        self.identical(fromHex('0x.1921fb54442d18p5'), pi)
        self.identical(fromHex('0x.3243f6a8885a3p4'), pi)
        self.identical(fromHex('0x.6487ed5110b46p3'), pi)
        self.identical(fromHex('0x.c90fdaa22168cp2'), pi)
        self.identical(fromHex('0x1.921fb54442d18p1'), pi)
        self.identical(fromHex('0x3.243f6a8885a3p0'), pi)
        self.identical(fromHex('0x6.487ed5110b46p-1'), pi)
        self.identical(fromHex('0xc.90fdaa22168cp-2'), pi)
        self.identical(fromHex('0x19.21fb54442d18p-3'), pi)
        self.identical(fromHex('0x32.43f6a8885a3p-4'), pi)
        self.identical(fromHex('0x64.87ed5110b46p-5'), pi)
        self.identical(fromHex('0xc9.0fdaa22168cp-6'), pi)
        self.identical(fromHex('0x192.1fb54442d18p-7'), pi)
        self.identical(fromHex('0x324.3f6a8885a3p-8'), pi)
        self.identical(fromHex('0x648.7ed5110b46p-9'), pi)
        self.identical(fromHex('0xc90.fdaa22168cp-10'), pi)
        self.identical(fromHex('0x1921.fb54442d18p-11'), pi)
        # ...
        self.identical(fromHex('0x1921fb54442d1.8p-47'), pi)
        self.identical(fromHex('0x3243f6a8885a3p-48'), pi)
        self.identical(fromHex('0x6487ed5110b46p-49'), pi)
        self.identical(fromHex('0xc90fdaa22168cp-50'), pi)
        self.identical(fromHex('0x1921fb54442d18p-51'), pi)
        self.identical(fromHex('0x3243f6a8885a30p-52'), pi)
        self.identical(fromHex('0x6487ed5110b460p-53'), pi)
        self.identical(fromHex('0xc90fdaa22168c0p-54'), pi)
        self.identical(fromHex('0x1921fb54442d180p-55'), pi)


        # results that should overflow...
        raises(OverflowError, fromHex, '-0x1p1024')
        raises(OverflowError, fromHex, '0x1p+1025')
        raises(OverflowError, fromHex, '+0X1p1030')
        raises(OverflowError, fromHex, '-0x1p+1100')
        raises(OverflowError, fromHex, '0X1p123456789123456789')
        raises(OverflowError, fromHex, '+0X.8p+1025')
        raises(OverflowError, fromHex, '+0x0.8p1025')
        raises(OverflowError, fromHex, '-0x0.4p1026')
        raises(OverflowError, fromHex, '0X2p+1023')
        raises(OverflowError, fromHex, '0x2.p1023')
        raises(OverflowError, fromHex, '-0x2.0p+1023')
        raises(OverflowError, fromHex, '+0X4p+1022')
        raises(OverflowError, fromHex, '0x1.ffffffffffffffp+1023')
        raises(OverflowError, fromHex, '-0X1.fffffffffffff9p1023')
        raises(OverflowError, fromHex, '0X1.fffffffffffff8p1023')
        raises(OverflowError, fromHex, '+0x3.fffffffffffffp1022')
        raises(OverflowError, fromHex, '0x3fffffffffffffp+970')
        raises(OverflowError, fromHex, '0x10000000000000000p960')
        raises(OverflowError, fromHex, '-0Xffffffffffffffffp960')

        # ...and those that round to +-max float
        self.identical(fromHex('+0x1.fffffffffffffp+1023'), MAX)
        self.identical(fromHex('-0X1.fffffffffffff7p1023'), -MAX)
        self.identical(fromHex('0X1.fffffffffffff7fffffffffffffp1023'), MAX)

        # zeros
        self.identical(fromHex('0x0p0'), 0.0)
        self.identical(fromHex('0x0p1000'), 0.0)
        self.identical(fromHex('-0x0p1023'), -0.0)
        self.identical(fromHex('0X0p1024'), 0.0)
        self.identical(fromHex('-0x0p1025'), -0.0)
        self.identical(fromHex('0X0p2000'), 0.0)
        self.identical(fromHex('0x0p123456789123456789'), 0.0)
        self.identical(fromHex('-0X0p-0'), -0.0)
        self.identical(fromHex('-0X0p-1000'), -0.0)
        self.identical(fromHex('0x0p-1023'), 0.0)
        self.identical(fromHex('-0X0p-1024'), -0.0)
        self.identical(fromHex('-0x0p-1025'), -0.0)
        self.identical(fromHex('-0x0p-1072'), -0.0)
        self.identical(fromHex('0X0p-1073'), 0.0)
        self.identical(fromHex('-0x0p-1074'), -0.0)
        self.identical(fromHex('0x0p-1075'), 0.0)
        self.identical(fromHex('0X0p-1076'), 0.0)
        self.identical(fromHex('-0X0p-2000'), -0.0)
        self.identical(fromHex('-0x0p-123456789123456789'), -0.0)
        self.identical(fromHex('0x1.0p00000000000000000000000000000003'), 8.0)
        self.identical(fromHex('0x1.0p+0000000000000000000000000000003'), 8.0)
        self.identical(fromHex('0x1.0p-000000000000000000000000000003'), 0.125)

        # values that should underflow to 0
        self.identical(fromHex('0X1p-1075'), 0.0)
        self.identical(fromHex('-0X1p-1075'), -0.0)
        self.identical(fromHex('-0x1p-123456789123456789'), -0.0)
        self.identical(fromHex('0x1.00000000000000001p-1075'), TINY)
        self.identical(fromHex('-0x1.1p-1075'), -TINY)
        self.identical(fromHex('0x1.fffffffffffffffffp-1075'), TINY)

        # check round-half-even is working correctly near 0 ...
        self.identical(fromHex('0x1p-1076'), 0.0)
        self.identical(fromHex('0X2p-1076'), 0.0)
        self.identical(fromHex('0X3p-1076'), TINY)
        self.identical(fromHex('0x4p-1076'), TINY)
        self.identical(fromHex('0X5p-1076'), TINY)
        self.identical(fromHex('0X6p-1076'), 2*TINY)
        self.identical(fromHex('0x7p-1076'), 2*TINY)
        self.identical(fromHex('0X8p-1076'), 2*TINY)
        self.identical(fromHex('0X9p-1076'), 2*TINY)
        self.identical(fromHex('0xap-1076'), 2*TINY)
        self.identical(fromHex('0Xbp-1076'), 3*TINY)
        self.identical(fromHex('0xcp-1076'), 3*TINY)
        self.identical(fromHex('0Xdp-1076'), 3*TINY)
        self.identical(fromHex('0Xep-1076'), 4*TINY)
        self.identical(fromHex('0xfp-1076'), 4*TINY)
        self.identical(fromHex('0x10p-1076'), 4*TINY)
        self.identical(fromHex('-0x1p-1076'), -0.0)
        self.identical(fromHex('-0X2p-1076'), -0.0)
        self.identical(fromHex('-0x3p-1076'), -TINY)
        self.identical(fromHex('-0X4p-1076'), -TINY)
        self.identical(fromHex('-0x5p-1076'), -TINY)
        self.identical(fromHex('-0x6p-1076'), -2*TINY)
        self.identical(fromHex('-0X7p-1076'), -2*TINY)
        self.identical(fromHex('-0X8p-1076'), -2*TINY)
        self.identical(fromHex('-0X9p-1076'), -2*TINY)
        self.identical(fromHex('-0Xap-1076'), -2*TINY)
        self.identical(fromHex('-0xbp-1076'), -3*TINY)
        self.identical(fromHex('-0xcp-1076'), -3*TINY)
        self.identical(fromHex('-0Xdp-1076'), -3*TINY)
        self.identical(fromHex('-0xep-1076'), -4*TINY)
        self.identical(fromHex('-0Xfp-1076'), -4*TINY)
        self.identical(fromHex('-0X10p-1076'), -4*TINY)

        # ... and near MIN ...
        self.identical(fromHex('0x0.ffffffffffffd6p-1022'), MIN-3*TINY)
        self.identical(fromHex('0x0.ffffffffffffd8p-1022'), MIN-2*TINY)
        self.identical(fromHex('0x0.ffffffffffffdap-1022'), MIN-2*TINY)
        self.identical(fromHex('0x0.ffffffffffffdcp-1022'), MIN-2*TINY)
        self.identical(fromHex('0x0.ffffffffffffdep-1022'), MIN-2*TINY)
        self.identical(fromHex('0x0.ffffffffffffe0p-1022'), MIN-2*TINY)
        self.identical(fromHex('0x0.ffffffffffffe2p-1022'), MIN-2*TINY)
        self.identical(fromHex('0x0.ffffffffffffe4p-1022'), MIN-2*TINY)
        self.identical(fromHex('0x0.ffffffffffffe6p-1022'), MIN-2*TINY)
        self.identical(fromHex('0x0.ffffffffffffe8p-1022'), MIN-2*TINY)
        self.identical(fromHex('0x0.ffffffffffffeap-1022'), MIN-TINY)
        self.identical(fromHex('0x0.ffffffffffffecp-1022'), MIN-TINY)
        self.identical(fromHex('0x0.ffffffffffffeep-1022'), MIN-TINY)
        self.identical(fromHex('0x0.fffffffffffff0p-1022'), MIN-TINY)
        self.identical(fromHex('0x0.fffffffffffff2p-1022'), MIN-TINY)
        self.identical(fromHex('0x0.fffffffffffff4p-1022'), MIN-TINY)
        self.identical(fromHex('0x0.fffffffffffff6p-1022'), MIN-TINY)
        self.identical(fromHex('0x0.fffffffffffff8p-1022'), MIN)
        self.identical(fromHex('0x0.fffffffffffffap-1022'), MIN)
        self.identical(fromHex('0x0.fffffffffffffcp-1022'), MIN)
        self.identical(fromHex('0x0.fffffffffffffep-1022'), MIN)
        self.identical(fromHex('0x1.00000000000000p-1022'), MIN)
        self.identical(fromHex('0x1.00000000000002p-1022'), MIN)
        self.identical(fromHex('0x1.00000000000004p-1022'), MIN)
        self.identical(fromHex('0x1.00000000000006p-1022'), MIN)
        self.identical(fromHex('0x1.00000000000008p-1022'), MIN)
        self.identical(fromHex('0x1.0000000000000ap-1022'), MIN+TINY)
        self.identical(fromHex('0x1.0000000000000cp-1022'), MIN+TINY)
        self.identical(fromHex('0x1.0000000000000ep-1022'), MIN+TINY)
        self.identical(fromHex('0x1.00000000000010p-1022'), MIN+TINY)
        self.identical(fromHex('0x1.00000000000012p-1022'), MIN+TINY)
        self.identical(fromHex('0x1.00000000000014p-1022'), MIN+TINY)
        self.identical(fromHex('0x1.00000000000016p-1022'), MIN+TINY)
        self.identical(fromHex('0x1.00000000000018p-1022'), MIN+2*TINY)

        # ... and near 1.0.
        self.identical(fromHex('0x0.fffffffffffff0p0'), 1.0-EPS)
        self.identical(fromHex('0x0.fffffffffffff1p0'), 1.0-EPS)
        self.identical(fromHex('0X0.fffffffffffff2p0'), 1.0-EPS)
        self.identical(fromHex('0x0.fffffffffffff3p0'), 1.0-EPS)
        self.identical(fromHex('0X0.fffffffffffff4p0'), 1.0-EPS)
        self.identical(fromHex('0X0.fffffffffffff5p0'), 1.0-EPS/2)
        self.identical(fromHex('0X0.fffffffffffff6p0'), 1.0-EPS/2)
        self.identical(fromHex('0x0.fffffffffffff7p0'), 1.0-EPS/2)
        self.identical(fromHex('0x0.fffffffffffff8p0'), 1.0-EPS/2)
        self.identical(fromHex('0X0.fffffffffffff9p0'), 1.0-EPS/2)
        self.identical(fromHex('0X0.fffffffffffffap0'), 1.0-EPS/2)
        self.identical(fromHex('0x0.fffffffffffffbp0'), 1.0-EPS/2)
        self.identical(fromHex('0X0.fffffffffffffcp0'), 1.0)
        self.identical(fromHex('0x0.fffffffffffffdp0'), 1.0)
        self.identical(fromHex('0X0.fffffffffffffep0'), 1.0)
        self.identical(fromHex('0x0.ffffffffffffffp0'), 1.0)
        self.identical(fromHex('0X1.00000000000000p0'), 1.0)
        self.identical(fromHex('0X1.00000000000001p0'), 1.0)
        self.identical(fromHex('0x1.00000000000002p0'), 1.0)
        self.identical(fromHex('0X1.00000000000003p0'), 1.0)
        self.identical(fromHex('0x1.00000000000004p0'), 1.0)
        self.identical(fromHex('0X1.00000000000005p0'), 1.0)
        self.identical(fromHex('0X1.00000000000006p0'), 1.0)
        self.identical(fromHex('0X1.00000000000007p0'), 1.0)
        self.identical(fromHex('0x1.00000000000007ffffffffffffffffffffp0'),
                       1.0)
        self.identical(fromHex('0x1.00000000000008p0'), 1.0)
        self.identical(fromHex('0x1.00000000000008000000000000000001p0'),
                       1+EPS)
        self.identical(fromHex('0X1.00000000000009p0'), 1.0+EPS)
        self.identical(fromHex('0x1.0000000000000ap0'), 1.0+EPS)
        self.identical(fromHex('0x1.0000000000000bp0'), 1.0+EPS)
        self.identical(fromHex('0X1.0000000000000cp0'), 1.0+EPS)
        self.identical(fromHex('0x1.0000000000000dp0'), 1.0+EPS)
        self.identical(fromHex('0x1.0000000000000ep0'), 1.0+EPS)
        self.identical(fromHex('0X1.0000000000000fp0'), 1.0+EPS)
        self.identical(fromHex('0x1.00000000000010p0'), 1.0+EPS)
        self.identical(fromHex('0X1.00000000000011p0'), 1.0+EPS)
        self.identical(fromHex('0x1.00000000000012p0'), 1.0+EPS)
        self.identical(fromHex('0X1.00000000000013p0'), 1.0+EPS)
        self.identical(fromHex('0X1.00000000000014p0'), 1.0+EPS)
        self.identical(fromHex('0x1.00000000000015p0'), 1.0+EPS)
        self.identical(fromHex('0x1.00000000000016p0'), 1.0+EPS)
        self.identical(fromHex('0X1.00000000000017p0'), 1.0+EPS)
        self.identical(fromHex('0x1.00000000000017ffffffffffffffffffffp0'),
                       1.0+EPS)
        self.identical(fromHex('0x1.00000000000018p0'), 1.0+2*EPS)
        self.identical(fromHex('0X1.00000000000018000000000000000001p0'),
                       1.0+2*EPS)
        self.identical(fromHex('0x1.00000000000019p0'), 1.0+2*EPS)
        self.identical(fromHex('0X1.0000000000001ap0'), 1.0+2*EPS)
        self.identical(fromHex('0X1.0000000000001bp0'), 1.0+2*EPS)
        self.identical(fromHex('0x1.0000000000001cp0'), 1.0+2*EPS)
        self.identical(fromHex('0x1.0000000000001dp0'), 1.0+2*EPS)
        self.identical(fromHex('0x1.0000000000001ep0'), 1.0+2*EPS)
        self.identical(fromHex('0X1.0000000000001fp0'), 1.0+2*EPS)
        self.identical(fromHex('0x1.00000000000020p0'), 1.0+2*EPS)

    def test_roundtrip(self):
        def roundtrip(x):
            return float.fromhex(x.hex())
        import sys
        import math
        TINY = float.fromhex('0x0.0000000000001p-1022') # min subnormal

        for x in [float("nan"), float("inf"), sys.float_info.max,
                  sys.float_info.min, sys.float_info.min-TINY, TINY, 0.0]:
            self.identical(x, roundtrip(x))
            self.identical(-x, roundtrip(-x))

        # fromHex(toHex(x)) should exactly recover x, for any non-NaN float x.
        import random
        for i in xrange(500):
            e = random.randrange(-1200, 1200)
            m = random.random()
            s = random.choice([1.0, -1.0])
            try:
                x = s*math.ldexp(m, e)
            except OverflowError:
                pass
            else:
                self.identical(x, float.fromhex(x.hex()))

    def test_invalid(self):
        raises(ValueError, float.fromhex, "0P")
