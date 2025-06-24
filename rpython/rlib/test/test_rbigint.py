from __future__ import division

import operator
import sys, os
import math
from random import random, randint, sample

try:
    import pytest
except ImportError:
    print 'cwd', os.getcwd()
    print 'sys.path', sys.path
    raise

from rpython.rlib import rbigint as lobj
from rpython.rlib.rarithmetic import r_uint, r_longlong, r_ulonglong, intmask, LONG_BIT
from rpython.rlib.rbigint import (rbigint, SHIFT, MASK, KARATSUBA_CUTOFF,
    _store_digit, _mask_digit, InvalidEndiannessError, InvalidSignednessError,
    gcd_lehmer, lehmer_xgcd, gcd_binary, divmod_big, ONERBIGINT, MaxIntError,
    _str_to_int_big_w5pow, _str_to_int_big_base10, _str_to_int_big_inner10,
    _format_lowest_level_divmod_int_results, _format_int10_18digits)
from rpython.rlib.rbigint import HOLDER
from rpython.rlib.rfloat import NAN
from rpython.rtyper.test.test_llinterp import interpret
from rpython.translator.c.test.test_standalone import StandaloneTests
from rpython.rtyper.tool.rfficache import platform
from rpython.rlib.rstring import StringBuilder

from hypothesis import given, strategies, example, settings, assume

longs = strategies.builds(
    long, strategies.integers())
ints = strategies.integers(-sys.maxint-1, sys.maxint)

def makelong(data):
    numbits = data.draw(strategies.integers(1, 2000))
    r = data.draw(strategies.integers(0, 1 << numbits))
    if data.draw(strategies.booleans()):
        return -r
    return r

def makelong_long_sequences(data, ndigits):
    """ From CPython:
    Get quasi-random long consisting of ndigits digits (in base BASE).
    quasi == the most-significant digit will not be 0, and the number
    is constructed to contain long strings of 0 and 1 bits.  These are
    more likely than random bits to provoke digit-boundary errors.
    The sign of the number is also random.
    """
    nbits_hi = ndigits * SHIFT
    nbits_lo = nbits_hi - SHIFT + 1
    answer = 0L
    nbits = 0
    r = data.draw(strategies.integers(0, SHIFT * 2 - 1)) | 1  # force 1 bits to start
    while nbits < nbits_lo:
        bits = (r >> 1) + 1
        bits = min(bits, nbits_hi - nbits)
        assert 1 <= bits <= SHIFT
        nbits = nbits + bits
        answer = answer << bits
        if r & 1:
            answer = answer | ((1 << bits) - 1)
        r = data.draw(strategies.integers(0, SHIFT * 2 - 1))
    assert nbits_lo <= nbits <= nbits_hi
    if data.draw(strategies.booleans()):
        answer = -answer
    return answer


MAXDIGITS = 15
digitsizes = strategies.sampled_from(
    range(1, MAXDIGITS+1) +
    range(KARATSUBA_CUTOFF, KARATSUBA_CUTOFF + 14) +
    [KARATSUBA_CUTOFF * 3, KARATSUBA_CUTOFF * 1000]
)

def make_biglongs_for_division(data):
    size1 = data.draw(digitsizes)
    val1 = makelong_long_sequences(data, size1)
    size2 = data.draw(digitsizes)
    val2 = makelong_long_sequences(data, size2)
    return val1, val2

tuples_biglongs_for_division = strategies.builds(
        make_biglongs_for_division,
        strategies.data())

biglongs = strategies.builds(makelong, strategies.data())


def makerarithint(data):
    classlist = platform.numbertype_to_rclass.values()
    cls = data.draw(strategies.sampled_from(classlist))
    if cls is int:
        minimum = -sys.maxint-1
        maximum = sys.maxint
    else:
        BITS = cls.BITS
        if cls.SIGNED:
            minimum = -2 ** (BITS - 1)
            maximum = 2 ** (BITS - 1) - 1
        else:
            minimum = 0
            maximum = 2 ** BITS - 1
    value = data.draw(strategies.integers(minimum, maximum))
    return cls(value)
rarith_ints = strategies.builds(makerarithint, strategies.data())


def gen_signs(l):
    for s in l:
        if s == 0:
            yield s
        else:
            yield s
            yield -s

long_vals_not_too_big = range(17) + [
        37, 39, 50,
        127, 128, 129, 511, 512, 513, sys.maxint, sys.maxint + 1,
        12345678901234567890L,
        123456789123456789000000L,
]

long_vals = long_vals_not_too_big + [
        1 << 100, 3 ** 10000]

int_vals = range(33) + [
        1000,
        0x11111111, 0x11111112, 8888,
        9999, sys.maxint, 2 ** 19, 2 ** 18 - 1
]
signed_int_vals = list(gen_signs(int_vals)) + [-sys.maxint-1]

