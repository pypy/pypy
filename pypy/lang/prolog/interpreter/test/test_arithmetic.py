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
    assert_true("X is 2 * -2, X = -4.")
    assert_true("X is 2 + -2, X = 0.")
    assert_true("X is 2 // -2, X = -1.")

def test_comparison():
    assert_true("1 =:= 1.0.")
    assert_true("1 + 1 > 1.")
    assert_true("1 + 0.001 >= 1 + 0.001.")
    assert_true("1 + 0.001 =< 1 + 0.001.")
    assert_false("1 > 1.")
    assert_false("1 =\\= 1.0.")
    assert_true("1 =\\= 32.")
