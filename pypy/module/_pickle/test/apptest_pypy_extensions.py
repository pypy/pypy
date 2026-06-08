"""Tests for PyPy-specific pickle extensions (pypy_extensions flag).

These test the compact ASCII-list pickle format emitted by Pickler when
pypy_extensions=True, and the corresponding fast unpickle path.
"""
import io
import pytest
from _pickle import Pickler, dumps, loads


def _pypy_dumps(obj, protocol=4):
    """Pickle obj using the PyPy-specific ASCII-list optimisation."""
    buf = io.BytesIO()
    p = Pickler(buf, protocol)
    p.pypy_extensions = True
    p.dump(obj)
    return buf.getvalue()


def test_attribute_default():
    buf = io.BytesIO()
    p = Pickler(buf, 4)
    assert p.pypy_extensions == False
    p.pypy_extensions = True
    assert p.pypy_extensions == True


def test_ascii_list_roundtrip():
    data = ['hello', 'world', 'foo', 'bar']
    assert loads(_pypy_dumps(data)) == data


def test_ascii_list_large():
    data = ['%032x' % i for i in range(10000)]
    assert loads(_pypy_dumps(data)) == data


def test_uses_global_marker():
    blob = _pypy_dumps(['a', 'b', 'c'])
    assert b'pypy._builtin' in blob
    assert b'_ascii_list_unpickle' in blob


def test_flag_off_no_marker():
    assert b'pypy._builtin' not in dumps(['a', 'b', 'c'], 4)


def test_empty_list():
    assert loads(_pypy_dumps([])) == []


def test_single_item():
    assert loads(_pypy_dumps(['only'])) == ['only']


def test_empty_strings():
    data = ['', '', 'hello', '']
    assert loads(_pypy_dumps(data)) == data


def test_max_length_string():
    # Strings of exactly 255 bytes must use the fast path.
    data = ['a' * 255, 'b' * 128]
    blob = _pypy_dumps(data)
    assert b'pypy._builtin' in blob
    assert loads(blob) == data


def test_non_ascii_falls_back():
    # A list containing a non-ASCII string must not use the fast path.
    data = ['hello', 'wörld']
    blob = _pypy_dumps(data)
    assert b'pypy._builtin' not in blob
    assert loads(blob) == data


def test_mixed_types_falls_back():
    # A list with non-string items must not use the fast path.
    data = ['hello', 42, 'world']
    blob = _pypy_dumps(data)
    assert b'pypy._builtin' not in blob
    assert loads(blob) == data


def test_proto_less_than_2_falls_back():
    # Protocols 0 and 1 must not emit the PyPy-specific form.
    data = ['hello', 'world']
    for proto in (0, 1):
        blob = _pypy_dumps(data, protocol=proto)
        assert b'pypy._builtin' not in blob
        assert loads(blob) == data


def test_long_string_falls_back():
    # Strings longer than 255 bytes cannot use 1-byte length prefix.
    data = ['x' * 256, 'short']
    blob = _pypy_dumps(data)
    assert b'pypy._builtin' not in blob
    assert loads(blob) == data


def test_shared_reference():
    # The same list referenced twice must unpickle to the same object.
    data = ['a', 'b', 'c']
    obj = [data, data]
    result = loads(_pypy_dumps(obj))
    assert result[0] == data
    assert result[1] == data
    assert result[0] is result[1]


def test_nested():
    # ASCII lists inside other structures must round-trip correctly.
    data = {'key': ['foo', 'bar', 'baz'], 'other': 42}
    assert loads(_pypy_dumps(data)) == data


# --- bytes list fast path ---

def test_bytes_list_roundtrip():
    data = [b'hello', b'world', b'foo', b'bar']
    assert loads(_pypy_dumps(data)) == data


def test_bytes_list_uses_global_marker():
    blob = _pypy_dumps([b'a', b'b', b'c'])
    assert b'pypy._builtin' in blob
    assert b'_bytes_list_unpickle' in blob


def test_bytes_list_empty():
    assert loads(_pypy_dumps([])) == []


def test_bytes_list_single_item():
    assert loads(_pypy_dumps([b'only'])) == [b'only']


def test_bytes_list_empty_bytes():
    data = [b'', b'', b'hello', b'']
    assert loads(_pypy_dumps(data)) == data


def test_bytes_list_max_length():
    data = [b'a' * 255, b'b' * 128]
    blob = _pypy_dumps(data)
    assert b'pypy._builtin' in blob
    assert loads(blob) == data


def test_bytes_list_long_item_falls_back():
    data = [b'x' * 256, b'short']
    blob = _pypy_dumps(data)
    assert b'_bytes_list_unpickle' not in blob
    assert loads(blob) == data


def test_bytes_list_flag_off_no_marker():
    assert b'_bytes_list_unpickle' not in dumps([b'a', b'b', b'c'], 4)


def test_bytes_list_proto_less_than_2_falls_back():
    data = [b'hello', b'world']
    for proto in (0, 1):
        blob = _pypy_dumps(data, protocol=proto)
        assert b'pypy._builtin' not in blob
        assert loads(blob) == data


def test_bytes_list_large():
    data = [bytes([i % 256]) * 16 for i in range(10000)]
    assert loads(_pypy_dumps(data)) == data


def test_bytes_list_shared_reference():
    data = [b'a', b'b', b'c']
    obj = [data, data]
    result = loads(_pypy_dumps(obj))
    assert result[0] == data
    assert result[1] == data
    assert result[0] is result[1]


def test_bytes_list_mixed_types_falls_back():
    data = [b'hello', 42, b'world']
    blob = _pypy_dumps(data)
    assert b'_bytes_list_unpickle' not in blob
    assert loads(blob) == data