class TestRLong(object):
    def test_simple(self):
        for op1 in [-2, -1, 0, 1, 2, 10, 50]:
            for op2 in [-2, -1, 0, 1, 2, 10, 50]:
                rl_op1 = rbigint.fromint(op1)
                rl_op2 = rbigint.fromint(op2)
                for op in "add sub mul".split():
                    r1 = getattr(rl_op1, op)(rl_op2)
                    r2 = getattr(operator, op)(op1, op2)
                    assert r1.tolong() == r2

    def test_frombool(self):
        assert rbigint.frombool(False).tolong() == 0
        assert rbigint.frombool(True).tolong() == 1

    def test_str(self):
        n = 1
        r1 = rbigint.fromint(1)
        three = rbigint.fromint(3)
        for i in range(300):
            n *= 3
            r1 = r1.mul(three)
            assert r1.str() == str(n)
            r2 = r1.neg()
            assert r2.str() == str(-n)

    def test_floordiv(self):
        for op1 in gen_signs(long_vals):
            rl_op1 = rbigint.fromlong(op1)
            for op2 in gen_signs(long_vals):
                if not op2:
                    continue
                rl_op2 = rbigint.fromlong(op2)
                r1 = rl_op1.floordiv(rl_op2)
                r2 = op1 // op2
                assert r1.tolong() == r2

    def test_int_floordiv(self):
        x = 1000L
        r = rbigint.fromlong(x)
        r2 = r.int_floordiv(10)
        assert r2.tolong() == 100L

        for op1 in gen_signs(long_vals):
            for op2 in signed_int_vals:
                if not op2:
                    continue
                rl_op1 = rbigint.fromlong(op1)
                r1 = rl_op1.int_floordiv(op2)
                r2 = op1 // op2
                assert r1.tolong() == r2

        with pytest.raises(ZeroDivisionError):
            r.int_floordiv(0)

        # Error pointed out by Armin Rigo
        n = sys.maxint+1
        r = rbigint.fromlong(n)
        assert r.int_floordiv(int(-n)).tolong() == -1L

        for x in int_vals:
            if not x:
                continue
            r = rbigint.fromlong(x)
            rn = rbigint.fromlong(-x)
            res = r.int_floordiv(x)
            res2 = r.int_floordiv(-x)
            res3 = rn.int_floordiv(x)
            assert res.tolong() == 1L
            assert res2.tolong() == -1L
            assert res3.tolong() == -1L

    def test_floordiv2(self):
        n1 = rbigint.fromlong(sys.maxint + 1)
        n2 = rbigint.fromlong(-(sys.maxint + 1))
        assert n1.floordiv(n2).tolong() == -1L
        assert n2.floordiv(n1).tolong() == -1L

    def test_truediv(self):
        for op1 in gen_signs(long_vals_not_too_big):
            rl_op1 = rbigint.fromlong(op1)
            for op2 in gen_signs(long_vals):
                rl_op2 = rbigint.fromlong(op2)
                if not op2:
                    with pytest.raises(ZeroDivisionError):
                        rl_op1.truediv(rl_op2)
                    continue
                r1 = rl_op1.truediv(rl_op2)
                r2 = op1 / op2
                assert r1 == r2

    def test_truediv_precision(self):
        op1 = rbigint.fromlong(12345*2**30)
        op2 = rbigint.fromlong(98765*7**81)
        f = op1.truediv(op2)
        assert f == 4.7298422347492634e-61      # exactly

    def test_truediv_overflow(self):
        overflowing = 2**1024 - 2**(1024-53-1)
        op1 = rbigint.fromlong(overflowing-1)
        op2 = rbigint.fromlong(1)
        f = op1.truediv(op2)
        assert f == 1.7976931348623157e+308     # exactly

        op1 = rbigint.fromlong(overflowing-1)
        op2 = rbigint.fromlong(-1)
        f = op1.truediv(op2)
        assert f == -1.7976931348623157e+308    # exactly

        op1 = rbigint.fromlong(-overflowing+1)
        op2 = rbigint.fromlong(-1)
        f = op1.truediv(op2)
        assert f == +1.7976931348623157e+308    # exactly

        op1 = rbigint.fromlong(overflowing)
        op2 = rbigint.fromlong(1)
        with pytest.raises(OverflowError):
            op1.truediv(op2)

    def test_truediv_overflow2(self):
        overflowing = 2**1024 - 2**(1024-53-1)
        op1 = rbigint.fromlong(2*overflowing - 10)
        op2 = rbigint.fromlong(2)
        f = op1.truediv(op2)
        assert f == 1.7976931348623157e+308    # exactly
        op2 = rbigint.fromlong(-2)
        f = op1.truediv(op2)
        assert f == -1.7976931348623157e+308   # exactly

    def test_mod(self):
        for op1 in gen_signs(long_vals):
            rl_op1 = rbigint.fromlong(op1)
            for op2 in gen_signs(long_vals):
                rl_op2 = rbigint.fromlong(op2)
                if not op2:
                    with pytest.raises(ZeroDivisionError):
                        rl_op1.mod(rl_op2)
                    continue
                r1 = rl_op1.mod(rl_op2)
                r2 = op1 % op2

                assert r1.tolong() == r2

    def test_int_mod(self):
        for x in gen_signs(long_vals):
            op1 = rbigint.fromlong(x)
            for y in signed_int_vals:
                if not y:
                    with pytest.raises(ZeroDivisionError):
                        op1.int_mod(0)
                    continue
                r1 = op1.int_mod(y)
                r2 = x % y
                assert r1.tolong() == r2

    def test_int_mod_int_result(self):
        for x in gen_signs(long_vals):
            op1 = rbigint.fromlong(x)
            for y in signed_int_vals:
                if not y:
                    with pytest.raises(ZeroDivisionError):
                        op1.int_mod_int_result(0)
                    continue
                r1 = op1.int_mod_int_result(y)
                r2 = x % y
                assert r1 == r2

    def test_int_divmod_int_result(self):
        for x in gen_signs(long_vals):
            op1 = rbigint.fromlong(x)
            for y in signed_int_vals:
                if not y:
                    continue
                r1 = op1.int_mod_int_result(y)
                r2 = x % y
                assert r1 == r2


    def test_pow(self):
        for op1 in gen_signs(long_vals_not_too_big):
            rl_op1 = rbigint.fromlong(op1)
            for op2 in [0, 1, 2, 8, 9, 10, 11]:
                rl_op2 = rbigint.fromint(op2)
                r1 = rl_op1.pow(rl_op2)
                r2 = op1 ** op2
                assert r1.tolong() == r2

                for op3 in gen_signs([1, 2, 5, 1000, 12312312312312235659969696l]):
                    if not op3:
                        continue
                    r3 = rl_op1.pow(rl_op2, rbigint.fromlong(op3))
                    r4 = pow(op1, op2, op3)
                    assert r3.tolong() == r4

    def test_int_pow(self):
        for op1 in gen_signs(long_vals_not_too_big):
            rl_op1 = rbigint.fromlong(op1)
            for op2 in [0, 1, 2, 8, 9, 10, 11, 127, 128, 129]:
                r1 = rl_op1.int_pow(op2)
                r2 = op1 ** op2
                assert r1.tolong() == r2

                for op3 in gen_signs(long_vals_not_too_big):
                    if not op3:
                        continue
                    r3 = rl_op1.int_pow(op2, rbigint.fromlong(op3))
                    r4 = pow(op1, op2, op3)
                    assert r3.tolong() == r4

    def test_int_pow_big(self):
        if sys.maxint < 2**32:
            pytest.skip("64-bit only")
        for op1 in gen_signs(int_vals):
            rl_op1 = rbigint.fromint(op1)
            for op2 in [2**31, 2**32-1, 2**32]:
                r1 = rl_op1.int_pow(op2, rbigint.fromint(sys.maxint))
                r2 = pow(op1, op2, sys.maxint)
                assert r1.tolong() == r2

    def test_pow_raises(self):
        r1 = rbigint.fromint(2)
        r0 = rbigint.fromint(0)
        with pytest.raises(ValueError):
            r1.int_pow(2, r0)
        with pytest.raises(ValueError):
            r1.pow(r1, r0)

    def test_touint(self):
        result = r_uint(sys.maxint + 42)
        rl = rbigint.fromint(sys.maxint).add(rbigint.fromint(42))
        assert rl.touint() == result

    def test_eq_ne_operators(self):
        a1 = rbigint.fromint(12)
        a2 = rbigint.fromint(12)
        a3 = rbigint.fromint(123)

        assert a1 == a2
        assert a1 != a3
        assert not (a1 != a2)
        assert not (a1 == a3)

    def test_divmod_big2(self):
        def check(a, b):
            fa = rbigint.fromlong(a)
            fb = rbigint.fromlong(b)
            div, mod = divmod_big(fa, fb)
            assert div.mul(fb).add(mod).eq(fa)
        check(2, 3)
        check(3, 2)
        check((2 << 1000) - 1, (2 << (65 * 3 + 2)) - 1)
        check((2 + 5 * 2 ** SHIFT) << (100 * SHIFT), 5 << (100 * SHIFT))

    def test_divmod_big_is_used(self, monkeypatch):
        # make sure that the big divmod path is actually hit
        monkeypatch.setattr(rbigint, "_divmod_small", None)
        fa = rbigint.fromlong(3 ** (SHIFT * HOLDER.DIV_LIMIT * 2))
        fb = rbigint.fromlong(5 ** (SHIFT * HOLDER.DIV_LIMIT))
        div, mod = fa.divmod(fb)
        assert div.mul(fb).add(mod).eq(fa)

    def test_karatsuba_not_used_bug(self):
        a = rbigint.fromlong(2 ** 2000 + 1)
        b = rbigint.fromlong(2 ** 5000 + 7)
        assert a.mul(b).tolong() == a.tolong() * b.tolong()

    def test_lopsided_bug(self):
        la = 0x1b8e499a888235ea66f6497e3640bc118592a4ecb800e53e0121af9b2dede38c9323dc160ad564c10ff34095fcc89ecefde3116e7ad99bd5a5b785d811a1e930ae0b0a919623569c99d6c1e779aa5345609a14fc64a83970991d7df672d3bf2fe800766932291b2593382495d1b2a9de1a212d0e517d35764a8a30d060d4218f034807c59728a009683887c3f239f6b958216fd6e36db778bf350941be6ee987f87ea6460ba77f1db154fff175d20117107b5ebd48305b4190d082433419f3daace778d9ce9975ca33293c8b7ad7dd253321e208c22e1bf3833535dd4c76395117e6f32444254fdb9e77cd0b5f8d98c31dafaab720067ef925
        a = rbigint.fromlong(la)
        lb = 0x30fcf4a0f2ae98bd28d249c3eeabf902b492ec4f8001978aacada9f76e18b0f9e9234e6013427a3ac705c82716b9fde1c35ac9a7f6d8317bd14643473bca821da73012c9ee77b66bbc287529bbd97797c82e5e327a0e9f0110346e27e894e21c471d44493cbadaed7780410a585a118ad91e88fd02a5b4608483e500ac23c9e1ccf1d4ed7e811c8280647f953cd8d3109cad389a77df7f0f8cd01074e0c52d6380e12798f84637513b41c7029891c90c8f1436a5d5ab4ce656c80405b1f53fbda529ba66c49f0a4b059ea4862fb8a5977758ae4875a74e22b05e98a5dd43f41e6361b0407925e34d8b7fa5698d6d815adf712f7e71d2a8d75ee7749e22e558157d73c1ed1089063dd7a29c915990836b5a951aa77917847bd9807d6c89b4262871127d17ca5a84e2b23bc5eb66137cce412dcbd88622b55b05b710258affcc845a8e1b99d33c187a237eacd21e9628063948f711b2e5617b647f3fe7c28bac1989612a66d6be34d59ffee63e15e0cdf10d43c6f6301c47e7c7f3ca71dc4e312873633957a6054f25d4db49dcc401aba272ff7c23e077c143510a040f5eb80fe096384c3a4ab0604d951710956f84cdefb631a2ed806ad8f5fef5ef1223dbea4b8a7b49309e9672e77c763dbb698432c77cfff875ab5c97d24f4441b5a3704deda8835135e3e6314be281a97963b49eccf06571b634efa16605a0ec2eda8148a6537e24da5fb128cfbde3ea6c28d850eac3815dd2a0a72844a14590124a6e9062befbdf7fb14c7783ee5096481a5ef0ef9dabf4bc831213afc469a5256818e1dba97cae6f63d6cf2b9584361f36b1b8fa60286fe6bc010129b7f99ee250907ed0a134900513bd3c38555de3b085e7e86
        b = rbigint.fromlong(lb)
        x = a.mul(b)
        assert x.tolong() == la * lb

    def test_mul_bug(self):
        x = -0x1fffffffffffe00000000000007fffffffffffffffffe0000000000000fffffffffffffc0000000000000003fffffffffff1fffffffffffffffffffff8000000000000000ff80000000000000fffffff000000000000000000000fff800000000000003fffffffffffffffffffffffffffffffe000000000000000000fffffffffffffffffffffffffffffffffffffffffffffc3ffffffffffffff80000000003fffffffffffffe000000000000003fffffffffffffffffffffffffffffffffffffc000000000000000007ffc00000007fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffe00000000000000000000000fffffffffe0000000000000000000000000000000007ffffffffff8000000000000000000000000007ffffffffe00000000000001ffffffff00000000007fffffffffc0000000000000000000007fffffffffffffe0000000000ffffffffffffffffffffffffffffff0000000000000000000000000000004000000000000000000007fffffffffffffffc00fffffffff80000001fffffffffffe0000000007ffffffffffffffffc000000000000000000000003f00fffffff000000001fffffffffffffffffffffffffffffffffe000000000000003ffffffffffffffc000000000000000000000000000000000000000000000000fffffffffffff8000001ffffffffffffffffffffffffe00000000000003ffffffffffffffffffffffff00000000fffffffffff000000000L
        y = -0x3fffffffffffc0000000000000000007ffffffffffff800000000000000000001ffffffffffffffc0000000000000000000000ffffffffffffffffffffffffffffc000000000000000000001ffffffffffffffffffffffffffffffffffffffffffffffffffffe00000000000000000000000000007fffffffffff000000000000000000000000fffffffffffffffffffffffffffffffffffffffff0000000003e007fffffffffffffffffff80000000000000000003fffffffffc000000000000007fffc0000000007ffffffffffffff0000000000010000000000000001fffffffffffffffffffffffffffffffffe000000000000fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffe0000000000001ffff007fff0000000000000000000000001f000000000001fffffffffffffffffc00000000001fffffffffffffffffffffffffffffffffffffff0000000000000000001ffffffffffff00000000000000000000000000000000000003fffffffff00003fffffffe00000000000000000000ffffffffffffffffffffff800001ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff8000000000000001ffe000001ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff00000000000fffffffffff800000000000000000fffffffffffffffffffe00000000003ffffffffffffffffffffffffffffffffffffffffc000000000000000006000001fffffffe0000000000ffffffffffffffffffffffffff8003fffffffffffffffffffffffffffe0000007fffc0000000000000000000000001ffffffffffffffffffffffffffffffffffff0000000000001fffe00000000000000000000000000000000000000000000000000000003fffffff0000000000007ffffff8000000000000001fffffffffffffffff80001fffffffffffffffffffffffffff800000000000000000001ffffe00000000000000000003fffffffffffffffffffffffff000000000000000fffffffffffffffffffffffffffffc0000000000000003fffffe0000000000000000000000001ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffe0000000003fff00001ffffffffffffffffffff0000000000001fffffffffffffc0000000000007ffffffffffffffffffffc000000000007fffffffffffffffffff80000000000003ffffffffffffc0000000000000000000000000000000000000000000000ffffe000000000000000000000000000001ffffffffffffffffffffffffffffffffffffe007ffffffffffff000000000000003fffffffffffffffffff800000000000000ff0000000000000000000000000000001ffffffffffffe00000000000007ffffffffffffff8000000000000001ffffffffffffc0000000000007ff000003fffffffffffffffffffffffffffffffffffffe00000007ffffffffffffffffffffe00000007ffffff0000000000000000ffffc00000000000000000ffffffffff8000000000000000fffffe0000000000000000000007fffffffffc000000fe0000000000000000000001ffffff800000000000000001ffffffffff00000000000000000000000000000000000000000000000ffffffffffffffffff000000000000000000000007fffffffffffffc0000fffffffffffffffffffffffffe000003ffffffffffff800000000000001fffffffffffffc000000000000000000000000001fff8000000000000000000000000000fffffffffffffffffffffffff0000000000000000003fe00000003fffffffffffffffff00000000000000ffffffffffe07fffffffffffffffc000000000000000000000003fffffff800000000000000000000003fffffffffffc0000000000000000000000003fffffffffffffffffc0000000000ffffffffffffffffffffffffffffffffffffffffffffffffffe000ffffffffffffffffc000000000000000000000000000000000000000000ffffffffffffffff8000000000000000000000000000000000000000000000000000000000fffffffffffffffc00000000000000003fffffffffffffffffffffffffffffffffffffe00003fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffe0000000000003fffffff00000000007ffffffffffc0007ffffffffe00000ffffc000700000000000000fffffffffff80000000000000000000000L
        xl = rbigint.fromlong(x)
        yl = rbigint.fromlong(y)
        assert xl.mul(yl).tolong() == x * y
        assert yl.mul(xl).tolong() == x * y


