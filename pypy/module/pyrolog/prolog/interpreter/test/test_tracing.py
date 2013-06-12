import py
from prolog.interpreter.test.tool import prolog_raises, \
assert_true, assert_false
from prolog.interpreter.parsing import get_engine
from prolog.interpreter.continuation import Engine

def test_simple_trace():
    assert_true("trace.")
    assert_true("notrace.")
