"""App-level tests for bytearray."""
from pytest import raises


def test_init_index_takes_precedence_over_bytes():
    # issue 5567: bytearray() honours __index__ and ignores __bytes__.
    # only bytes() honours __bytes__.
    class Both:
        def __bytes__(self):
            return b'xy'
        def __index__(self):
            return 3

    assert bytearray(Both()) == b'\x00\x00\x00'
    assert bytes(Both()) == b'xy'

    class IntBytes(int):
        def __bytes__(self):
            return b'xy'

    assert bytearray(IntBytes(3)) == b'\x00\x00\x00'
    assert bytes(IntBytes(3)) == b'xy'


def test_init_index_side_effect_order():
    log = []

    class Both:
        def __bytes__(self):
            log.append('__bytes__')
            return b'xy'
        def __index__(self):
            log.append('__index__')
            return 3

    bytearray(Both())
    assert log == ['__index__']


def test_init_str_subclass_with_index():
    # a str is rejected before __index__ is considered
    class StrIdx(str):
        def __index__(self):
            return 3

    raises(TypeError, bytearray, StrIdx('a'))
    raises(TypeError, bytes, StrIdx('a'))


def test_init_index():
    class Indexable:
        def __index__(self):
            return 3

    assert bytearray(Indexable()) == b'\x00\x00\x00'
    assert bytearray(True) == b'\x00'

    class NegIndexable:
        def __index__(self):
            return -1

    raises(ValueError, bytearray, NegIndexable())


def test_init_huge_count_overflows():
    raises(OverflowError, bytearray, 2 ** 200)