def bigint(lst, sign):
    for digit in lst:
        assert digit & MASK == digit    # wrongly written test!
    return rbigint(map(_store_digit, map(_mask_digit, lst)), sign)


class Test_rbigint(object):

    def test_args_from_long(self):
        BASE = 1 << SHIFT
        assert rbigint.fromlong(0).eq(bigint([0], 0))
        assert rbigint.fromlong(17).eq(bigint([17], 1))
        assert rbigint.fromlong(BASE-1).eq(bigint([intmask(BASE-1)], 1))
        assert rbigint.fromlong(BASE).eq(bigint([0, 1], 1))
        assert rbigint.fromlong(BASE**2).eq(bigint([0, 0, 1], 1))
        assert rbigint.fromlong(-17).eq(bigint([17], -1))
        assert rbigint.fromlong(-(BASE-1)).eq(bigint([intmask(BASE-1)], -1))
        assert rbigint.fromlong(-BASE).eq(bigint([0, 1], -1))
        assert rbigint.fromlong(-(BASE**2)).eq(bigint([0, 0, 1], -1))
#        assert rbigint.fromlong(-sys.maxint-1).eq(
#            rbigint.digits_for_most_neg_long(-sys.maxint-1), -1)

    def test_args_from_int(self):
        BASE = 1 << 31 # Can't can't shift here. Shift might be from longlonglong
        MAX = int(BASE-1)
        assert rbigint.fromrarith_int(0).eq(bigint([0], 0))
        assert rbigint.fromrarith_int(17).eq(bigint([17], 1))
        assert rbigint.fromrarith_int(MAX).eq(bigint([MAX], 1))
        # No longer true.
        """assert rbigint.fromrarith_int(r_longlong(BASE)).eq(bigint([0, 1], 1))
        assert rbigint.fromrarith_int(r_longlong(BASE**2)).eq(
            bigint([0, 0, 1], 1))"""
        assert rbigint.fromrarith_int(-17).eq(bigint([17], -1))
        assert rbigint.fromrarith_int(-MAX).eq(bigint([MAX], -1))
        """assert rbigint.fromrarith_int(-MAX-1).eq(bigint([0, 1], -1))
        assert rbigint.fromrarith_int(r_longlong(-(BASE**2))).eq(
            bigint([0, 0, 1], -1))"""
