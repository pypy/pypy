from rpython.rlib.buffer import *


def test_string_buffer():
    buf = StringBuffer('hello world')
    assert buf.getitem(4) == 'o'
    assert buf.getlength() == 11
    assert buf.getslice(1, 6, 1, 5) == 'ello '
    assert buf.getslice(1, 6, 2, 3) == 'el '
    assert buf.as_str() == 'hello world'
