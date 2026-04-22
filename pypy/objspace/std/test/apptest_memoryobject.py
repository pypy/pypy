"""App-level tests for memoryview."""
from pytest import raises


def test_setitem_released_during_value_conversion():
    # gh-92888: memoryview must re-check if view was released after
    # converting the value via __index__, before writing.
    size = 128

    def release():
        m.release()

    class MyIndex:
        def __index__(self):
            release()
            return 4

    m = memoryview(bytearray(b'\xff' * size))
    with raises(ValueError, match="operation forbidden"):
        m[0] = MyIndex()


def test_setitem_released_during_value_conversion_formats():
    size = 128

    def release():
        m.release()

    class MyIndex:
        def __index__(self):
            release()
            return 4

    for fmt in 'bhilqnBHILQN':
        m = memoryview(bytearray(b'\xff' * size)).cast(fmt)
        with raises(ValueError, match="operation forbidden"):
            m[0] = MyIndex()


def test_setitem_released_during_float_conversion():
    size = 128

    def release():
        m.release()

    class MyFloat:
        def __float__(self):
            release()
            return 4.25

    for fmt in 'fd':
        m = memoryview(bytearray(b'\xff' * size)).cast(fmt)
        with raises(ValueError, match="operation forbidden"):
            m[0] = MyFloat()


def test_setitem_released_during_bool_conversion():
    size = 128

    def release():
        m.release()

    class MyBool:
        def __bool__(self):
            release()
            return True

    m = memoryview(bytearray(b'\xff' * size)).cast('?')
    with raises(ValueError, match="operation forbidden"):
        m[0] = MyBool()


def test_tuple_setitem_released_during_value_conversion():
    size = 128

    def release():
        m.release()

    class MyIndex:
        def __index__(self):
            release()
            return 4

    m = memoryview(bytearray(b'\xff' * size)).cast('B', (64, 2))
    with raises(ValueError, match="operation forbidden"):
        m[0, 0] = MyIndex()