#        assert rbigint.fromrarith_int(-sys.maxint-1).eq((
#            rbigint.digits_for_most_neg_long(-sys.maxint-1), -1)

    def test_args_from_uint(self):
        BASE = 1 << SHIFT
        assert rbigint.fromrarith_int(r_uint(0)).eq(bigint([0], 0))
        assert rbigint.fromrarith_int(r_uint(17)).eq(bigint([17], 1))
        assert rbigint.fromrarith_int(r_uint(BASE-1)).eq(bigint([intmask(BASE-1)], 1))
        assert rbigint.fromrarith_int(r_uint(BASE)).eq(bigint([0, 1], 1))
        #assert rbigint.fromrarith_int(r_uint(BASE**2)).eq(bigint([0], 0))
        assert rbigint.fromrarith_int(r_uint(sys.maxint)).eq(
            rbigint.fromint(sys.maxint))
        assert rbigint.fromrarith_int(r_uint(sys.maxint+1)).eq(
            rbigint.fromlong(sys.maxint+1))
        assert rbigint.fromrarith_int(r_uint(2*sys.maxint+1)).eq(
            rbigint.fromlong(2*sys.maxint+1))

    def test_fromdecimalstr(self):
        x = rbigint.fromdecimalstr("12345678901234567890523897987")
        assert x.tolong() == 12345678901234567890523897987L
        assert x.tobool() is True
        x = rbigint.fromdecimalstr("+12345678901234567890523897987")
        assert x.tolong() == 12345678901234567890523897987L
        assert x.tobool() is True
        x = rbigint.fromdecimalstr("-12345678901234567890523897987")
        assert x.tolong() == -12345678901234567890523897987L
        assert x.tobool() is True
        x = rbigint.fromdecimalstr("+0")
        assert x.tolong() == 0
        assert x.tobool() is False
        x = rbigint.fromdecimalstr("-0")
        assert x.tolong() == 0
        assert x.tobool() is False

    def test_fromstr(self):
        from rpython.rlib.rstring import ParseStringError
        assert rbigint.fromstr('123L').tolong() == 123
        assert rbigint.fromstr('123L  ').tolong() == 123
        with pytest.raises(ParseStringError):
            rbigint.fromstr('L')
        with pytest.raises(ParseStringError):
            rbigint.fromstr('L  ')
        assert rbigint.fromstr('123L', 4).tolong() == 27
        assert rbigint.fromstr('123L', 30).tolong() == 27000 + 1800 + 90 + 21
        assert rbigint.fromstr('123L', 22).tolong() == 10648 + 968 + 66 + 21
        assert rbigint.fromstr('123L', 21).tolong() == 441 + 42 + 3
        assert rbigint.fromstr('1891234174197319').tolong() == 1891234174197319
        assert rbigint.fromstr('1891_234_17_4_19731_9', allow_underscores=True).tolong() == 1891234174197319
        assert rbigint.fromstr('1_1' * 6000, allow_underscores=True).tolong() == int('11' * 6000)

    def test__from_numberstring_parser_rewind_bug(self):
        from rpython.rlib.rstring import NumberStringParser
        s = "-99"
        p = NumberStringParser(s, s, 10, 'int')
        assert p.sign == -1
        res = p.next_digit()
        assert res == 9
        res = p.next_digit()
        assert res == 9
        res = p.next_digit()
        assert res == -1
        p.rewind()
        res = p.next_digit()
        assert res == 9
        res = p.next_digit()
        assert res == 9
        res = p.next_digit()
        assert res == -1

    def test_fromstr_huge(self):
        assert _str_to_int_big_base10("1" * 1000, 0, 1000).tolong() == int("1" * 1000)
        mem = {}

        result = _str_to_int_big_inner10('123952' * 1000, 0, 6000, mem, 20)
        assert len(mem) == 13
        assert result

    def test_from_numberstring_parser(self):
        from rpython.rlib.rstring import NumberStringParser
        parser = NumberStringParser("1231231241", "1231231241", 10, "long")
        assert rbigint._from_numberstring_parser(parser).tolong() == 1231231241

    def test_from_numberstring_parser_no_implicit_octal(self):
        from rpython.rlib.rstring import NumberStringParser, ParseStringError
        s = "077777777777777777777777777777"
        parser = NumberStringParser(s, s, 0, "long",
                                    no_implicit_octal=True)
        with pytest.raises(ParseStringError):
            rbigint._from_numberstring_parser(parser)
        parser = NumberStringParser("000", "000", 0, "long",
                                    no_implicit_octal=True)
        assert rbigint._from_numberstring_parser(parser).tolong() == 0

    def test_limit(self):
        from rpython.rlib.rstring import NumberStringParser, MaxDigitsError
        max_str_digits = 999
        s = '0' * (max_str_digits)
        s0 = '1' + s
        s1 = '1' + s[1:]
        s2 = '  - 1' + s[1:]
        with pytest.raises(MaxDigitsError):
            parser = NumberStringParser(s0, s0, 0, "long",
                                        max_str_digits=max_str_digits)
        # these succeed
        parser = NumberStringParser(s2, s2, 0, "long",
                                    max_str_digits=max_str_digits)
        parser = NumberStringParser(s1, s1, 0, "long",
                                    max_str_digits=max_str_digits)
        x = rbigint._from_numberstring_parser(parser)

        assert s1 == x.str(max_str_digits)
        with pytest.raises(MaxIntError):
            x.str(max_str_digits - 1)

    def test_add(self):
        for x in gen_signs(long_vals):
            f1 = rbigint.fromlong(x)
            for y in gen_signs(long_vals):
                f2 = rbigint.fromlong(y)
                result = f1.add(f2)
                assert result.tolong() == x + y
            
        

    def test_add(self):
        for x in gen_signs(long_vals):
            f1 = rbigint.fromlong(x)
            for y in gen_signs(long_vals):
                f2 = rbigint.fromlong(y)
                result = f1.add(f2)
                assert result.tolong() == x + y

    def test_int_add(self):
        for x in gen_signs(long_vals):
            f1 = rbigint.fromlong(x)
            for y in signed_int_vals:
                result = f1.int_add(y)
                assert result.tolong() == x + y

    def test_sub(self):
        for x in gen_signs(long_vals):
            f1 = rbigint.fromlong(x)
            for y in gen_signs(long_vals):
                f2 = rbigint.fromlong(y)
                result = f1.sub(f2)
                assert result.tolong() == x - y

    def test_int_sub(self):
        for x in gen_signs(long_vals):
            f1 = rbigint.fromlong(x)
            for y in signed_int_vals:
                result = f1.int_sub(y)
                assert result.tolong() == x - y

    def test_subzz(self):
        w_l0 = rbigint.fromint(0)
        assert w_l0.sub(w_l0).tolong() == 0

    def test_mul(self):
        for x in gen_signs(long_vals):
            f1 = rbigint.fromlong(x)
            for y in gen_signs(long_vals_not_too_big):
                f2 = rbigint.fromlong(y)
                result = f1.mul(f2)
                assert result.tolong() == x * y
            # there's a special case for a is b
            result = f1.mul(f1)
            assert result.tolong() == x * x

    def test_int_mul(self):
        for x in gen_signs(long_vals):
            f1 = rbigint.fromlong(x)
            for y in signed_int_vals:
                result = f1.int_mul(y)
                assert result.tolong() == x * y

    def test_mul_int_int_rbigint_result(self):
        for x in signed_int_vals:
            for y in signed_int_vals:
                result = rbigint.mul_int_int_bigint_result(x, y)
                assert result.tolong() == x * y

    def test_tofloat(self):
        x = 12345678901234567890L ** 10
        f1 = rbigint.fromlong(x)
        d = f1.tofloat()
        assert d == float(x)
        x = x ** 100
        f1 = rbigint.fromlong(x)
        with pytest.raises(OverflowError):
            f1.tofloat()
        f2 = rbigint.fromlong(2097152 << SHIFT)
        d = f2.tofloat()
        assert d == float(2097152 << SHIFT)

    def test_tofloat_precision(self):
        assert rbigint.fromlong(0).tofloat() == 0.0
        for sign in [1, -1]:
            for p in xrange(100):
                x = long(2**p * (2**53 + 1) + 1) * sign
                y = long(2**p * (2**53+ 2)) * sign
                rx = rbigint.fromlong(x)
                rxf = rx.tofloat()
                assert rxf == float(y)
                assert rbigint.fromfloat(rxf).tolong() == y
                #
                x = long(2**p * (2**53 + 1)) * sign
                y = long(2**p * 2**53) * sign
                rx = rbigint.fromlong(x)
                rxf = rx.tofloat()
                assert rxf == float(y)
                assert rbigint.fromfloat(rxf).tolong() == y

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
        with pytest.raises(OverflowError):
            rbigint.fromfloat(x)
        with pytest.raises(ValueError):
            rbigint.fromfloat(NAN)
        #
        f1 = rbigint.fromfloat(9007199254740991.0)
        assert f1.tolong() == 9007199254740991

        null = rbigint.fromfloat(-0.0)
        assert null.int_eq(0)

    def test_eq_ne(self):
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

        assert not f1.ne(f1)
        assert not f2.ne(f2)
        assert not f3.ne(f3)
        assert f1.ne(f2)
        assert f1.ne(f3)

    def test_eq_fastpath(self):
        x = 1234
        y = 1234
        f1 = rbigint.fromint(x)
        f2 = rbigint.fromint(y)
        assert f1.eq(f2)

    def test_lt(self):
        val = [0, 0x111111111111, 0x111111111112, 0x111111111112FFFF]
        for x in gen_signs(val):
            for y in gen_signs(val):
                f1 = rbigint.fromlong(x)
                f2 = rbigint.fromlong(y)
                assert (x < y) ==  f1.lt(f2)

    def test_int_comparison(self):
        for x in gen_signs(long_vals):
            for y in signed_int_vals:
                f1 = rbigint.fromlong(x)
                assert (x < y) == f1.int_lt(y)
                assert (x <= y) == f1.int_le(y)
                assert (x > y) == f1.int_gt(y)
                assert (x >= y) == f1.int_ge(y)
                assert (x == y) == f1.int_eq(y)
                assert (x != y) == f1.int_ne(y)

    def test_order(self):
        f6 = rbigint.fromint(6)
        f7 = rbigint.fromint(7)
        assert (f6.lt(f6), f6.lt(f7), f7.lt(f6)) == (0,1,0)
        assert (f6.le(f6), f6.le(f7), f7.le(f6)) == (1,1,0)
        assert (f6.gt(f6), f6.gt(f7), f7.gt(f6)) == (0,0,1)
        assert (f6.ge(f6), f6.ge(f7), f7.ge(f6)) == (1,0,1)

    def test_int_order(self):
        f6 = rbigint.fromint(6)
        f7 = rbigint.fromint(7)
        assert (f6.int_lt(6), f6.int_lt(7), f7.int_lt(6)) == (0,1,0)
        assert (f6.int_le(6), f6.int_le(7), f7.int_le(6)) == (1,1,0)
        assert (f6.int_gt(6), f6.int_gt(7), f7.int_gt(6)) == (0,0,1)
        assert (f6.int_ge(6), f6.int_ge(7), f7.int_ge(6)) == (1,0,1)

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
                with pytest.raises(ValueError):
                    l.touint()

        toobig_lv1 = rbigint.fromlong(sys.maxint+1)
        assert toobig_lv1.tolong() == sys.maxint+1
        toobig_lv2 = rbigint.fromlong(sys.maxint+2)
        assert toobig_lv2.tolong() == sys.maxint+2
        toobig_lv3 = rbigint.fromlong(-sys.maxint-2)
        assert toobig_lv3.tolong() == -sys.maxint-2

        for lv in (toobig_lv1, toobig_lv2, toobig_lv3):
            with pytest.raises(OverflowError):
                lv.toint()

        lmaxuint = rbigint.fromlong(2*sys.maxint+1)
        toobig_lv4 = rbigint.fromlong(2*sys.maxint+2)

        u = lmaxuint.touint()
        assert u == 2*sys.maxint+1

        with pytest.raises(ValueError):
            toobig_lv3.touint()
        with pytest.raises(OverflowError):
            toobig_lv4.touint()


    def test_pow_lll(self):
        x = 10L
        y = 2L
        z = 13L
        f1 = rbigint.fromlong(x)
        f2 = rbigint.fromlong(y)
        f3 = rbigint.fromlong(z)
        v = f1.pow(f2, f3)
        assert v.tolong() == pow(x, y, z)
        f3n = f3.neg()
        v = f1.pow(f2, f3n)
        assert v.tolong() == pow(x, y, -z)
        #
        f1, f2, f3 = [rbigint.fromlong(i)
                      for i in (10L, -1L, 42L)]
        with pytest.raises(TypeError):
            f1.pow(f2, f3)
        f1, f2, f3 = [rbigint.fromlong(i)
                      for i in (10L, 5L, 0L)]
        with pytest.raises(ValueError):
            f1.pow(f2, f3)

    def test_pow_lll_bug(self):
        two = rbigint.fromint(2)
        t = rbigint.fromlong(2655689964083835493447941032762343136647965588635159615997220691002017799304)
        for n, expected in [(37, 9), (1291, 931), (67889, 39464)]:
            v = two.pow(t, rbigint.fromint(n))
            assert v.toint() == expected
        #
        # more tests, comparing against CPython's answer
        enabled = sample(range(5*32), 10)
        for i in range(5*32):
            t = t.mul(two)      # add one random bit
            if random() >= 0.5:
                t = t.add(rbigint.fromint(1))
            if i not in enabled:
                continue    # don't take forever
            n = randint(1, sys.maxint)
            v = two.pow(t, rbigint.fromint(n))
            assert v.toint() == pow(2, t.tolong(), n)

    def test_pow_lll_bug2(self):
        x = rbigint.fromlong(2)
        y = rbigint.fromlong(5100894665148900058249470019412564146962964987365857466751243988156579407594163282788332839328303748028644825680244165072186950517295679131100799612871613064597)
        z = rbigint.fromlong(538564)
        expected = rbigint.fromlong(163464)
        got = x.pow(y, z)
        assert got.eq(expected)

    def test_pow_lln(self):
        x = 10L
        y = 2L
        f1 = rbigint.fromlong(x)
        f2 = rbigint.fromlong(y)
        v = f1.pow(f2)
        assert v.tolong() == x ** y

    def test_normalize(self):
        f1 = bigint([1, 0], 1)
        f1._normalize()
        assert f1.numdigits() == 1
        f0 = bigint([0], 0)
        f0._normalize()
        assert f0.numdigits() == 1
        assert f0._size == 0
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
        masks_list = [int((1 << i) - 1) for i in range(1, r_uint.BITS-1)]
        for x in gen_signs([3L ** 30L, 5L ** 20L, 7 ** 300, 0L, 1L]):
            f1 = rbigint.fromlong(x)
            with pytest.raises(ValueError):
                f1.lshift(negative)
            with pytest.raises(ValueError):
                f1.rshift(negative)
            for y in [0L, 1L, 32L, 2304L, 11233L, 3 ** 9]:
                res1 = f1.lshift(int(y)).tolong()
                res2 = f1.rshift(int(y)).tolong()
                assert res1 == x << y
                assert res2 == x >> y
                for mask in masks_list:
                    res3 = f1.abs_rshift_and_mask(r_ulonglong(y), mask)
                    assert res3 == (abs(x) >> y) & mask

        # test special optimization case in rshift:
        assert rbigint.fromlong(-(1 << 100)).rshift(5).tolong() == -(1 << 100) >> 5

        # Chek value accuracy.
        assert rbigint.fromlong(18446744073709551615L).rshift(1).tolong() == 18446744073709551615L >> 1

    def test_shift_optimization(self):
        # does not crash with memory error
        assert rbigint.fromint(0).lshift(sys.maxint).tolong() == 0

    def test_qshift(self):
        for x in range(10):
            for y in range(1, 161, 16):
                num = (x << y) + x
                f1 = rbigint.fromlong(num)
                nf1 = rbigint.fromlong(-num)

                for z in range(1, 31):
                    res1 = f1.lqshift(z).tolong()
                    res2 = f1.rqshift(z).tolong()
                    res3 = nf1.lqshift(z).tolong()

                    assert res1 == num << z
                    assert res2 == num >> z
                    assert res3 == -num << z

        # Large digit
        for x in range((1 << SHIFT) - 10, (1 << SHIFT) + 10):
            f1 = rbigint.fromlong(x)
            assert f1.rqshift(SHIFT).tolong() == x >> SHIFT
            assert f1.rqshift(SHIFT+1).tolong() == x >> (SHIFT+1)

    def test_from_list_n_bits(self):
        for x in ([3L ** 30L, 5L ** 20L, 7 ** 300] +
                  [1L << i for i in range(130)] +
                  [(1L << i) - 1L for i in range(130)]):
            for nbits in range(1, SHIFT+1):
                mask = (1 << nbits) - 1
                lst = []
                got = x
                while got > 0:
                    lst.append(int(got & mask))
                    got >>= nbits
                f1 = rbigint.from_list_n_bits(lst, nbits)
                assert f1.tolong() == x

    def test_bitwise(self):
        for x in gen_signs(long_vals):
            lx = rbigint.fromlong(x)
            for y in gen_signs(long_vals):
                ly = rbigint.fromlong(y)
                for mod in "xor and_ or_".split():
                    res1 = getattr(lx, mod)(ly).tolong()
                    res2 = getattr(operator, mod)(x, y)
                    assert res1 == res2

    def test_int_bitwise(self):
        for x in gen_signs(long_vals):
            lx = rbigint.fromlong(x)
            for y in signed_int_vals:
                for mod in "xor and_ or_".split():
                    res1 = getattr(lx, 'int_' + mod)(y).tolong()
                    res2 = getattr(operator, mod)(x, y)
                    assert res1 == res2

    def test_mul_eq_shift(self):
        p2 = rbigint.fromlong(1).lshift(63)
        f1 = rbigint.fromlong(0).lshift(63)
        f2 = rbigint.fromlong(0).mul(p2)
        assert f1.eq(f2)

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
        x = rbigint.fromlong(-18471379832321000000000000000000000000000000000000000000)
        assert x.str() == '-18471379832321000000000000000000000000000000000000000000'
        assert x.repr() == '-18471379832321000000000000000000000000000000000000000000L'
        assert x.hex() == '-0xc0d9a6f41fbcf1718b618443d45516a051e40000000000L'
        assert x.oct() == '-014033151572037571705614266060420752125055201217100000000000000L'

    def test_format_caching(self):
        big = rbigint.fromlong(2 ** 1000)
        res1 = big.str()
        oldpow = rbigint.__dict__['pow']
        rbigint.pow = None
        # make sure pow is not used the second time
        try:
            res2 = big.str()
            assert res2 == res1
        finally:
            rbigint.pow = oldpow

    def test_overzealous_assertion(self):
        a = rbigint.fromlong(-1<<10000)
        b = rbigint.fromlong(-1<<3000)
        assert a.mul(b).tolong() == (-1<<10000)*(-1<<3000)

    def test_bit_length(self):
        assert rbigint.fromlong(0).bit_length() == 0
        assert rbigint.fromlong(1).bit_length() == 1
        assert rbigint.fromlong(2).bit_length() == 2
        assert rbigint.fromlong(3).bit_length() == 2
        assert rbigint.fromlong(4).bit_length() == 3
        assert rbigint.fromlong(-3).bit_length() == 2
        assert rbigint.fromlong(-4).bit_length() == 3
        assert rbigint.fromlong(1<<40).bit_length() == 41

    def test_hash(self):
        for i in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
                  sys.maxint-3, sys.maxint-2, sys.maxint-1, sys.maxint,
                  ]:
            # hash of machine-sized integers
            assert rbigint.fromint(i).hash() == i
            # hash of negative machine-sized integers
            assert rbigint.fromint(-i-1).hash() == -i-1
        #

    def test_log(self):
        from rpython.rlib.rfloat import ulps_check
        for op in long_vals:
            for base in [0, 2, 4, 8, 16, 10, math.e]:
                if not op:
                    with pytest.raises(ValueError):
                        rbigint.fromlong(op).log(base)
                    continue
                l = rbigint.fromlong(op).log(base)
                if base:
                    assert ulps_check(l, math.log(op, base)) is None
                else:
                    assert ulps_check(l, math.log(op)) is None

    def test_log2(self):
        assert rbigint.fromlong(1).log(2.0) == 0.0
        assert rbigint.fromlong(2).log(2.0) == 1.0
        assert rbigint.fromlong(2**1023).log(2.0) == 1023.0

    def test_frombytes(self):
        bigint = rbigint.frombytes('', byteorder='big', signed=True)
        assert bigint.tolong() == 0
        s = "\xFF\x12\x34\x56"
        bigint = rbigint.frombytes(s, byteorder="big", signed=False)
        assert bigint.tolong() == 0xFF123456
        bigint = rbigint.frombytes(s, byteorder="little", signed=False)
        assert bigint.tolong() == 0x563412FF
        s = "\xFF\x02\x03\x04\x05\x06\x07\x08\x09\x10\x11\x12\x13\x14\x15\xFF"
        bigint = rbigint.frombytes(s, byteorder="big", signed=False)
        assert s == bigint.tobytes(16, byteorder="big", signed=False)
        with pytest.raises(InvalidEndiannessError):
            bigint.frombytes('\xFF', 'foo', signed=True)
        bigint = rbigint.frombytes('\x82', byteorder='big', signed=True)
        assert bigint.tolong() == -126

    def test_tobytes(self):
        assert rbigint.fromint(0).tobytes(1, 'big', signed=True) == '\x00'
        assert rbigint.fromint(1).tobytes(2, 'big', signed=True) == '\x00\x01'
        with pytest.raises(OverflowError):
            rbigint.fromint(255).tobytes(1, 'big', signed=True)
        assert rbigint.fromint(-129).tobytes(2, 'big', signed=True) == '\xff\x7f'
        assert rbigint.fromint(-129).tobytes(2, 'little', signed=True) == '\x7f\xff'
        assert rbigint.fromint(65535).tobytes(3, 'big', signed=True) == '\x00\xff\xff'
        assert rbigint.fromint(-65536).tobytes(3, 'little', signed=True) == '\x00\x00\xff'
        assert rbigint.fromint(65535).tobytes(2, 'big', signed=False) == '\xff\xff'
        assert rbigint.fromint(-8388608).tobytes(3, 'little', signed=True) == '\x00\x00\x80'
        i = rbigint.fromint(-8388608)
        with pytest.raises(InvalidEndiannessError):
            i.tobytes(3, 'foo', signed=True)
        with pytest.raises(InvalidSignednessError):
            i.tobytes(3, 'little', signed=False)
        with pytest.raises(OverflowError):
            i.tobytes(2, 'little', signed=True)

    def test_gcd(self):
        assert gcd_binary(2*3*7**2, 2**2*7) == 2*7
        pytest.raises(ValueError, gcd_binary, 2*3*7**2, -2**2*7)
        assert gcd_binary(1234, 5678) == 2
        assert gcd_binary(13, 13**6) == 13
        assert gcd_binary(12, 0) == 12
        assert gcd_binary(0, 0) == 0
        with pytest.raises(ValueError):
            gcd_binary(-10, 0)
        with pytest.raises(ValueError):
            gcd_binary(10, -10)

        x = rbigint.fromlong(9969216677189303386214405760200)
        y = rbigint.fromlong(16130531424904581415797907386349)
        g = x.gcd(y)
        assert g == rbigint.fromlong(1)

        for x in gen_signs([12843440367927679363613699686751681643652809878241019930204617606850071260822269719878805]):
            x = rbigint.fromlong(x)
            for y in gen_signs([12372280584571061381380725743231391746505148712246738812788540537514927882776203827701778968535]):
                y = rbigint.fromlong(y)
                g = x.gcd(y)
                assert g.tolong() == 18218089570126697993340888567155155527541105


