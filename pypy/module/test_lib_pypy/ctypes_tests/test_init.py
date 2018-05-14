import pytest
from ctypes import *


class X(Structure):
    _fields_ = [("a", c_int),
                ("b", c_int)]
    new_was_called = False

    def __new__(cls):
        result = super(X, cls).__new__(cls)
        result.new_was_called = True
        return result

    def __init__(self):
        self.a = 9
        self.b = 12

class Y(Structure):
    _fields_ = [("x", X)]


@pytest.mark.xfail(
    reason="subclassing semantics and implementation details not implemented")
def test_get():
    # make sure the only accessing a nested structure
    # doesn't call the structure's __new__ and __init__
    y = Y()
    assert (y.x.a, y.x.b) == (0, 0)
    assert y.x.new_was_called == False

    # But explicitely creating an X structure calls __new__ and __init__, of course.
    x = X()
    assert (x.a, x.b) == (9, 12)
    assert x.new_was_called == True

    y.x = x
    assert (y.x.a, y.x.b) == (9, 12)
    assert y.x.new_was_called == False
