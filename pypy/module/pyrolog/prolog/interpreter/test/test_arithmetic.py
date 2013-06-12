import py
import sys
from prolog.interpreter.parsing import parse_file, TermBuilder
from prolog.interpreter.parsing import parse_query_term, get_engine
from prolog.interpreter.error import UnificationFailed
from prolog.interpreter.continuation import Heap, Engine
from prolog.interpreter import error
from prolog.interpreter.test.tool import collect_all, assert_false, assert_true
from prolog.interpreter.term import Number, Float, BigInt
import prolog.interpreter.arithmetic # has side-effects, changes Number etc

from rpython.rlib.rbigint import rbigint

def is_64_bit():
    return sys.maxint > 2147483647

class TestArithmeticMethod(object):
    def test_add(self):
        f1 = Float(5.1)
        f2 = Float(10.1)
        assert f1.arith_add(f2).floatval == 15.2

        n0 = Number(1)
        n1 = Number(2)
        assert n0.arith_add(n1).num == 3

        n2 = Number(2)
        f3 = Float(3.2)
        assert n2.arith_add(f3).floatval == 5.2
        assert f3.arith_add(n2).floatval == 5.2

        b1 = BigInt(rbigint.fromdecimalstr('50000000000000000000000'))
        b2 = BigInt(rbigint.fromdecimalstr('10000000000000000000001'))
        assert b1.arith_add(b2).value.str() == '60000000000000000000001'

        n3 = Number(sys.maxint)
        assert n3.arith_add(n0).value.str() == str(sys.maxint + 1)

        b = BigInt(rbigint.fromdecimalstr('100000000000000000000000000000'))
        f = Float(1.5)
        assert b.arith_add(f).floatval == 100000000000000000000000000001.5
        assert f.arith_add(b).floatval == 100000000000000000000000000001.5

        assert b.arith_add(n0).value.tofloat() == 100000000000000000000000000001.0
        assert n0.arith_add(b).value.tofloat() == 100000000000000000000000000001.0


    def test_sub(self):
        n1 = Number(5)
        n2 = Number(10)
        assert n1.arith_sub(n2).num == -5
        assert n2.arith_sub(n1).num == 5

        f1 = Float(10.5)
        f2 = Float(30.6)
        assert f1.arith_sub(f2).floatval == -20.1
        assert f2.arith_sub(f1).floatval == 20.1

        b1 = BigInt(rbigint.fromdecimalstr('10000000000000000000000000000000000000'))
        b2 = BigInt(rbigint.fromdecimalstr('20000000000000000000000000000000000000'))
        assert b1.arith_sub(b2).value.tofloat() == -10000000000000000000000000000000000000.0
        assert b2.arith_sub(b1).value.tofloat() == 10000000000000000000000000000000000000.0
        assert BigInt(rbigint.fromdecimalstr('100000000000000000000')).arith_sub(Number(1)).value.str() == '99999999999999999999'
        assert Number(5).arith_sub(BigInt(rbigint.fromdecimalstr('5'))).num == 0
        assert BigInt(rbigint.fromdecimalstr('1000000000000000')).arith_sub(Float(500000000000000)).floatval == 500000000000000.0
        assert Float(2000000000000000).arith_sub(BigInt(rbigint.fromdecimalstr('1000000000000000'))).floatval == 1000000000000000.0


    def test_mul(self):
        assert Number(5).arith_mul(Number(100)).num == 500
        assert Number(5).arith_mul(BigInt(rbigint.fromdecimalstr('1000000000000000000000000000000'))).value.tofloat() == 5000000000000000000000000000000.0
        assert Number(-10).arith_mul(Float(-7.3)).floatval == 73
        assert BigInt(rbigint.fromdecimalstr('-1000000000000000000000000000')).arith_mul(BigInt(rbigint.fromdecimalstr('100000000000000000000'))).value.str() == '-100000000000000000000000000000000000000000000000'
        assert Float(6.7).arith_mul(Float(-2.4)).floatval == -16.08
        assert Float(6.7).arith_mul(BigInt(rbigint.fromdecimalstr('100000000000000000000000000000000000'))).floatval == 670000000000000000000000000000000000.0
        assert BigInt(rbigint.fromdecimalstr('100000000000000000000000000000000000')).arith_mul(Float(6.7)).floatval == 670000000000000000000000000000000000.0
        assert Number(2).arith_mul(Float(2.5)).floatval == 5
        assert Float(2.5).arith_mul(Number(2)).floatval == 5

    def test_div(self):
        assert Number(5).arith_div(Number(2)).num == 2
        assert Number(15).arith_div(Number(5)).num == 3
        assert Number(5).arith_div(Float(2.5)).floatval == 2.0
        assert Float(2.5).arith_div(Number(5)).floatval == 0.5
        assert Float(-10).arith_div(Float(2.5)).floatval == -4.0
        assert BigInt(rbigint.fromdecimalstr('50000000000000000')).arith_div(BigInt(rbigint.fromdecimalstr('25000000000000000'))).num == 2
        assert BigInt(rbigint.fromdecimalstr('100000000000000000000')).arith_div(Float(100000000000000000000.0)).floatval == 1.0
        assert Float(100000000000000000000).arith_div(BigInt(rbigint.fromdecimalstr('100000000000000000000'))).floatval == 1.0
        assert Number(5).arith_div(BigInt(rbigint.fromdecimalstr('5'))).num == 1
        assert BigInt(rbigint.fromdecimalstr('5')).arith_div(Number(5)).num == 1

        py.test.raises(ZeroDivisionError, 'BigInt(rbigint.fromdecimalstr(\'1\')).arith_div(BigInt(rbigint.fromdecimalstr(\'0\')))')
        py.test.raises(ZeroDivisionError, 'BigInt(rbigint.fromdecimalstr(\'1\')).arith_div(Number(0))')
        py.test.raises(ZeroDivisionError, 'BigInt(rbigint.fromdecimalstr(\'1\')).arith_div(Float(0))')
        py.test.raises(ZeroDivisionError, 'Float(1).arith_div(Number(0))')
        py.test.raises(ZeroDivisionError, 'Number(1).arith_div(Number(0))')
        py.test.raises(ZeroDivisionError, 'Number(1).arith_div(Float(0))')

    def test_floordiv(self):
        assert Number(5).arith_floordiv(Number(2)).num == 2
        assert Number(15).arith_floordiv(Number(5)).num == 3
        py.test.raises(error.CatchableError, "Number(5).arith_floordiv(Float(2.5))")
        py.test.raises(error.CatchableError, "Float(2.5).arith_floordiv(Number(5))")
        py.test.raises(error.CatchableError, "Float(-10).arith_floordiv(Float(2.5))")
        assert BigInt(rbigint.fromdecimalstr('50000000000000000')).arith_floordiv(BigInt(rbigint.fromdecimalstr('25000000000000000'))).num == 2
        py.test.raises(error.CatchableError, "BigInt(rbigint.fromdecimalstr('100000000000000000000')).arith_floordiv(Float(100000000000000000000.0))")
        py.test.raises(error.CatchableError, "Float(100000000000000000000).arith_floordiv(BigInt(rbigint.fromdecimalstr('100000000000000000000')))")
        assert Number(5).arith_floordiv(BigInt(rbigint.fromdecimalstr('5'))).num == 1
        assert BigInt(rbigint.fromdecimalstr('5')).arith_floordiv(Number(5)).num == 1

        py.test.raises(ZeroDivisionError, 'BigInt(rbigint.fromdecimalstr(\'1\')).arith_floordiv(BigInt(rbigint.fromdecimalstr(\'0\')))')
        py.test.raises(ZeroDivisionError, 'BigInt(rbigint.fromdecimalstr(\'1\')).arith_floordiv(Number(0))')
        py.test.raises(ZeroDivisionError, 'Number(1).arith_floordiv(Number(0))')

    def test_power(self):
        assert Number(5).arith_pow(Number(2)).num == 25
        assert Float(2.3).arith_pow(Float(3.1)).floatval == 13.223800591254721
        assert BigInt(rbigint.fromdecimalstr('1000000')).arith_pow(Number(4)).value.str() == '1000000000000000000000000'
        assert Float(10.0).arith_pow(BigInt(rbigint.fromdecimalstr('10'))).floatval == 10000000000.0
        assert BigInt(rbigint.fromdecimalstr('10')).arith_pow(Float(10.0)).floatval == 10000000000.0

        assert BigInt(rbigint.fromdecimalstr('1000000000000000')).arith_pow(Number(0)).num == 1
        assert Float(10000000000).arith_pow(BigInt(rbigint.fromdecimalstr('0'))).floatval == 1.0

    def test_shr(self):
        assert Number(8).arith_shr(Number(2)).num == 2
        assert BigInt(rbigint.fromint(256)).arith_shr(Number(5)).num == 8
        assert BigInt(rbigint.fromint(256)).arith_shr(BigInt(rbigint.fromint(5))).num == 8
        assert Number(256).arith_shr(BigInt(rbigint.fromint(5))).num == 8

        py.test.raises(ValueError, 'BigInt(rbigint.fromint(2)).arith_shr(BigInt(rbigint.fromdecimalstr(\'100000000000000000000000000000000000000000000000\')))')

    def test_shl(self):
        assert Number(2).arith_shl(Number(5)).num == 64
        assert BigInt(rbigint.fromint(1000)).arith_shl(Number(1)).num == 2000
        assert BigInt(rbigint.fromint(1000)).arith_shl(BigInt(rbigint.fromint(1))).num == 2000
        assert Number(1000).arith_shl(BigInt(rbigint.fromint(1))).num == 2000
        assert Number(1000).arith_shl(BigInt(rbigint.fromint(100))).value.str() == '1267650600228229401496703205376000'

    def test_or(self):
        assert Number(8).arith_or(Number(2)).num == 10
        assert BigInt(rbigint.fromint(256)).arith_or(Number(128)).num == 384
        assert BigInt(rbigint.fromdecimalstr('18446744073709551616')).arith_or(BigInt(rbigint.fromdecimalstr('9223372036854775808'))).value.str() == '27670116110564327424'
        assert Number(128).arith_or(BigInt(rbigint.fromint(256))).num == 384

    def test_and(self):
        assert Number(8).arith_and(Number(2)).num == 0
        assert BigInt(rbigint.fromint(46546)).arith_and(Number(34)).num == 2
        assert Number(46546).arith_and(BigInt(rbigint.fromint(34))).num == 2

    def test_xor(self):
        assert Number(8).arith_xor(Number(2)).num == 10
        assert BigInt(rbigint.fromint(46546)).arith_xor(Number(34)).num == 46576
        assert Number(46546).arith_xor(BigInt(rbigint.fromint(34))).num == 46576

    def test_mod(self):
        assert Number(8).arith_mod(Number(2)).num == 0
        assert BigInt(rbigint.fromint(46546)).arith_mod(Number(33)).num == 16
        assert Number(46546).arith_mod(BigInt(rbigint.fromint(33))).num == 16

        py.test.raises(ZeroDivisionError, 'BigInt(rbigint.fromdecimalstr("12342424234")).arith_mod(BigInt(rbigint.fromint(0)))')
        py.test.raises(ZeroDivisionError, 'Number(34535).arith_mod(BigInt(rbigint.fromint(0)))')
        py.test.raises(ZeroDivisionError, 'BigInt(rbigint.fromdecimalstr("12342424234")).arith_mod(Number(0))')

    def test_invert(self):
        assert Number(2345).arith_not().num == -2346
        assert BigInt(rbigint.fromdecimalstr('37846578346543875674385')).arith_not().value.str() == '-37846578346543875674386'

    def test_abs(self):
        assert Number(-345345345).arith_abs().num == 345345345
        assert Float(345345.435).arith_abs().floatval == 345345.435
        assert Float(-345345.435).arith_abs().floatval == 345345.435
        assert BigInt(rbigint.fromdecimalstr('-123123123123123123123123123')).arith_abs().value.str() == '123123123123123123123123123'

    def test_max(self):
        assert Number(5).arith_max(Number(1)).num == 5
        assert Float(-1.32).arith_max(Float(4.5)).floatval == 4.5
        assert BigInt(rbigint.fromdecimalstr('111111111111111111111111111')).arith_max(BigInt(rbigint.fromdecimalstr('222222222222222222222222222222'))).value.str() == '222222222222222222222222222222'
        assert Number(-1000).arith_max(BigInt(rbigint.fromint(-1001))).num == -1000
        assert BigInt(rbigint.fromint(-1001)).arith_max(Number(-1000)).num == -1000
        assert BigInt(rbigint.fromdecimalstr('10000')).arith_max(Float(20000)).floatval == 20000.0
        assert Float(20000).arith_max(BigInt(rbigint.fromdecimalstr('10000'))).floatval == 20000.0

    def test_min(self):
        assert Number(5).arith_min(Number(1)).num == 1
        assert Float(-1.32).arith_min(Float(4.5)).floatval == -1.32
        assert BigInt(rbigint.fromdecimalstr('111111111111111111111111111')).arith_min(BigInt(rbigint.fromdecimalstr('222222222222222222222222222222'))).value.str() == '111111111111111111111111111'
        assert Number(-1000).arith_min(BigInt(rbigint.fromint(-1001))).num == -1001
        assert BigInt(rbigint.fromint(-1001)).arith_min(Number(-1000)).num == -1001
        assert BigInt(rbigint.fromdecimalstr('10000')).arith_min(Float(20000)).floatval == 10000.0
        assert Float(20000).arith_min(BigInt(rbigint.fromdecimalstr('10000'))).floatval == 10000.0

    def test_float_misc(self):
        assert Float(7.4).arith_round().num == 7.0
        assert Float(7.5).arith_round().num == 8.0
        assert Float(7.4).arith_floor().num == 7.0
        assert Float(7.9).arith_floor().num == 7.0
        assert Float(7.4).arith_ceiling().num == 8.0
        assert Float(7.4).arith_float_fractional_part().floatval == 7.4 - 7
        assert Float(7.4).arith_float_integer_part().num == 7.0

    def test_data_types_32_bit(self):
        if is_64_bit():
            py.test.skip("only test on 32 bit")
        assert BigInt(rbigint.fromdecimalstr('348765738456378457436537854637845')).arith_mod(BigInt(rbigint.fromdecimalstr('845763478537534095'))).value.str() == '738607793931799615'
        assert BigInt(rbigint.fromdecimalstr('10')).arith_pow(BigInt(rbigint.fromdecimalstr('10'))).value.str() == '10000000000'
        assert BigInt(rbigint.fromdecimalstr('34876573845637845')).arith_xor(BigInt(rbigint.fromdecimalstr('845763478537534095'))).value.str() == '848692582328774746'
        assert BigInt(rbigint.fromdecimalstr('34876573845637845')).arith_and(BigInt(rbigint.fromdecimalstr('845763478537534095'))).value.str() == '15973735027198597'