class TestInternalFunctions(object):
    def test__inplace_divrem1(self):
        # signs are not handled in the helpers!
        for x, y in [(1238585838347L, 3), (1234123412311231L, 1231231), (99, 100)]:
            if y > MASK:
                continue
            f1 = rbigint.fromlong(x)
            f2 = y
            remainder = lobj._inplace_divrem1(f1, f1, f2)
            f1._normalize()
            assert (f1.tolong(), remainder) == divmod(x, y)
        out = bigint([99, 99], 1)
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
            y = long(randint(1, 1 << 60))
            y <<= 60
            y += randint(1, 1 << 60)
            if y > x:
                x <<= 100

            f1 = rbigint.fromlong(x)
            f2 = rbigint.fromlong(y)
            div, rem = lobj._x_divrem(f1, f2)
            _div, _rem = divmod(x, y)
            assert div.tolong() == _div
            assert rem.tolong() == _rem

    def test__x_divrem2(self):
        Rx = 1 << 130
        Rx2 = 1 << 150
        Ry = 1 << 127
        Ry2 = 1 << 150
        for i in range(10):
            x = long(randint(Rx, Rx2))
            y = long(randint(Ry, Ry2))
            f1 = rbigint.fromlong(x)
            f2 = rbigint.fromlong(y)
            div, rem = lobj._x_divrem(f1, f2)
            _div, _rem = divmod(x, y)
            assert div.tolong() == _div
            assert rem.tolong() == _rem

    def test_divmod(self):
        x = 12345678901234567890L
        for i in range(100):
            y = long(randint(0, 1 << 60))
            y <<= 60
            y += randint(0, 1 << 60)
            for sx, sy in (1, 1), (1, -1), (-1, -1), (-1, 1):
                sx *= x
                sy *= y
                f1 = rbigint.fromlong(sx)
                f2 = rbigint.fromlong(sy)
                div, rem = f1.divmod(f2)
                _div, _rem = divmod(sx, sy)
                assert div.tolong() == _div
                assert rem.tolong() == _rem
        with pytest.raises(ZeroDivisionError):
            rbigint.fromlong(x).divmod(rbigint.fromlong(0))

        # an explicit example for a very rare case in _x_divrem:
        # "add w back if q was too large (this branch taken rarely)"
        x = 2401064762424988628303678384283622960038813848808995811101817752058392725584695633
        y = 510439143470502793407446782273075179624699774495710665331026
        f1 = rbigint.fromlong(x)
        f2 = rbigint.fromlong(y)
        div, rem = f1.divmod(f2)
        _div, _rem = divmod(x, y)
        assert div.tolong() == _div
        assert rem.tolong() == _rem

    def test_divmod_big_bug(self):
        a = -0x13131313131313131313cfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfcfd0
        b = -0x131313131313131313d0
        ra = rbigint.fromlong(a)
        rb = rbigint.fromlong(b)
        oldval = HOLDER.DIV_LIMIT
        try:
            HOLDER.DIV_LIMIT = 2 # set limit low to test divmod_big more
            rdiv, rmod = divmod_big(ra, rb)
            div, mod = divmod(a, b)
            assert rdiv.tolong() == div
            assert rmod.tolong() == mod
        finally:
            HOLDER.DIV_LIMIT = oldval

    def test_int_divmod(self):
        for x in long_vals:
            for y in int_vals + [-sys.maxint-1]:
                if not y:
                    continue
                for sx, sy in (1, 1), (1, -1), (-1, -1), (-1, 1):
                    sx *= x
                    sy *= y
                    if sy == sys.maxint + 1:
                        continue
                    f1 = rbigint.fromlong(sx)
                    div, rem = f1.int_divmod(sy)
                    div1, rem1 = f1.divmod(rbigint.fromlong(sy))
                    _div, _rem = divmod(sx, sy)
                    assert div1.tolong() == _div
                    assert rem1.tolong() == _rem
                    assert div.tolong() == _div
                    assert rem.tolong() == _rem
        with pytest.raises(ZeroDivisionError):
            rbigint.fromlong(x).int_divmod(0)

    # testing Karatsuba stuff
    def test__v_iadd(self):
        f1 = bigint([lobj.MASK] * 10, 1)
        f2 = bigint([1], 1)
        carry = lobj._v_iadd(f1, 1, len(f1._digits)-1, f2, 1)
        assert carry == 1
        assert f1.tolong() == lobj.MASK

    def test__v_isub(self):
        f1 = bigint([lobj.MASK] + [0] * 9 + [1], 1)
        f2 = bigint([1], 1)
        borrow = lobj._v_isub(f1, 1, len(f1._digits)-1, f2, 1)
        assert borrow == 0
        assert f1.tolong() == (1 << lobj.SHIFT) ** 10 - 1

    def test__kmul_split(self):
        split = 5
        diglo = [0] * split
        dighi = [lobj.MASK] * split
        f1 = bigint(diglo + dighi, 1)
        hi, lo = lobj._kmul_split(f1, split)
        assert lo._digits == [_store_digit(0)]
        assert hi._digits == map(_store_digit, dighi)

    def test__k_mul(self):
        digs = KARATSUBA_CUTOFF * 5
        f1 = bigint([lobj.MASK] * digs, 1)
        f2 = lobj._x_add(f1, bigint([1], 1))
        ret = lobj._k_mul(f1, f2)
        assert ret.tolong() == f1.tolong() * f2.tolong()

    def test_longlong(self):
        max = 1L << (r_longlong.BITS-1)
        f1 = rbigint.fromlong(max-1)    # fits in r_longlong
        f2 = rbigint.fromlong(-max)     # fits in r_longlong
        f3 = rbigint.fromlong(max)      # overflows
        f4 = rbigint.fromlong(-max-1)   # overflows
        assert f1.tolonglong() == max-1
        assert f2.tolonglong() == -max
        with pytest.raises(OverflowError):
            f3.tolonglong()
        with pytest.raises(OverflowError):
            f4.tolonglong()

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

    def test_toulonglong(self):
        with pytest.raises(ValueError):
            rbigint.fromlong(-1).toulonglong()

    def test_fits_int(self):
        assert rbigint.fromlong(0).fits_int()
        assert rbigint.fromlong(42).fits_int()
        assert rbigint.fromlong(-42).fits_int()
        assert rbigint.fromlong(sys.maxint).fits_int()
        assert not rbigint.fromlong(sys.maxint + 1).fits_int()
        assert rbigint.fromlong(-sys.maxint - 1).fits_int()
        assert not rbigint.fromlong(-sys.maxint - 2).fits_int()
        assert not rbigint.fromlong(-73786976294838206459).fits_int()
        assert not rbigint.fromlong(1 << 1000).fits_int()

    def test_parse_digit_string(self):
        from rpython.rlib.rbigint import parse_digit_string
        class Parser:
            def __init__(self, base, sign, digits):
                self.base = base
                self.sign = sign
                self.i = 0
                self._digits = digits
                self.start = 0
                self.end = len(digits)
            def next_digit(self):
                i = self.i
                if i == len(self._digits):
                    return -1
                self.i = i + 1
                return self._digits[i]
            def prev_digit(self):
                i = self.i - 1
                assert i >= 0
                self.i = i
                return self._digits[i]
        x = parse_digit_string(Parser(10, 1, [6]))
        assert x.eq(rbigint.fromint(6))
        x = parse_digit_string(Parser(10, 1, [6, 2, 3]))
        assert x.eq(rbigint.fromint(623))
        x = parse_digit_string(Parser(10, -1, [6, 2, 3]))
        assert x.eq(rbigint.fromint(-623))
        x = parse_digit_string(Parser(16, 1, [0xA, 0x4, 0xF]))
        assert x.eq(rbigint.fromint(0xA4F))
        num = 0
        for i in range(36):
            x = parse_digit_string(Parser(36, 1, range(i)))
            assert x.eq(rbigint.fromlong(num))
            num = num * 36 + i
        x = parse_digit_string(Parser(16, -1, range(15,-1,-1)*99))
        assert x.eq(rbigint.fromlong(long('-0x' + 'FEDCBA9876543210'*99, 16)))
        assert x.tobool() is True
        x = parse_digit_string(Parser(7, 1, [0, 0, 0]))
        assert x.tobool() is False
        x = parse_digit_string(Parser(7, -1, [0, 0, 0]))
        assert x.tobool() is False

        for base in [2, 4, 8, 16, 32]:
            for inp in [[0], [1], [1, 0], [0, 1], [1, 0, 1], [1, 0, 0, 1],
                        [1, 0, 0, base-1, 0, 1], [base-1, 1, 0, 0, 0, 1, 0],
                        [base-1]]:
                inp = inp * 97
                x = parse_digit_string(Parser(base, -1, inp))
                num = sum(inp[i] * (base ** (len(inp)-1-i))
                          for i in range(len(inp)))
                assert x.eq(rbigint.fromlong(-num))


