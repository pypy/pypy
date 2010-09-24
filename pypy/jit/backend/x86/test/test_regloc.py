import struct
from pypy.jit.backend.x86.regloc import *
from pypy.jit.backend.x86.test.test_rx86 import CodeBuilder32, CodeBuilder64, assert_encodes_as
from pypy.jit.backend.x86.assembler import heap
from pypy.jit.backend.x86.arch import IS_X86_64, IS_X86_32
from pypy.rlib.rarithmetic import intmask
import py.test

class LocationCodeBuilder32(CodeBuilder32, LocationCodeBuilder):
    pass

class LocationCodeBuilder64(CodeBuilder64, LocationCodeBuilder):
    pass

cb32 = LocationCodeBuilder32
cb64 = LocationCodeBuilder64

def test_mov_16():
    # 32-bit
    assert_encodes_as(cb32, "MOV16", (ecx, ebx), '\x66\x89\xD9')
    assert_encodes_as(cb32, "MOV16", (ecx, ImmedLoc(12345)), '\x66\xB9\x39\x30')

    # 64-bit
    assert_encodes_as(cb64, "MOV16", (ecx, ebx), '\x66\x89\xD9')
    # XXX: What we are testing for here is actually not the most compact
    # encoding.
    assert_encodes_as(cb64, "MOV16", (ecx, ImmedLoc(12345)), '\x66\xC7\xC1\x39\x30')
    assert_encodes_as(cb64, "MOV16", (AddressLoc(r13, ImmedLoc(0), 0, 0), ImmedLoc(12345)), '\x66\x41\xC7\x45\x00\x39\x30')

def test_cmp_16():
    # 32-bit
    assert_encodes_as(cb32, "CMP16", (ecx, ebx), '\x66\x39\xD9')
    assert_encodes_as(cb32, "CMP16", (ecx, ImmedLoc(12345)), '\x66\x81\xF9\x39\x30')

    # 64-bit
    assert_encodes_as(cb64, "CMP16", (ecx, ebx), '\x66\x39\xD9')
    assert_encodes_as(cb64, "CMP16", (ecx, ImmedLoc(12345)), '\x66\x81\xF9\x39\x30')
    assert_encodes_as(cb64, "CMP16", (AddressLoc(r13, ImmedLoc(0), 0, 0), ImmedLoc(12345)), '\x66\x41\x81\x7D\x00\x39\x30')

def test_jmp_wraparound():
    if not IS_X86_32:
        py.test.skip()

    pos_addr = intmask(0x7FFFFF00)
    neg_addr = intmask(0x800000BB)

    # JMP to "negative" address from "positive" address
    s = cb32()
    s.base_address = pos_addr
    s.JMP(ImmedLoc(neg_addr))
    expected_ofs = neg_addr - (pos_addr+5)
    assert s.getvalue() == '\xE9' + struct.pack("<i", expected_ofs)

    # JMP to a "positive" address from a "negative" address
    s = cb32()
    s.base_address = neg_addr
    s.JMP(ImmedLoc(pos_addr))
    expected_ofs = pos_addr - (neg_addr+5)
    assert s.getvalue() == '\xE9' + struct.pack("<i", expected_ofs)


class Test64Bits:

    def setup_class(cls):
        if not IS_X86_64:
            py.test.skip()

    def test_reuse_scratch_register(self):
        base_addr = 0xFEDCBA9876543210
        cb = LocationCodeBuilder64()
        cb.begin_reuse_scratch_register()
        cb.MOV(ecx, heap(base_addr))
        cb.MOV(ecx, heap(base_addr + 8))
        cb.end_reuse_scratch_register()

        expected_instructions = (
                # mov r11, 0xFEDCBA9876543210
                '\x49\xBB\x10\x32\x54\x76\x98\xBA\xDC\xFE' +
                # mov rcx, [r11]
                '\x49\x8B\x0B' +
                # mov rcx, [r11+8]
                '\x49\x8B\x4B\x08'
        )
        assert cb.getvalue() == expected_instructions

    def test_64bit_address_1(self):
        base_addr = 0xFEDCBA9876543210
        cb = LocationCodeBuilder64()
        cb.CMP(ecx, AddressLoc(ImmedLoc(0), ImmedLoc(0), 0, base_addr))
        #
        expected_instructions = (
                # mov r11, 0xFEDCBA9876543210
                '\x49\xBB\x10\x32\x54\x76\x98\xBA\xDC\xFE'
                # cmp rcx, [r11]
                '\x49\x3B\x0B'
        )
        assert cb.getvalue() == expected_instructions

    def test_64bit_address_2(self):
        base_addr = 0xFEDCBA9876543210
        cb = LocationCodeBuilder64()
        cb.MOV(ecx, AddressLoc(ImmedLoc(0), edx, 3, base_addr))
        #
        expected_instructions = (
                # mov r11, 0xFEDCBA9876543210
                '\x49\xBB\x10\x32\x54\x76\x98\xBA\xDC\xFE'
                # mov rcx, [r11+8*rdx]
                '\x49\x8B\x0C\xD3'
        )
        assert cb.getvalue() == expected_instructions

    def test_64bit_address_3(self):
        base_addr = 0xFEDCBA9876543210
        cb = LocationCodeBuilder64()
        cb.MOV(ecx, AddressLoc(edx, ImmedLoc(0), 0, base_addr))
        #
        # sub-efficient instruction generated in that particular case:
        # the LEA is not really needed, but it's useful because we can
        # keep the same mode 'm' for generating the final instruction
        expected_instructions = (
                # mov r11, 0xFEDCBA9876543210
                '\x49\xBB\x10\x32\x54\x76\x98\xBA\xDC\xFE'
                # lea r11, [rdx+r11]
                '\x4E\x8D\x1C\x1A'
                # mov rcx, [r11]
                '\x49\x8B\x0B'
        )
        assert cb.getvalue() == expected_instructions

    def test_64bit_address_4(self):
        base_addr = 0xFEDCBA9876543210
        cb = LocationCodeBuilder64()
        cb.begin_reuse_scratch_register()
        assert cb._reuse_scratch_register is True
        assert cb._scratch_register_known is False
        cb.MOV(ecx, AddressLoc(edx, esi, 2, base_addr))
        assert cb._reuse_scratch_register is True
        assert cb._scratch_register_known is False
        #
        expected_instructions = (
                # mov r11, 0xFEDCBA9876543210
                '\x49\xBB\x10\x32\x54\x76\x98\xBA\xDC\xFE'
                # lea r11, [rdx+r11]
                '\x4E\x8D\x1C\x1A'
                # mov rcx, [r11+4*rsi]
                '\x49\x8B\x0C\xB3'
        )
        assert cb.getvalue() == expected_instructions
