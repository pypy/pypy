from __future__ import division
import py
import operator, sys
from random import random, randint, sample
from pypy.rlib.rbigint import rbigint, SHIFT, MASK, KARATSUBA_CUTOFF
from pypy.rlib import rbigint as lobj
from pypy.rlib.rarithmetic import r_uint, r_longlong, r_ulonglong, intmask
from pypy.rpython.test.test_llinterp import interpret

class TestRLong(object):
    def test_simple(self):
        for op1 in [-2, -1, 0, 1, 2, 50]:
            for op2 in [-2, -1, 0, 1, 2, 50]:
                rl_op1 = rbigint.fromint(op1)
                rl_op2 = rbigint.fromint(op2)
                for op in "add sub mul".split():
                    r1 = getattr(rl_op1, op)(rl_op2)
                    r2 = getattr(operator, op)(op1, op2)
                    assert r1.tolong() == r2
            
    def test_floordiv(self):
        for op1 in [-12, -2, -1, 1, 2, 50]:
            for op2 in [-4, -2, -1, 1, 2, 8]:
                rl_op1 = rbigint.fromint(op1)
                rl_op2 = rbigint.fromint(op2)
                r1 = rl_op1.floordiv(rl_op2)
                r2 = op1 // op2
                assert r1.tolong() == r2

    def test_truediv(self):
        for op1 in [-12, -2, -1, 1, 2, 50]:
            for op2 in [-4, -2, -1, 1, 2, 8]:
                rl_op1 = rbigint.fromint(op1)
                rl_op2 = rbigint.fromint(op2)
                r1 = rl_op1.truediv(rl_op2)
                r2 = op1 / op2
                assert r1 == r2

    def test_mod(self):
        for op1 in [-50, -12, -2, -1, 1, 2, 50, 52]:
            for op2 in [-4, -2, -1, 1, 2, 8]:
                rl_op1 = rbigint.fromint(op1)
                rl_op2 = rbigint.fromint(op2)
                r1 = rl_op1.mod(rl_op2)
                r2 = op1 % op2
                assert r1.tolong() == r2

    def test_pow(self):
        for op1 in [-50, -12, -2, -1, 1, 2, 50, 52]:
            for op2 in [0, 1, 2, 8, 9, 10, 11]:
                rl_op1 = rbigint.fromint(op1)
                rl_op2 = rbigint.fromint(op2)
                r1 = rl_op1.pow(rl_op2)
                r2 = op1 ** op2
                assert r1.tolong() == r2

    def test_touint(self):
        import sys
        from pypy.rlib.rarithmetic import r_uint
        result = r_uint(sys.maxint + 42)
        rl = rbigint.fromint(sys.maxint).add(rbigint.fromint(42))
        assert rl.touint() == result

def gen_signs(l):
    for s in l:
        if s == 0:
            yield s
        else:
            yield s
            yield -s


class Test_rbigint(object):

    def test_args_from_long(self):
        BASE = 1 << SHIFT
        assert rbigint.fromlong(0).eq(rbigint([0], 0))
        assert rbigint.fromlong(17).eq(rbigint([17], 1))
        assert rbigint.fromlong(BASE-1).eq(rbigint([intmask(BASE-1)], 1))
        assert rbigint.fromlong(BASE).eq(rbigint([0, 1], 1))
        assert rbigint.fromlong(BASE**2).eq(rbigint([0, 0, 1], 1))
        assert rbigint.fromlong(-17).eq(rbigint([17], -1))
        assert rbigint.fromlong(-(BASE-1)).eq(rbigint([intmask(BASE-1)], -1))
        assert rbigint.fromlong(-BASE).eq(rbigint([0, 1], -1))
        assert rbigint.fromlong(-(BASE**2)).eq(rbigint([0, 0, 1], -1))
