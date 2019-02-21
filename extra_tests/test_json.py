import pytest
import json
from hypothesis import given, strategies

def is_(x, y):
    return type(x) is type(y) and x == y

def test_no_ensure_ascii():
    assert is_(json.dumps(u"\u1234", ensure_ascii=False), u'"\u1234"')
    assert is_(json.dumps(u"\xc0", ensure_ascii=False), u'"\xc0"')
    with pytest.raises(TypeError):
        json.dumps((u"\u1234", b"x"), ensure_ascii=False)
    with pytest.raises(TypeError):
        json.dumps((b"x", u"\u1234"), ensure_ascii=False)

def test_issue2191():
    assert is_(json.dumps(u"xxx", ensure_ascii=False), u'"xxx"')

jsondata = strategies.recursive(
    strategies.none() |
    strategies.booleans() |
    strategies.floats(allow_nan=False) |
    strategies.text(),
    lambda children: strategies.lists(children) |
        strategies.dictionaries(strategies.text(), children))

@given(jsondata)
def test_roundtrip(d):
    assert json.loads(json.dumps(d)) == d
