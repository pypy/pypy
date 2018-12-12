from ctypes import *

def test_buffer():
    b = create_string_buffer(32)
    assert len(b) == 32
    assert sizeof(b) == 32 * sizeof(c_char)
    assert type(b[0]) is str

    b = create_string_buffer(33L)
    assert len(b) == 33
    assert sizeof(b) == 33 * sizeof(c_char)
    assert type(b[0]) is str

    b = create_string_buffer(b"abc")
    assert len(b) == 4 # trailing nul char
    assert sizeof(b) == 4 * sizeof(c_char)
    assert type(b[0]) is str
    assert b[0] == b"a"
    assert b[:] == b"abc\0"

def test_from_buffer():
    b1 = bytearray(b"abcde")
    b = (c_char * 5).from_buffer(b1)
    assert b[2] == b"c"
    #
    b1 = bytearray(b"abcd")
    b = c_int.from_buffer(b1)
    assert b.value in (1684234849,   # little endian
                        1633837924)   # big endian

def test_from_buffer_keepalive():
    # Issue #2878
    b1 = bytearray(b"ab")
    array = (c_uint16 * 32)()
    array[6] = c_uint16.from_buffer(b1)
    # this is also what we get on CPython.  I don't think it makes
    # sense because the array contains just a copy of the number.
    assert array._objects == {'6': b1}