#        assert rbigint.fromlong(-sys.maxint-1).eq(
#            rbigint.digits_for_most_neg_long(-sys.maxint-1), -1)

    def test_args_from_int(self):
        BASE = 1 << SHIFT
        assert rbigint.fromrarith_int(0).eq(rbigint([0], 0))
        assert rbigint.fromrarith_int(17).eq(rbigint([17], 1))
        assert rbigint.fromrarith_int(BASE-1).eq(rbigint([intmask(BASE-1)], 1))
        assert rbigint.fromrarith_int(BASE).eq(rbigint([0, 1], 1))
        assert rbigint.fromrarith_int(BASE**2).eq(rbigint([0, 0, 1], 1))
        assert rbigint.fromrarith_int(-17).eq(rbigint([17], -1))
        assert rbigint.fromrarith_int(-(BASE-1)).eq(rbigint([intmask(BASE-1)], -1))
        assert rbigint.fromrarith_int(-BASE).eq(rbigint([0, 1], -1))
        assert rbigint.fromrarith_int(-(BASE**2)).eq(rbigint([0, 0, 1], -1))
#        assert rbigint.fromrarith_int(-sys.maxint-1).eq((
#            rbigint.digits_for_most_neg_long(-sys.maxint-1), -1)

    def test_args_from_uint(self):
        BASE = 1 << SHIFT
        assert rbigint.fromrarith_int(r_uint(0)).eq(rbigint([0], 0))
        assert rbigint.fromrarith_int(r_uint(17)).eq(rbigint([17], 1))
        assert rbigint.fromrarith_int(r_uint(BASE-1)).eq(rbigint([intmask(BASE-1)], 1))
        assert rbigint.fromrarith_int(r_uint(BASE)).eq(rbigint([0, 1], 1))
        assert rbigint.fromrarith_int(r_uint(BASE**2)).eq(rbigint([0], 0))
        assert rbigint.fromrarith_int(r_uint(sys.maxint)).eq(
            rbigint.fromint(sys.maxint))
        assert rbigint.fromrarith_int(r_uint(sys.maxint+1)).eq(
            rbigint.fromlong(sys.maxint+1))
        assert rbigint.fromrarith_int(r_uint(2*sys.maxint+1)).eq(
            rbigint.fromlong(2*sys.maxint+1))

    def test_add(self):
        x = 123456789123456789000000L
        y = 123858582373821923936744221L
        for i in [-1, 1]:
            for j in [-1, 1]:
                f1 = rbigint.fromlong(x * i)
                f2 = rbigint.fromlong(y * j)
                result = f1.add(f2)
                assert result.tolong() == x * i + y * j

    def test_sub(self):
        x = 12378959520302182384345L
        y = 88961284756491823819191823L
        for i in [-1, 1]:
            for j in [-1, 1]:
                f1 = rbigint.fromlong(x * i)
                f2 = rbigint.fromlong(y * j)
                result = f1.sub(f2)
                assert result.tolong() == x * i - y * j

    def test_subzz(self):
        w_l0 = rbigint.fromint(0)
        assert w_l0.sub(w_l0).tolong() == 0

    def test_mul(self):
        x = -1238585838347L
        y = 585839391919233L
        f1 = rbigint.fromlong(x)
        f2 = rbigint.fromlong(y)
        result = f1.mul(f2)
        assert result.tolong() == x * y
        # also test a * a, it has special code
        result = f1.mul(f1)
        assert result.tolong() == x * x

    def test_tofloat(self):
        x = 12345678901234567890L ** 10
        f1 = rbigint.fromlong(x)
        d = f1.tofloat()
        assert d == float(x)
        x = x ** 100
        f1 = rbigint.fromlong(x)
        assert raises(OverflowError, f1.tofloat)
        f2 = rbigint([0, 2097152], 1)
        d = f2.tofloat()
        assert d == float(2097152 << SHIFT)

    def test_fromfloat(self):
        x = 1234567890.1234567890
        f1 = rbigint.fromfloat(x)
        y = f1.tofloat()
        assert f1.tolong() == long(x)
        # check overflow
        #x = 12345.6789e10000000000000000000000000000
        # XXX don't use such consts. marshal doesn't handle them right.
        x = 12345.6789e200
        x *= x
        assert raises(OverflowError, rbigint.fromfloat, x)

    def test_eq(self):
        x = 5858393919192332223L
        y = 585839391919233111223311112332L
        f1 = rbigint.fromlong(x)
        f2 = rbigint.fromlong(-x)
        f3 = rbigint.fromlong(y)
        assert f1.eq(f1)
        assert f2.eq(f2)
        assert f3.eq(f3)
        assert not f1.eq(f2)
        assert not f1.eq(f3)

    def test_lt(self):
        val = [0, 0x111111111111, 0x111111111112, 0x111111111112FFFF]
        for x in gen_signs(val):
            for y in gen_signs(val):
                f1 = rbigint.fromlong(x)
                f2 = rbigint.fromlong(y)
                assert (x < y) ==  f1.lt(f2)

    def test_int_conversion(self):
        f1 = rbigint.fromlong(12332)
        f2 = rbigint.fromint(12332)
        assert f2.tolong() == f1.tolong()
        assert f2.toint()
        assert rbigint.fromlong(42).tolong() == 42
        assert rbigint.fromlong(-42).tolong() == -42

        u = f2.touint()
        assert u == 12332
        assert type(u) is r_uint

    def test_conversions(self):
        for v in (0, 1, -1, sys.maxint, -sys.maxint-1):
            assert rbigint.fromlong(long(v)).tolong() == long(v)
            l = rbigint.fromint(v)
            assert l.toint() == v
            if v >= 0:
                u = l.touint()
                assert u == v
                assert type(u) is r_uint
            else:
                py.test.raises(ValueError, l.touint)

        toobig_lv1 = rbigint.fromlong(sys.maxint+1)
        assert toobig_lv1.tolong() == sys.maxint+1
        toobig_lv2 = rbigint.fromlong(sys.maxint+2)
        assert toobig_lv2.tolong() == sys.maxint+2
        toobig_lv3 = rbigint.fromlong(-sys.maxint-2)
        assert toobig_lv3.tolong() == -sys.maxint-2

        for lv in (toobig_lv1, toobig_lv2, toobig_lv3):
            py.test.raises(OverflowError, lv.toint)

        lmaxuint = rbigint.fromlong(2*sys.maxint+1)
        toobig_lv4 = rbigint.fromlong(2*sys.maxint+2)

        u = lmaxuint.touint()
        assert u == 2*sys.maxint+1

        py.test.raises(ValueError, toobig_lv3.touint)
        py.test.raises(OverflowError, toobig_lv4.touint)


    def test_pow_lll(self):
        x = 10L
        y = 2L
        z = 13L
        f1 = rbigint.fromlong(x)
        f2 = rbigint.fromlong(y)
        f3 = rbigint.fromlong(z)
        v = f1.pow(f2, f3)
        assert v.tolong() == pow(x, y, z)
        f1, f2, f3 = [rbigint.fromlong(i)
                      for i in (10L, -1L, 42L)]
        py.test.raises(TypeError, f1.pow, f2, f3)
        f1, f2, f3 = [rbigint.fromlong(i)
                      for i in (10L, 5L, 0L)]
        py.test.raises(ValueError, f1.pow, f2, f3)

    def test_pow_lln(self):
        x = 10L
        y = 2L
        f1 = rbigint.fromlong(x)
        f2 = rbigint.fromlong(y)
        v = f1.pow(f2)
        assert v.tolong() == x ** y

    def test_normalize(self):
        f1 = rbigint([1, 0], 1)
        f1._normalize()
        assert len(f1.digits) == 1
        f0 = rbigint([0], 0)
        assert f1.sub(f1).eq(f0)

    def test_invert(self):
        x = 3 ** 40
        f1 = rbigint.fromlong(x)
        f2 = rbigint.fromlong(-x)
        r1 = f1.invert()
        r2 = f2.invert()
        assert r1.tolong() == -(x + 1)
        assert r2.tolong() == -(-x + 1)

    def test_shift(self):
        negative = -23
        for x in gen_signs([3L ** 30L, 5L ** 20L, 7 ** 300, 0L, 1L]):
            f1 = rbigint.fromlong(x)
            py.test.raises(ValueError, f1.lshift, negative)
            py.test.raises(ValueError, f1.rshift, negative)
            for y in [0L, 1L, 32L, 2304L, 11233L, 3 ** 9]:
                res1 = f1.lshift(int(y)).tolong()
                res2 = f1.rshift(int(y)).tolong()
                assert res1 == x << y
                assert res2 == x >> y

    def test_bitwise(self):
        for x in gen_signs([0, 1, 5, 11, 42, 43, 3 ** 30]):
            for y in gen_signs([0, 1, 5, 11, 42, 43, 3 ** 30, 3 ** 31]):
                lx = rbigint.fromlong(x)
                ly = rbigint.fromlong(y)
                for mod in "xor and_ or_".split():
                    res1 = getattr(lx, mod)(ly).tolong()
                    res2 = getattr(operator, mod)(x, y)
                    assert res1 == res2

    def test_tostring(self):
        z = rbigint.fromlong(0)
        assert z.str() == '0'
        assert z.repr() == '0L'
        assert z.hex() == '0x0L'
        assert z.oct() == '0L'
        x = rbigint.fromlong(-18471379832321)
        assert x.str() == '-18471379832321'
        assert x.repr() == '-18471379832321L'
        assert x.hex() == '-0x10ccb4088e01L'
        assert x.oct() == '-0414626402107001L'
        assert x.format('.!') == (
            '-!....!!..!!..!.!!.!......!...!...!!!........!')
        assert x.format('abcdefghijkl', '<<', '>>') == '-<<cakdkgdijffjf>>'