BASE = 2 ** SHIFT

class TestTranslatable(object):
    def test_square(self):
        def test():
            xlo = rbigint.fromint(1410065408)
            xhi = rbigint.fromint(4)
            x = xlo.or_(xhi.lshift(31))
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
        from rpython.rlib.rarithmetic import r_int
        from rpython.rlib.unroll import unrolling_iterable
        from rpython.rtyper.lltypesystem.rffi import r_int_real, r_uint_real
        classlist = platform.numbertype_to_rclass.values()
        cases = [] # tuples of (values, strvalues, typename)
        for r in classlist:
            if r in (r_int, r_int_real, r_uint_real):  # and also r_longlong on 64-bit
                continue
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
            results = [str(long(x)) for x in values]
            cases.append((values, results, str(r)))
        cases = unrolling_iterable(cases)
        def fn():
            for values, results, typname in cases:
                for i in range(len(values)):
                    n = rbigint.fromrarith_int(values[i])
                    n = rbigint.fromrarith_int(values[i])
                    if n.str() != results[i]:
                        return typname + str(i)
            return None
        res = interpret(fn, [])
        assert not res

    def test_truediv_overflow(self):
        overflowing = 2**1024 - 2**(1024-53-1)
        op1 = rbigint.fromlong(overflowing)

        def fn():
            try:
                return op1.truediv(rbigint.fromint(1))
            except OverflowError:
                return -42.0

        res = interpret(fn, [])
        assert res == -42.0

    def test_isqrt(self):
        def fn(x):
            num = rbigint.fromint(3).int_pow(x)
            return num.mul(num).isqrt().eq(num)


        res = interpret(fn, [100])
        assert res == True

    def test_mul_int_int_rbigint_result(self):
        def fn(x, y):
            res = rbigint.mul_int_int_bigint_result(x, y)
            return len(res.str())
        res = interpret(fn, [sys.maxint, sys.maxint])


