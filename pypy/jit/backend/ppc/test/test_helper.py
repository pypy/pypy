from pypy.jit.backend.ppc.helper.assembler import (encode32, decode32)
                                                          #encode64, decode64)

def test_encode32():
    mem = [None]*4
    encode32(mem, 0, 1234567)
    assert ''.join(mem) == '\x00\x12\xd6\x87'
    mem = [None]*4
    encode32(mem, 0, 983040)
    assert ''.join(mem) == '\x00\x0F\x00\x00'

def test_decode32():
    mem = list('\x00\x12\xd6\x87')
    assert decode32(mem, 0) ==  1234567
    mem = list('\x00\x0F\x00\x00')
    assert decode32(mem, 0) == 983040
    mem = list("\x00\x00\x00\x03")
    assert decode32(mem, 0) == 3

def test_encode32_and_decode32():
    mem = [None] * 4
    for val in [1, 45654, -456456, 123, 99999]:
        encode32(mem, 0, val)
        assert decode32(mem, 0) == val

