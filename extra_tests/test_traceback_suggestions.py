import pytest
from pathlib import Path

try:
    from hypothesis import given, strategies as st
except ImportError:
    given = st = None

path = Path(__file__).parent.joinpath("..", "lib-python", "3", "traceback.py")

with open(path) as f:
    content = f.read()

d = {}
c = compile(content, path, 'exec')
exec(c, d, d)
orig_levenshtein_distance = d['_levenshtein_distance']
def _levenshtein_distance(a, b):
    return orig_levenshtein_distance(a, b, max(len(a), len(b)))
_compute_suggestion_error = d['_compute_suggestion_error']
TracebackException = d['TracebackException']


# levensthein tests

def test_levensthein():
    assert _levenshtein_distance("cat", "sat") == 2
    assert _levenshtein_distance("cat", "ca") == 2
    assert _levenshtein_distance("cat", "caT") == 1 # case change is only edit distance 1
    assert _levenshtein_distance("Kätzchen", "Satz") == 9

if given is not None:
    @given(st.text())
    def test_x_x(s):
        assert _levenshtein_distance(s, s) == 0

    @given(st.text())
    def test_x_empty(s):
        assert _levenshtein_distance(s, '') == len(s)

    @given(st.text(), st.text())
    def test_symmetric(a, b):
        assert _levenshtein_distance(a, b) == _levenshtein_distance(b, a)

    @given(st.text(), st.text(), st.characters())
    def test_add_char(a, b, char):
        d = _levenshtein_distance(a, b)
        assert d == _levenshtein_distance(char + a, char + b)
        assert d == _levenshtein_distance(a + char, b + char)

    @given(st.text(), st.text(), st.text())
    def test_triangle(a, b, c):
        assert _levenshtein_distance(a, c) <= _levenshtein_distance(a, b) + _levenshtein_distance(b, c)


# suggestion tests

def test_compute_suggestion_attribute_error():
    class A:
        good = 1
        walk = 2

    assert _compute_suggestion_error(AttributeError(obj=A(), name="god"), None, "god") == "good"
    assert _compute_suggestion_error(AttributeError(obj=A(), name="good"), None, "good") == None
    assert _compute_suggestion_error(AttributeError(obj=A(), name="goodabcd"), None, "goodabcd") == None

def fmt(e):
    return "\n".join(
            TracebackException.from_exception(e).format_exception_only())

def test_format_attribute_error():
    class A:
        good = 1
        walk = 2
    a = A()
    try:
        a.god
    except AttributeError as e:
        assert fmt(e) == "AttributeError: 'A' object has no attribute 'god'. Did you mean: 'good'?\n"

def test_compute_suggestion_name_error():
    def f():
        abc = 1
        absc # abc beats abs!

    try:
        f()
    except NameError as e:
        assert fmt(e) == "NameError: name 'absc' is not defined. Did you mean: 'abc'?\n"

def test_compute_suggestion_name_error_from_global():
    def f():
        test_compute_suggestion_name_error_from_globl

    try:
        f()
    except NameError as e:
        assert fmt(e) == "NameError: name 'test_compute_suggestion_name_error_from_globl' is not defined. Did you mean: 'test_compute_suggestion_name_error_from_global'?\n"

def test_compute_suggestion_name_error_from_builtin():
    try:
        abcs
    except NameError as e:
        assert fmt(e) == "NameError: name 'abcs' is not defined. Did you mean: 'abs'?\n"

def test_missing_import():
    try:
        math
    except NameError as e:
        assert fmt(e) == "NameError: name 'math' is not defined. Did you mean: 'Path'? Or did you forget to import 'math'\n"
