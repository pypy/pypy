import pytest
from traceback import _levenshtein_distance, _compute_suggestion_attribute_error, \
        TracebackException
from hypothesis import given, strategies as st

# levensthein tests

def test_levensthein():
    assert _levenshtein_distance("cat", "sat") == 1
    assert _levenshtein_distance("cat", "ca") == 1
    assert _levenshtein_distance("Kätzchen", "Satz") == 6

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

    assert _compute_suggestion_attribute_error(AttributeError(obj=A(), name="god")) == "good"
    assert _compute_suggestion_attribute_error(AttributeError(obj=A(), name="wlak")) == "walk"
    assert _compute_suggestion_attribute_error(AttributeError(obj=A(), name="good")) == None
    assert _compute_suggestion_attribute_error(AttributeError(obj=A(), name="goodabcd")) == None

def test_format_attribute_error():
    class A:
        good = 1
        walk = 2
    a = A()
    try:
        a.god
    except AttributeError as e:
        formatted = "\n".join(
            TracebackException.from_exception(e).format_exception_only())
        assert formatted == "AttributeError: 'A' object has no attribute 'god'. Did you mean: good?\n"
