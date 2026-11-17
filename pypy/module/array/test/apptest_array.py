# spaceconfig = {"usemodules": ["array"]}
import pytest
from array import array

def test_index_positions():
    a = array('i', [1, 2, 3, 1, 2, 1])
    assert a.index(1, start=2) == 3
    with pytest.raises(ValueError):
        a.index(1, start=1, stop=3)

def test_index_start_stop_negative():
    a = array('i', [1, 2, 3, 1, 2, 1])
    assert a.index(1, start=-3) == 3
    assert a.index(1, start=-300000) == 0
    assert a.index(1, start=1, stop=-1) == 3
    with pytest.raises(ValueError):
        a.index(1, start=1, stop=-1000)


def test_array_is_mutable_sequence():
    from _collections_abc import MutableSequence
    assert isinstance(array("B"), MutableSequence)


def test_array_u_items_are_wchar():
    # a non-BMP codepoint is a surrogate pair of two items where wchar_t is
    # 2 bytes (windows), a single item elsewhere
    a = array('u', "Bonne Journ\xe9e \U0002030a\U00020347")
    two_bytes = a.itemsize == 2
    assert len(a) == (18 if two_bytes else 16)
    assert a.tounicode() == "Bonne Journ\xe9e \U0002030a\U00020347"
    assert len(a.tounicode()) == 16
    b = array('u')
    b.fromunicode("\U0002030a")
    assert len(b) == (2 if two_bytes else 1)
    assert b.tounicode() == "\U0002030a"
    if two_bytes:
        # like CPython's u_setitem, one item must be one wchar_t
        with pytest.raises(TypeError):
            b.append("\U0002030a")
    else:
        b.append("\U0002030a")
        assert len(b) == 2
