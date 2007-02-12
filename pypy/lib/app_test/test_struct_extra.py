from pypy.lib import struct 

def test_simple():
    morezeros = '\x00' * (struct.calcsize('l')-4)
    assert struct.pack('<l', 16) == '\x10\x00\x00\x00' + morezeros
    assert struct.pack('4s', 'WAVE') == 'WAVE'
    assert struct.pack('<4sl', 'WAVE', 16) == 'WAVE\x10\x00\x00\x00' + morezeros
    s = 'ABCD01234567\x01\x00\x00\x00\x02\x00\x00\x00\x03\x00'
    assert struct.unpack('<4s4H2lH', s) == ('ABCD', 0x3130, 0x3332, 0x3534,
                                            0x3736, 1, 2, 3)
