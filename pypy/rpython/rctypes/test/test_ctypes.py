"""
The purpose of this test file is to check how ctypes really work,
down to what aliases what and what exact types operations return.
"""

from ctypes import *

def test_primitive_pointer():
    x = c_int(5)
    assert x.value == 5
    x.value = 6
    assert x.value == 6

    p = pointer(x)
    assert isinstance(p.contents, c_int)
    p.contents.value += 1
    assert x.value == 7

    y = c_int(12)
    p.contents = y
    p.contents.value += 2
    assert y.value == 14
    assert x.value == 7

    pp = pointer(p)
    pp.contents.contents = x
    p.contents.value += 2
    assert x.value == 9

    assert isinstance(p[0], int)
    p[0] += 1
    assert x.value == 10
    z = c_int(86)
    p[0] = z
    assert x.value == 86
    z.value = 84
    assert x.value == 86

    assert isinstance(pp[0], POINTER(c_int))
    assert pp[0].contents.value == x.value == 86
    pp[0].contents = z
    assert p.contents.value == z.value == 84

    q = pointer(y)
    pp[0] = q
    assert pp.contents.contents.value == y.value == 14


def test_char_p():
    x = c_char_p("hello\x00world")
    assert x.value == "hello"
    x.value = "world"
    assert x.value == "world"

    p = pointer(x)
    assert p[0] == x.value == "world"
    p[0] = "other"
    assert x.value == p.contents.value == p[0] == "other"
