import pytest
import json

def is_(x, y):
    return type(x) is type(y) and x == y

def test_no_ensure_ascii():
    assert is_(json.dumps(u"\u1234", ensure_ascii=False), u'"\u1234"')
    assert is_(json.dumps("\xc0", ensure_ascii=False), '"\xc0"')
    with pytest.raises(UnicodeDecodeError) as excinfo:
        json.dumps((u"\u1234", "\xc0"), ensure_ascii=False)
    assert str(excinfo.value).startswith(
        "'ascii' codec can't decode byte 0xc0 ")
    with pytest.raises(UnicodeDecodeError) as excinfo:
        json.dumps(("\xc0", u"\u1234"), ensure_ascii=False)
    assert str(excinfo.value).startswith(
        "'ascii' codec can't decode byte 0xc0 ")

def test_issue2191():
    assert is_(json.dumps(u"xxx", ensure_ascii=False), u'"xxx"')
