from rpython.rlib.buffer import StringBuffer, SubBuffer, Buffer
from rpython.annotator.annrpython import RPythonAnnotator
from rpython.annotator.model import SomeInteger


def test_string_buffer():
    buf = StringBuffer('hello world')
    assert buf.getitem(4) == 'o'
    assert buf.getitem(4) == buf[4]
    assert buf.getlength() == 11
    assert buf.getlength() == len(buf)
    assert buf.getslice(1, 6, 1, 5) == 'ello '
    assert buf.getslice(1, 6, 1, 5) == buf[1:6]
    assert buf.getslice(1, 6, 2, 3) == 'el '
    assert buf.as_str() == 'hello world'



def test_len_nonneg():
    # This test needs a buffer subclass whose getlength() isn't guaranteed to
    # return a non-neg integer.
    class DummyBuffer(Buffer):
        def __init__(self, s):
            self.size = s

        def getlength(self):
            return self.size
    def func(n):
        buf = DummyBuffer(n)
        return len(buf)

    a = RPythonAnnotator()
    s = a.build_types(func, [int])
    assert s == SomeInteger(nonneg=True)


def test_as_str_and_offset_maybe():
    buf = StringBuffer('hello world')
    assert buf.as_str_and_offset_maybe() == ('hello world', 0)
    #
    sbuf = SubBuffer(buf, 6, 5)
    assert sbuf.getslice(0, 5, 1, 5) == 'world'
    assert sbuf.as_str_and_offset_maybe() == ('hello world', 6)
    #
    ssbuf = SubBuffer(sbuf, 3, 2)
    assert ssbuf.getslice(0, 2, 1, 2) == 'ld'
    assert ssbuf.as_str_and_offset_maybe() == ('hello world', 9)
    #
    ss2buf = SubBuffer(sbuf, 1, -1)
    assert ss2buf.as_str() == 'orld'
    assert ss2buf.getlength() == 4
    ss3buf = SubBuffer(ss2buf, 1, -1)
    assert ss3buf.as_str() == 'rld'
    assert ss3buf.getlength() == 3
    #
    ss4buf = SubBuffer(buf, 3, 4)
    assert ss4buf.as_str() == 'lo w'
    ss5buf = SubBuffer(ss4buf, 1, -1)
    assert ss5buf.as_str() == 'o w'
    assert ss5buf.getlength() == 3

def test_repeated_subbuffer():
    buf = StringBuffer('x' * 10000)
    for i in range(9999, 9, -1):
        buf = SubBuffer(buf, 1, i)
    assert buf.getlength() == 10

def test_string_buffer_as_buffer():
    buf = StringBuffer(b'hello world')
    addr = buf.get_raw_address()
    assert addr[0] == b'h'
    assert addr[4] == b'o'
    assert addr[6] == b'w'
    assert addr[len(b'hello world')] == b'\x00'