def test_simple():
    assert_true("X is 1 + 2, X = 3.")
    assert_false("X is 1.1 + 2.8, X = 4.0.")
    assert_true("X is 1 - 2, X = -1.")
    assert_true("X is 2 * -2, X = -4.")
    assert_true("X is 2 * -2.1, X = -4.2.")
    assert_true("X is 2 + -2, X = 0.")
    assert_true("X is 2 / -2, X = -1.")

    assert_true("X is 1 << 4, X = 16.")
    assert_true("X is 128 >> 7, X = 1.")
    assert_true("X is 12 \\/ 10, X = 14.")
    assert_true("X is 12 /\\ 10, X = 8.")
    assert_true("X is 12 xor 10, X = 6.")

    assert_true("X is max(12, 13), X = 13.")
    assert_true("X is min(12, 13), X = 12.")
    assert_true("X is max(12, 13.9), X = 13.9.")
    assert_true("X is min(12.1, 13), X = 12.1.")

    assert_true("X is abs(42), X = 42.")
    assert_true("X is abs(-42), X = 42.")
    assert_true("X is abs(42.42), X = 42.42.")
    assert_true("X is abs(-42.42), X = 42.42.")

    assert_true("X is round(0), X = 0.")
    assert_true("X is round(0.3), X = 0.")
    assert_true("X is round(0.4), X = 0.")
    assert_true("X is round(0.5), X = 1.")
    assert_true("X is round(0.6), X = 1.")
    assert_true("X is round(1), X = 1.")
    assert_true("X is round(-0.3), X = 0.")
    assert_true("X is round(-0.4), X = 0.")
    assert_true("X is round(-0.5), X = -1.")
    assert_true("X is round(-0.6), X = -1.") 
    assert_true("X is round(-1), X = -1.")

    assert_true("X is ceiling(0), X = 0.")
    assert_true("X is ceiling(0.3), X = 1.")
    assert_true("X is ceiling(0.4), X = 1.")
    assert_true("X is ceiling(0.5), X = 1.")
    assert_true("X is ceiling(0.6), X = 1.")
    assert_true("X is ceiling(1), X = 1.")
    assert_true("X is ceiling(-0.3), X = 0.")
    assert_true("X is ceiling(-0.4), X = 0.")
    assert_true("X is ceiling(-0.5), X = 0.")
    assert_true("X is ceiling(-0.6), X = 0.")
    assert_true("X is ceiling(-1), X = -1.")

    assert_true("X is floor(0), X = 0.")
    assert_true("X is floor(0.3), X = 0.")
    assert_true("X is floor(0.4), X = 0.")
    assert_true("X is floor(0.5), X = 0.")
    assert_true("X is floor(0.6), X = 0.")
    assert_true("X is floor(1), X = 1.")
    assert_true("X is floor(-0.3), X = -1.")
    assert_true("X is floor(-0.4), X = -1.")
    assert_true("X is floor(-0.5), X = -1.")
    assert_true("X is floor(-0.6), X = -1.")
    assert_true("X is floor(-1), X = -1.")

    assert_true("X is float_integer_part(0), X = 0.")
    assert_true("X is float_integer_part(0.3), X = 0.")
    assert_true("X is float_integer_part(0.4), X = 0.")
    assert_true("X is float_integer_part(0.5), X = 0.")
    assert_true("X is float_integer_part(0.6), X = 0.")
    assert_true("X is float_integer_part(1), X = 1.")
    assert_true("X is float_integer_part(-0.3), X = 0.")
    assert_true("X is float_integer_part(-0.4), X = 0.")
    assert_true("X is float_integer_part(-0.5), X = 0.")
    assert_true("X is float_integer_part(-0.6), X = 0.")
    assert_true("X is float_integer_part(-1), X = -1.")

    assert_true("X is float_fractional_part(1), X = 0.")
    assert_true("X is float_fractional_part(2), X = 0.")
    assert_true("X is float_fractional_part(-1), X = 0.")
    assert_true("X is float_fractional_part(1.2), Y is 1.2 - 1, X = Y.")
    assert_true("X is float_fractional_part(1.4), Y is 1.4 - 1, X = Y.")
    assert_true("X is float_fractional_part(1.6), Y is 1.6 - 1, X = Y.")
    assert_true("X is float_fractional_part(-1.2), X is -1.2 + 1, X = Y.")
    assert_true("X is float_fractional_part(-1.4), X is -1.4 + 1, X = Y.")
    assert_true("X is float_fractional_part(-1.6), X is -1.6 + 1, X = Y.")

    assert_true("X is 2 ** 4, X = 16.")
    assert_true("X is 100 ** 0.0, X = 1.0.")
    assert_true("X is 0 ** 0, X = 1.")

def test_comparison():
    assert_true("1 =:= 1.0.")
    assert_true("1 + 1 > 1.")
    assert_true("1 + 0.001 >= 1 + 0.001.")
    assert_true("1 + 0.001 =< 1 + 0.001.")
    assert_false("1 > 1.")
    assert_true("1.1 > 1.")
    assert_false("1 =\\= 1.0.")
    assert_true("1 =\\= 32.")
