import py
from pypy.lang.prolog.interpreter.parsing import parse_file, TermBuilder
from pypy.lang.prolog.interpreter.parsing import parse_query_term, get_engine
from pypy.lang.prolog.interpreter.error import UnificationFailed, CutException
from pypy.lang.prolog.interpreter.engine import Heap, Engine
from pypy.lang.prolog.interpreter import error
from pypy.lang.prolog.interpreter.test.tool import collect_all, assert_false, assert_true

def test_simple():
    assert_true("X is 1 + 2, X = 3.")
    assert_true("X is 1.2 + 2.8, X = 4.")
    assert_false("X is 1.1 + 2.8, X = 4.0.")
    assert_true("X is 1 - 2, X = -1.")
    assert_true("X is 1.2 - 1.2, X = 0.")
    assert_true("X is 2 * -2, X = -4.")
    assert_true("X is 2 * -2.1, X = -4.2.")
    assert_true("X is 2 + -2, X = 0.")
    assert_true("X is 2 // -2, X = -1.")

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
    assert_true("X is round(-0.5), X = 0.")
    #assert_true("X is round(-0.6), X = -1.") #XXX fix round
    #assert_true("X is round(-1), X = -1.")

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

def test_comparison():
    assert_true("1 =:= 1.0.")
    assert_true("1 + 1 > 1.")
    assert_true("1 + 0.001 >= 1 + 0.001.")
    assert_true("1 + 0.001 =< 1 + 0.001.")
    assert_false("1 > 1.")
    assert_true("1.1 > 1.")
    assert_false("1 =\\= 1.0.")
    assert_true("1 =\\= 32.")
