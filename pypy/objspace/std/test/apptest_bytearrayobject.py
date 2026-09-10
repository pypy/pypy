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


def test_init_does_not_honor_bytes_without_index():
    # unlike bytes(), bytearray() never calls __bytes__, even when
    # __index__ is absent (see test_init_index_takes_precedence_over_bytes
    # for the case where both are defined).
    class WithBytes:
        def __init__(self, value):
            self.value = value
        def __bytes__(self):
            return self.value

    assert bytes(WithBytes(b'xy')) == b'xy'
    raises(TypeError, bytearray, WithBytes(b'xy'))

def test_release_buffer_bad_argument():
    # __release_buffer__ with something that is not a live buffer from
    # this object must raise, not underflow the export count and abort
    b = bytearray(b'x')
    raises(ValueError, b.__release_buffer__, None)
    raises(ValueError, b.__release_buffer__, memoryview(bytearray(b'y')))
    raises(ValueError, b.__release_buffer__, memoryview(b'z'))
    m = b.__buffer__(0)
    b.__release_buffer__(m)
    raises(ValueError, m.tobytes)
    b += b'ok'   # no exports left, resize allowed