class TestInternalFunctions(object):
    def test__inplace_divrem1(self):
        # signs are not handled in the helpers!
        for x, y in [(1238585838347L, 3), (1234123412311231L, 1231231), (99, 100)]:
            f1 = rbigint.fromlong(x)
            f2 = y
            remainder = lobj._inplace_divrem1(f1, f1, f2)
            assert (f1.tolong(), remainder) == divmod(x, y)
        out = rbigint([99, 99], 1)
        remainder = lobj._inplace_divrem1(out, out, 100)

    def test__divrem1(self):
        # signs are not handled in the helpers!
        x = 1238585838347L
        y = 3
        f1 = rbigint.fromlong(x)
        f2 = y
        div, rem = lobj._divrem1(f1, f2)
        assert (div.tolong(), rem) == divmod(x, y)

    def test__muladd1(self):
        x = 1238585838347L
        y = 3
        z = 42
        f1 = rbigint.fromlong(x)
        f2 = y
        f3 = z
        prod = lobj._muladd1(f1, f2, f3)
        assert prod.tolong() == x * y + z

    def test__x_divrem(self):
        x = 12345678901234567890L
        for i in range(100):
            y = long(randint(0, 1 << 30))
            y <<= 30
            y += randint(0, 1 << 30)
            f1 = rbigint.fromlong(x)
            f2 = rbigint.fromlong(y)
            div, rem = lobj._x_divrem(f1, f2)
            assert div.tolong(), rem.tolong() == divmod(x, y)

    def test__divrem(self):
        x = 12345678901234567890L
        for i in range(100):
            y = long(randint(0, 1 << 30))
            y <<= 30
            y += randint(0, 1 << 30)
            for sx, sy in (1, 1), (1, -1), (-1, -1), (-1, 1):
                sx *= x
                sy *= y
                f1 = rbigint.fromlong(sx)
                f2 = rbigint.fromlong(sy)
                div, rem = lobj._x_divrem(f1, f2)
                assert div.tolong(), rem.tolong() == divmod(sx, sy)

    # testing Karatsuba stuff
    def test__v_iadd(self):
        f1 = rbigint([lobj.MASK] * 10, 1)
        f2 = rbigint([1], 1)
        carry = lobj._v_iadd(f1, 1, len(f1.digits)-1, f2, 1)
        assert carry == 1
        assert f1.tolong() == lobj.MASK

    def test__v_isub(self):
        f1 = rbigint([lobj.MASK] + [0] * 9 + [1], 1)
        f2 = rbigint([1], 1)
        borrow = lobj._v_isub(f1, 1, len(f1.digits)-1, f2, 1)
        assert borrow == 0
        assert f1.tolong() == (1 << lobj.SHIFT) ** 10 - 1

    def test__kmul_split(self):
        split = 5
        diglo = [0] * split
        dighi = [lobj.MASK] * split
        f1 = rbigint(diglo + dighi, 1)
        hi, lo = lobj._kmul_split(f1, split)
        assert lo.digits == [0]
        assert hi.digits == dighi

    def test__k_mul(self):
        digs = KARATSUBA_CUTOFF * 5
        f1 = rbigint([lobj.MASK] * digs, 1)
        f2 = lobj._x_add(f1,rbigint([1], 1))
        ret = lobj._k_mul(f1, f2)
        assert ret.tolong() == f1.tolong() * f2.tolong()

    def test__k_lopsided_mul(self):
        digs_a = KARATSUBA_CUTOFF + 3
        digs_b = 3 * digs_a
        f1 = rbigint([lobj.MASK] * digs_a, 1)
        f2 = rbigint([lobj.MASK] * digs_b, 1)
        ret = lobj._k_lopsided_mul(f1, f2)
        assert ret.tolong() == f1.tolong() * f2.tolong()

    def test_longlong(self):
        max = 1L << (r_longlong.BITS-1)
        f1 = rbigint.fromlong(max-1)    # fits in r_longlong
        f2 = rbigint.fromlong(-max)     # fits in r_longlong
        f3 = rbigint.fromlong(max)      # overflows
        f4 = rbigint.fromlong(-max-1)   # overflows
        assert f1.tolonglong() == max-1
        assert f2.tolonglong() == -max
        py.test.raises(OverflowError, f3.tolonglong)
        py.test.raises(OverflowError, f4.tolonglong)

    def test_uintmask(self):
        assert rbigint.fromint(-1).uintmask() == r_uint(-1)
        assert rbigint.fromint(0).uintmask() == r_uint(0)
        assert (rbigint.fromint(sys.maxint).uintmask() ==
                r_uint(sys.maxint))
        assert (rbigint.fromlong(sys.maxint+1).uintmask() ==
                r_uint(-sys.maxint-1))

    def test_ulonglongmask(self):
        assert rbigint.fromlong(-1).ulonglongmask() == r_ulonglong(-1)
        assert rbigint.fromlong(0).ulonglongmask() == r_ulonglong(0)
        assert (rbigint.fromlong(sys.maxint).ulonglongmask() ==
                r_ulonglong(sys.maxint))
        assert (rbigint.fromlong(9**50).ulonglongmask() ==
                r_ulonglong(9**50))
        assert (rbigint.fromlong(-9**50).ulonglongmask() ==
                r_ulonglong(-9**50))