class TestTranslated(StandaloneTests):

    def test_gcc_4_9(self):
        MIN = -sys.maxint-1

        def entry_point(argv):
            print rbigint.fromint(MIN+1)._digits
            print rbigint.fromint(MIN)._digits
            return 0

        t, cbuilder = self.compile(entry_point)
        data = cbuilder.cmdexec('hi there')
        if SHIFT == LONG_BIT-1:
            assert data == '[%d]\n[0, 1]\n' % sys.maxint
        else:
            # assume 64-bit without native 128-bit type
            assert data == '[%d, %d, 1]\n[0, 0, 2]\n' % (2**31-1, 2**31-1)

class TestHypothesis(object):
    @given(longs, longs, longs)
    def test_pow(self, x, y, z):
        f1 = rbigint.fromlong(x)
        f2 = rbigint.fromlong(y)
        f3 = rbigint.fromlong(z)
        try:
            res = pow(x, y, z)
        except Exception as e:
            with pytest.raises(type(e)):
                f1.pow(f2, f3)
        else:
            v1 = f1.pow(f2, f3)
            try:
                v2 = f1.int_pow(f2.toint(), f3)
            except OverflowError:
                pass
            else:
                assert v2.tolong() == res
            assert v1.tolong() == res

    @given(biglongs, biglongs)
    @example(510439143470502793407446782273075179618477362188870662225920,
             108089693021945158982483698831267549521)
    def test_divmod(self, x, y):
        if x < y:
            x, y = y, x

        f1 = rbigint.fromlong(x)
        f2 = rbigint.fromlong(y)
        try:
            res = divmod(x, y)
        except Exception as e:
            with pytest.raises(type(e)):
                f1.divmod(f2)
        else:
            a, b = f1.divmod(f2)
            assert (a.tolong(), b.tolong()) == res

    @given(biglongs, biglongs)
    @example(510439143470502793407446782273075179618477362188870662225920,
             108089693021945158982483698831267549521)
    def test_divmod_small(self, x, y):
        if x < y:
            x, y = y, x

        f1 = rbigint.fromlong(x)
        f2 = rbigint.fromlong(y)
        try:
            res = divmod(x, y)
        except Exception as e:
            with pytest.raises(type(e)):
                f1._divmod_small(f2)
        else:
            a, b = f1._divmod_small(f2)
            assert (a.tolong(), b.tolong()) == res


    @given(biglongs, biglongs)
    @example(510439143470502793407446782273075179618477362188870662225920,
             108089693021945158982483698831267549521)
    @example(51043991434705027934074467822730751796184773621888706622259209143470502793407446782273075179618477362188870662225920143470502793407446782273075179618477362188870662225920,
             10808)
    @example(17, 257)
    @example(510439143470502793407446782273075179618477362188870662225920L, 108089693021945158982483698831267549521L)
    def test_divmod_big(self, x, y):
        oldval = HOLDER.DIV_LIMIT
        try:
            HOLDER.DIV_LIMIT = 2 # set limit low to test divmod_big more
            if x < y:
                x, y = y, x

            # boost size
            x *= 3 ** (HOLDER.DIV_LIMIT * SHIFT * 5) - 1
            y *= 2 ** (HOLDER.DIV_LIMIT * SHIFT * 5) - 1

            f1 = rbigint.fromlong(x)
            f2 = rbigint.fromlong(y)
            try:
                res = divmod(x, y)
            except Exception as e:
                with pytest.raises(type(e)):
                    divmod_big(f1, f2)
            else:
                a, b = divmod_big(f1, f2)
                assert (a.tolong(), b.tolong()) == res
        finally:
            HOLDER.DIV_LIMIT = oldval

    @given(tuples_biglongs_for_division)
    def test_divmod_consistency(self, tup):
        lx, ly = tup
        ly = ly or 1
        x = rbigint.fromlong(lx)
        y = rbigint.fromlong(ly)
        q, r = x.divmod(y)
        q2, r2 = x.floordiv(y), x.mod(y)
        pab, pba = x.mul(y), y.mul(x)
        assert pab.eq(pba)
        assert q.eq(q2)
        assert r.eq(r2)
        assert x.eq(q.mul(y).add(r))
        if y.int_gt(0):
            assert r.lt(y)
            assert r.int_ge(0)
        else:
            assert y.lt(r)
            assert y.int_le(0)

    @given(biglongs, ints)
    def test_int_divmod(self, x, iy):
        f1 = rbigint.fromlong(x)
        try:
            res = divmod(x, iy)
        except Exception as e:
            with pytest.raises(type(e)):
                f1.int_divmod(iy)
        else:
            a, b = f1.int_divmod(iy)
            assert (a.tolong(), b.tolong()) == res

    @given(longs)
    def test_hash(self, x):
        # hash of large integers: should be equal to the hash of the
        # integer reduced modulo 2**64-1, to make decimal.py happy
        x = abs(x)
        y = x % (2**64-1)
        assert rbigint.fromlong(x).hash() == rbigint.fromlong(y).hash()
        assert rbigint.fromlong(-x).hash() == rbigint.fromlong(-y).hash()

    @given(ints)
    def test_hash_int(self, x):
        # hash of machine-sized integers
        assert rbigint.fromint(x).hash() == x
        # hash of negative machine-sized integers
        assert rbigint.fromint(-x-1).hash() == -x-1

    @given(longs)
    def test_abs(self, x):
        assert rbigint.fromlong(x).abs().tolong() == abs(x)

    @given(longs, longs)
    def test_truediv(self, a, b):
        ra = rbigint.fromlong(a)
        rb = rbigint.fromlong(b)
        if not b:
            with pytest.raises(ZeroDivisionError):
                ra.truediv(rb)
        else:
            assert repr(ra.truediv(rb)) == repr(a / b)

    @given(longs, longs)
    def test_bitwise_and_mul(self, x, y):
        lx = rbigint.fromlong(x)
        ly = rbigint.fromlong(y)
        for mod in "xor and_ or_ mul".split():
            res1a = getattr(lx, mod)(ly).tolong()
            res1b = getattr(ly, mod)(lx).tolong()
            res2 = getattr(operator, mod)(x, y)
            assert res1a == res2

    @given(longs, ints)
    def test_int_bitwise_and_mul(self, x, y):
        lx = rbigint.fromlong(x)
        for mod in "xor and_ or_ mul".split():
            res1 = getattr(lx, 'int_' + mod)(y).tolong()
            res2 = getattr(operator, mod)(x, y)
            assert res1 == res2

    @given(longs, ints)
    def test_int_comparison(self, x, y):
        lx = rbigint.fromlong(x)
        assert lx.int_lt(y) == (x < y)
        assert lx.int_eq(y) == (x == y)
        assert lx.int_le(y) == (x <= y)

    @given(longs, longs)
    def test_int_comparison2(self, x, y):
        lx = rbigint.fromlong(x)
        ly = rbigint.fromlong(y)
        assert lx.lt(ly) == (x < y)
        assert lx.eq(ly) == (x == y)
        assert lx.le(ly) == (x <= y)

    @given(ints, ints, ints)
    def test_gcd_binary(self, x, y, z):
        x, y, z = abs(x), abs(y), abs(z)

        def test(a, b, res):
            g = gcd_binary(a, b)

            assert g == res

        a, b = x, y
        while b:
            a, b = b, a % b

        gcd_x_y = a

        test(x, y, gcd_x_y)
        test(x, 0, x)
        test(0, x, x)
        test(x * z, y * z, gcd_x_y * z)
        test(x * z, z, z)
        test(z, y * z, z)

    @given(biglongs, biglongs, biglongs)
    @example(112233445566778899112233445566778899112233445566778899,
             13579246801357924680135792468013579246801,
             99887766554433221113)
    @settings(max_examples=10)
    def test_gcd(self, x, y, z):
        x, y, z = abs(x), abs(y), abs(z)

        def test(a, b, res):
            g = rbigint.fromlong(a).gcd(rbigint.fromlong(b)).tolong()

            assert g == res

        a, b = x, y
        while b:
            a, b = b, a % b

        gcd_x_y = a

        test(x, y, gcd_x_y)
        test(x * z, y * z, gcd_x_y * z)
        test(x * z, z, z)
        test(z, y * z, z)
        test(x, 0, x)
        test(0, x, x)

    @given(ints)
    def test_longlong_roundtrip(self, x):
        try:
            rx = r_longlong(x)
        except OverflowError:
            pass
        else:
            assert rbigint.fromrarith_int(rx).tolonglong() == rx

    @given(longs)
    def test_unsigned_roundtrip(self, x):
        x = abs(x)
        rx = r_uint(x) # will wrap on overflow
        assert rbigint.fromrarith_int(rx).touint() == rx
        rx = r_ulonglong(x) # will wrap on overflow
        assert rbigint.fromrarith_int(rx).toulonglong() == rx

    @given(biglongs, biglongs)
    def test_mod(self, x, y):
        rx = rbigint.fromlong(x)
        ry = rbigint.fromlong(y)
        if not y:
            with pytest.raises(ZeroDivisionError):
                rx.mod(ry)
            return
        r1 = rx.mod(ry)
        r2 = x % y

        assert r1.tolong() == r2

    @given(biglongs, ints)
    def test_int_mod(self, x, y):
        rx = rbigint.fromlong(x)
        if not y:
            with pytest.raises(ZeroDivisionError):
                rx.int_mod(0)
            return
        r1 = rx.int_mod(y)
        r2 = x % y
        assert r1.tolong() == r2

    @given(biglongs, ints)
    def test_int_mod_int_result(self, x, y):
        rx = rbigint.fromlong(x)
        if not y:
            with pytest.raises(ZeroDivisionError):
                rx.int_mod_int_result(0)
            return
        r1 = rx.int_mod_int_result(y)
        r2 = x % y
        assert r1 == r2

    @given(longs, strategies.integers(0, 2000))
    def test_shift(self, x, shift):
        rx = rbigint.fromlong(x)
        r1 = rx.lshift(shift)
        assert r1.tolong() == x << shift

        r1 = rx.rshift(shift)
        assert r1.tolong() == x >> shift

    @given(longs, strategies.integers(0, 2000), strategies.data())
    def test_abs_rshift_and_mask(self, x, shift, data):
        mask = data.draw(
            strategies.sampled_from(
                [int((1 << i) - 1) for i in range(1, min(SHIFT, r_uint.BITS - 1))]))
        rx = rbigint.fromlong(x)
        r1 = rx.abs_rshift_and_mask(r_ulonglong(shift), mask)
        assert r1 == (abs(x) >> shift) & mask

    @given(biglongs, strategies.integers(min_value=1, max_value=10000))
    def test_str_to_int_big_base10(self, l, limit):
        l = abs(l)
        s = str(l)
        assert _str_to_int_big_base10(str(l), 0, len(s), limit).tolong() == l

    @given(biglongs)
    def test_fromstr(self, l):
        assert rbigint.fromstr(str(l)).tolong() == l

    @given(biglongs)
    def test_fromstr_str_consistency(self, l):
        assert rbigint.fromstr(rbigint.fromlong(l).str()).tolong() == l

    @given(biglongs)
    def test_fromstr_small_limit(self, l):
        # set limits to 2 to stress the recursive algorithm some more
        oldval = HOLDER.STR2INT_LIMIT
        oldval2 = HOLDER.MINSIZE_STR2INT
        try:
            HOLDER.STR2INT_LIMIT = 2
            HOLDER.MINSIZE_STR2INT = 1
            assert rbigint.fromstr(str(l)).tolong() == l
            assert rbigint.fromstr(str(l) + "_1", allow_underscores=True).tolong() == int(str(l) + '1')
        finally:
            HOLDER.STR2INT_LIMIT = oldval
            HOLDER.MINSIZE_STR2INT = 1

    @given(strategies.integers(min_value=1, max_value=10000), strategies.integers(min_value=1, max_value=10000))
    @settings(max_examples=10)
    def test_str_to_int_big_w5pow(self, exp, limit):
        mem = {}
        assert (_str_to_int_big_w5pow(exp, mem, limit).tolong() == 5 ** exp ==
                rbigint.fromint(5).int_pow(exp).tolong())

    @given(biglongs)
    def test_bit_count(self, val):
        assert rbigint.fromlong(val).bit_count() == bin(abs(val)).count("1")

    @given(strategies.binary(), strategies.booleans(), strategies.booleans())
    def test_frombytes_tobytes_hypothesis(self, s, big, signed):
        # check the roundtrip from binary strings to bigints and back
        byteorder = 'big' if big else 'little'
        bigint = rbigint.frombytes(s, byteorder=byteorder, signed=signed)
        t = bigint.tobytes(len(s), byteorder=byteorder, signed=signed)
        assert s == t

    @given(biglongs, biglongs, biglongs)
    def test_distributive(self, a, b, c):
        la = rbigint.fromlong(a)
        lb = rbigint.fromlong(b)
        lc = rbigint.fromlong(c)
        # a * (b + c) == a * b + a * c
        assert la.mul(lb.add(lc)).eq(la.mul(lb).add(la.mul(lc)))

    @given(biglongs, biglongs, biglongs)
    def test_associative(self, a, b, c):
        la = rbigint.fromlong(a)
        lb = rbigint.fromlong(b)
        lc = rbigint.fromlong(c)
        # a * (b * c) == (a * b) * c
        assert la.mul(lb.mul(lc)).eq(la.mul(lb).mul(lc))
        # a + (b + c) == (a + b) + c
        assert la.add(lb.add(lc)).eq(la.add(lb).add(lc))

    @given(biglongs, biglongs)
    def test_commutative(self, a, b):
        la = rbigint.fromlong(a)
        lb = rbigint.fromlong(b)
        # a * b == b * a
        assert la.mul(lb).eq(lb.mul(la))
        # a + b == b + a
        assert la.add(lb).eq(lb.add(la))

    @given(longs, strategies.integers(0, 100), strategies.integers(0, 100))
    @settings(max_examples=10)
    def test_pow_mul(self, a, b, c):
        la = rbigint.fromlong(a)
        lb = rbigint.fromlong(b)
        lc = rbigint.fromlong(c)
        # a ** (b + c) == a ** b * a ** c
        assert la.pow(lb.add(lc)).eq(la.pow(lb).mul(la.pow(lc)))

    @given(rarith_ints)
    def test_args_from_rarith_int(self, i):
        li = rbigint.fromrarith_int(i)
        assert li.tolong() == int(i)

    @given(biglongs)
    @example(3**100)
    def test_isqrt(self, a):
        a = abs(a)
        la = rbigint.fromlong(a)
        lsq = la.isqrt()
        sq = lsq.tolong()
        assert sq * sq <= a
        assert (sq + 1) ** 2 > a

        x = a * a
        lx = rbigint.fromlong(x)
        assert lx.isqrt().tolong() == a

    @given(ints, ints)
    def test_mul_int_int_rbigint_result(self, a, b):
        res = rbigint.mul_int_int_bigint_result(a, b)
        assert res.tolong() == a * b

    @given(strategies.data())
    def test_format_lowest_level_divmod_int_results(self, data):
        b = data.draw(strategies.integers(1, MASK))
        a = data.draw(strategies.integers(0, b-1))
        c = data.draw(strategies.integers(0, b-1))
        assume(bool(b))
        atimesbplusb = rbigint.mul_int_int_bigint_result(a, b).int_add(c)
        div, mod = _format_lowest_level_divmod_int_results(atimesbplusb, b)
        print a, b, c, atimesbplusb, div, mod
        assert (div, mod) == divmod(atimesbplusb.tolong(), b)

    @given(strategies.integers(0, 10**18-1))
    def test_format_int10_18digits(self, val):
        builder = StringBuilder()
        _format_int10_18digits(val, builder)
        s = builder.build()
        assert len(s) == 18
        assert s.lstrip('0') == str(val).lstrip('0')


