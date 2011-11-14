from pypy.jit.backend.arm.helper.assembler import count_reg_args, \
                                                    decode32, encode32, \
                                                    decode64, encode64
from pypy.jit.metainterp.history import (BoxInt, BoxPtr, BoxFloat,
                                        INT, REF, FLOAT)
from pypy.jit.backend.arm.test.support import skip_unless_arm
skip_unless_arm()

def test_count_reg_args():
    assert count_reg_args([BoxPtr()]) == 1
    assert count_reg_args([BoxPtr()] * 2) == 2
    assert count_reg_args([BoxPtr()] * 3) == 3
    assert count_reg_args([BoxPtr()] * 4) == 4
    assert count_reg_args([BoxPtr()] * 5) == 4
    assert count_reg_args([BoxFloat()] * 1) == 1
    assert count_reg_args([BoxFloat()] * 2) == 2
    assert count_reg_args([BoxFloat()] * 3) == 2

    assert count_reg_args([BoxInt(), BoxInt(), BoxFloat()]) == 3
    assert count_reg_args([BoxInt(), BoxFloat(), BoxInt()]) == 2

    assert count_reg_args([BoxInt(), BoxFloat(), BoxInt()]) == 2
    assert count_reg_args([BoxInt(), BoxInt(), BoxInt(), BoxFloat()]) == 3

def test_encode32():
    mem = [None]*4
    encode32(mem, 0, 1234567)
    assert ''.join(mem) == '\x87\xd6\x12\x00'
    mem = [None]*4
    encode32(mem, 0, 983040)
    assert ''.join(mem) == '\x00\x00\x0F\x00'

def test_decode32():
    mem = list('\x87\xd6\x12\x00')
    assert decode32(mem, 0) ==  1234567
    mem = list('\x00\x00\x0F\x00')
    assert decode32(mem, 0) == 983040

def test_decode64():
    mem = list('\x87\xd6\x12\x00\x00\x00\x0F\x00')
    assert decode64(mem, 0) == 4222124651894407L

def test_encode64():
    mem = [None] * 8
    encode64(mem, 0, 4222124651894407L)
    assert ''.join(mem) ==  '\x87\xd6\x12\x00\x00\x00\x0F\x00'
