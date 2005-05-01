import support
struct = support.libmodule('struct')


def test_simple():
    morezeros = '\x00' * (struct.calcsize('l')-4)
    assert struct.pack('<l', 16) == '\x10\x00\x00\x00' + morezeros
    assert struct.pack('4s', 'WAVE') == 'WAVE'
    assert struct.pack('<4sl', 'WAVE', 16) == 'WAVE\x10\x00\x00\x00' + morezeros