BASE = 2 ** SHIFT

class TestTranslatable(object):
    def test_square(self):
        def test():
            x = rbigint([1410065408, 4], 1)
            y = x.mul(x)
            return y.str()
        res = interpret(test, [])
        assert "".join(res.chars) == test()

    def test_add(self):
        x = rbigint.fromint(-2147483647)
        y = rbigint.fromint(-1)
        z = rbigint.fromint(-2147483648)
        def test():
            return x.add(y).eq(z)
        assert test()
        res = interpret(test, [])
        assert res

    def test_args_from_rarith_int(self):
        from pypy.rpython.tool.rfficache import platform
        classlist = platform.numbertype_to_rclass.values()
        fnlist = []
        for r in classlist:
            if r is int:
                mask = sys.maxint*2+1
                signed = True
            else:
                mask = r.MASK
                signed = r.SIGNED
            values = [0, -1, mask>>1, -(mask>>1)-1]
            if not signed:
                values = [x & mask for x in values]
            values = [r(x) for x in values]

            def fn(i):
                n = rbigint.fromrarith_int(values[i])
                return n.str()

            for i in range(len(values)):
                res = fn(i)
                assert res == str(long(values[i]))
                res = interpret(fn, [i])
                assert ''.join(res.chars) == str(long(values[i]))
