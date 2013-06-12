import py
from prolog.interpreter.test.tool import assert_true, assert_false, prolog_raises
from prolog.interpreter.continuation import Engine

e = Engine(load_system=True)

def test_numbervars_simple():
    assert_true("numbervars(X, 0, 1).", e)
    assert_true("numbervars(f(X,Y), 0, 2).", e)
    assert_true("numbervars(f(X,X), 0, 1).", e)
    assert_true("numbervars(a, 0, 0).", e)
    assert_true("numbervars(0, 0, 0).", e)
    prolog_raises("type_error(_, _)", "numbervars(_, no_number, _)", e)

def test_numbervars_bindings():
    assert_true("""
        X = f(A,B,C),
        numbervars(X, 0, 3),
        X = f('$VAR'(0), '$VAR'(1), '$VAR'(2)).
    """, e)
    assert_true("""
        X = f(A,B,C),
        numbervars(X, 5, 8),
        X = f('$VAR'(5), '$VAR'(6), '$VAR'(7)).
    """, e)
    assert_false("""
        X = f(A,B,C),
        A = 123,
        B = C,
        numbervars(X, 5, 8),
        X = f('$VAR'(5), '$VAR'(6), '$VAR'(7)).
    """, e)
    assert_false("""
        X = f(A,B,C),
        A = '$VAR'(5),
        numbervars(X, 5, 8),
        X = f('$VAR'(5), '$VAR'(6), '$VAR'(7)).
    """, e)
    assert_true("""
        X = f(A,B,C),
        A = '$VAR'(5),
        numbervars(X, 5, 7),
        X = f('$VAR'(5), '$VAR'(5), '$VAR'(6)).
    """, e)