@pytest.mark.parametrize(['methname'], [(methodname, ) for methodname in dir(TestHypothesis) if methodname.startswith("test_")])
def test_hypothesis_small_shift(methname):
    # run the TestHypothesis in a subprocess with a smaller SHIFT value
    # the idea is that this finds hopefully finds edge cases more easily
    import subprocess, os
    # The cwd on the buildbot is actually in rpython
    # Add the pypy basedir so we get the local pytest
    env = os.environ.copy()
    parent = os.path.dirname
    env['PYTHONPATH'] = parent(parent(parent(parent(__file__))))
    p = subprocess.Popen(" ".join([sys.executable, os.path.abspath(__file__), methname]),
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         shell=True, env=env)
    stdout, stderr = p.communicate()
    if p.returncode:
        print stdout
        print stderr
    assert not p.returncode

def _get_hacked_rbigint(shift):
    testpath = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(os.path.dirname(testpath), "rbigint.py")) as f:
        s = f.read()
    s = s.replace("SHIFT = 63", "SHIFT = %s" % (shift, ))
    s = s.replace("SHIFT = 31", "SHIFT = %s" % (shift, ))
    with open(os.path.join(testpath, "_hacked_rbigint.py"), "w") as f:
        f.write(s)

    from rpython.rlib.test import _hacked_rbigint
    assert _hacked_rbigint.SHIFT == shift
    return _hacked_rbigint

def run():
    shift = 9
    print "USING SHIFT", shift, sys.argv[1]
    _hacked_rbigint = _get_hacked_rbigint(shift)
    globals().update(_hacked_rbigint.__dict__) # emulate import *
    assert SHIFT == shift
    t = TestHypothesis()
    try:
        getattr(t, sys.argv[1])()
    except:
        if "--pdb" in sys.argv:
            import traceback, pdb
            info = sys.exc_info()
            print(traceback.format_exc())
            pdb.post_mortem(info[2], pdb.Pdb)
        raise


if __name__ == '__main__':
    run()
