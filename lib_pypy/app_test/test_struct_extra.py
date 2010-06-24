from pypy.lib import struct 

def test_simple():
    morezeros = '\x00' * (struct.calcsize('l')-4)
    assert struct.pack('<l', 16) == '\x10\x00\x00\x00' + morezeros
    assert struct.pack('4s', 'WAVE') == 'WAVE'
    assert struct.pack('<4sl', 'WAVE', 16) == 'WAVE\x10\x00\x00\x00' + morezeros
    s = 'ABCD01234567\x01\x00\x00\x00\x02\x00\x00\x00\x03\x00'
    assert struct.unpack('<4s4H2lH', s) == ('ABCD', 0x3130, 0x3332, 0x3534,
                                            0x3736, 1, 2, 3)

def test_infinity():
    INFINITY = 1e200 * 1e200
    assert str(struct.unpack("!d", struct.pack("!d", INFINITY))[0]) \
           == str(INFINITY)
    assert str(struct.unpack("!d", struct.pack("!d", -INFINITY))[0]) \
           == str(-INFINITY)

def test_nan():
    INFINITY = 1e200 * 1e200
    NAN = INFINITY / INFINITY
    assert str(struct.unpack("!d", '\xff\xf8\x00\x00\x00\x00\x00\x00')[0]) \
           == str(NAN)
    assert str(struct.unpack("!d", struct.pack("!d", NAN))[0]) == str(NAN)
