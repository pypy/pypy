import py
from prolog.interpreter.test.tool import assert_true, assert_false

# sionu ~=~ structural identical or not unifiable
def test_basic_sionu():
    assert_false("?=(X, Y).")
    assert_true("?=(X, X).")
    assert_true("?=(1, 1).")
    assert_true("?=(1, 2).")
    assert_false("?=(X, 1).")
    assert_false("?=([X, Y], [X, X]).")
    assert_true("?=([X, Y], [X, Y]).")

def test_binding():
    assert_false("?=(X, 1), X == 1.")
    assert_true("(\+ ?=(X, 1)), var(X).")
