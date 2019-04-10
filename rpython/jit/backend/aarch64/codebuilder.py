
from rpython.rlib.objectmodel import we_are_translated
from rpython.jit.backend.llsupport.asmmemmgr import BlockBuilderMixin
from rpython.jit.backend.aarch64.locations import RegisterLocation
from rpython.jit.backend.aarch64 import registers as r
from rpython.rlib.rarithmetic import intmask
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.tool.udir import udir

PC_OFFSET = 0 # XXX

class AbstractAarch64Builder(object):
    def write32(self, word):
        self.writechar(chr(word & 0xFF))
        self.writechar(chr((word >> 8) & 0xFF))
        self.writechar(chr((word >> 16) & 0xFF))
        self.writechar(chr((word >> 24) & 0xFF))

    def RET_r(self, arg):
        self.write32((0b1101011001011111 << 16) | (arg << 5))

    def STR_ri(self, rt, rn, offset):
        base = 0b1111100100
        assert offset & 0x7 == 0
        assert 0 <= offset < 32768
        self.write32((base << 22) | ((offset >> 3) << 10) |
                     (rn << 5) | rt)

    def STP_rr_preindex(self, reg1, reg2, rn, offset):
        base = 0b1010100110
        assert -512 <= offset < 512
        assert offset & 0x7 == 0
        self.write32((base << 22) | ((0x7F & (offset >> 3)) << 15) |
                     (reg2 << 10) | (rn << 5) | reg1)

    def STP_rri(self, reg1, reg2, rn, offset):
        base = 0b1010100100
        assert -512 <= offset < 512
        assert offset & 0x7 == 0
        self.write32((base << 22) | ((0x7F & (offset >> 3)) << 15) |
                     (reg2 << 10) | (rn << 5) | reg1)

    def MOV_rr(self, rd, rn):
        self.ORR_rr(rd, r.xzr.value, rn)

    def ORR_rr(self, rd, rn, rm):
        base = 0b10101010000
        self.write32((base << 21) | (rm << 16) |
                     (rn << 5) | rd)

    def MOVK_r_u16(self, rd, immed, shift):
        base = 0b111100101
        assert 0 <= immed < 1 << 16
        assert shift in (0, 16, 32, 48)
        self.write32((base << 23) | (shift >> 4 << 21) | (immed << 5) | rd) 

    def MOVZ_r_u16(self, rd, immed, shift):
        base = 0b110100101
        assert 0 <= immed < 1 << 16
        assert shift in (0, 16, 32, 48)
        self.write32((base << 23) | (shift >> 4 << 21) | (immed << 5) | rd) 

    def MOVN_r_u16(self, rd, immed):
        base = 0b10010010100
        assert 0 <= immed < 1 << 16
        self.write32((base << 21) | (immed << 5) | rd)

    def ADD_ri(self, rd, rn, constant):
        base = 0b1001000100
        assert 0 <= constant < 4096
        self.write32((base << 22) | (constant << 10) |
                     (rn << 5) | rd)

    def SUB_ri(self, rd, rn, constant):
        base = 0b1101000100
        assert 0 <= constant < 4096
        self.write32((base << 22) | (constant << 10) | (rn << 5) | rd)

    def LDP_rri(self, reg1, reg2, rn, offset):
        base = 0b1010100101
        assert -512 <= offset < 512
        assert offset & 0x7 == 0
        assert reg1 != reg2
        self.write32((base << 22) | ((0x7F & (offset >> 3)) << 15) |
                     (reg2 << 10) | (rn << 5) | reg1)

    def LDP_rr_postindex(self, reg1, reg2, rn, offset):
        base = 0b1010100011
        assert -512 <= offset < 512
        assert offset & 0x7 == 0
        assert reg1 != reg2
        assert rn != reg1
        assert rn != reg2
        self.write32((base << 22) | ((0x7F & (offset >> 3)) << 15) |
                     (reg2 << 10) | (rn << 5) | reg1)

    def LDR_ri(self, rt, rn, immed):
        base = 0b1111100101
        assert 0 <= immed <= 1<<15
        assert immed & 0x7 == 0
        self.write32((base << 22) | (immed >> 3 << 10) | (rn << 5) | rt)
    
    def LDR_r_literal(self, rt, offset):
        base = 0b01011000
        assert -(1 << 20) <= offset < (1<< 20)
        assert offset & 0x3 == 0
        self.write32((base << 24) | ((0x7ffff & (offset >> 2)) << 5) | rt)

    def ADD_rr(self, rd, rn, rm):
        base = 0b10001011000
        self.write32((base << 21) | (rm << 16) | (rn << 5) | (rd))

    def CMP_rr(self, rn, rm):
        base = 0b11101011000
        self.write32((base << 21) | (rm << 16) | (rn << 5) | 0b11111)

    def CMP_ri(self, rn, imm):
        base = 0b1111000100
        assert 0 <= imm <= 4095
        self.write32((base << 22) | (imm << 10) | (rn << 5) | 0b11111)

    def NOP(self):
        self.write32(0b11010101000000110010000000011111)

    def B_ofs(self, ofs):
        base = 0b000101
        assert ofs & 0x3 == 0
        pos = self.currpos()
        target_ofs = ofs - (pos + PC_OFFSET)
        assert -(1 << (26 + 2)) < target_ofs < 1<<(26 + 2)
        if target_ofs < 0:
            target_ofs = (1 << 26) - (-target_ofs >> 2)
        else:
            target_ofs = target_ofs >> 2
        self.write32((base << 26) | target_ofs)

    def B_ofs_cond(self, ofs, cond):
        base = 0b01010100
        assert ofs & 0x3 == 0
        assert -1 << 10 < ofs < 1 << 10
        imm = ofs >> 2
        if imm < 0:
            xxx
        self.write32((base << 24) | (imm << 5) | cond)

    def BL(self, target):
        target = rffi.cast(lltype.Signed, target)
        self.gen_load_int_full(r.ip0.value, target)
        self.BR(r.ip0.value)

    def BR(self, reg):
        base = 0b1101011000011111000000
        self.write32((base << 10) | (reg << 5))

    def BRK(self):
        self.write32(0b11010100001 << 21)

    def gen_load_int_full(self, r, value):
        self.MOVZ_r_u16(r, value & 0xFFFF, 0)
        self.MOVK_r_u16(r, (value >> 16) & 0xFFFF, 16)
        self.MOVK_r_u16(r, (value >> 32) & 0xFFFF, 32)
        self.MOVK_r_u16(r, (value >> 48) & 0xFFFF, 48)

    def gen_load_int(self, r, value):
        """r is the register number, value is the value to be loaded to the
        register"""
        # XXX optimize!
        if value < 0:
            self.gen_load_int_full(r, value)
            return
        self.MOVZ_r_u16(r, value & 0xFFFF, 0)
        value = value >> 16
        shift = 16
        while value:
            self.MOVK_r_u16(r, value & 0xFFFF, shift)
            shift += 16
            value >>= 16

    def get_max_size_of_gen_load_int(self):
        return 4


class OverwritingBuilder(AbstractAarch64Builder):
    def __init__(self, cb, start, size):
        AbstractAarch64Builder.__init__(self)
        self.cb = cb
        self.index = start
        self.start = start
        self.end = start + size

    def currpos(self):
        return self.index

    def writechar(self, char):
        assert self.index <= self.end
        self.cb.overwrite(self.index, char)
        self.index += 1


class InstrBuilder(BlockBuilderMixin, AbstractAarch64Builder):

    def __init__(self, arch_version=7):
        AbstractAarch64Builder.__init__(self)
        self.init_block_builder()
        #
        # ResOperation --> offset in the assembly.
        # ops_offset[None] represents the beginning of the code after the last op
        # (i.e., the tail of the loop)
        self.ops_offset = {}

    def mark_op(self, op):
        pos = self.get_relative_pos()
        self.ops_offset[op] = pos

    def _dump_trace(self, addr, name, formatter=-1):
        if not we_are_translated():
            if formatter != -1:
                name = name % formatter
            dir = udir.ensure('asm', dir=True)
            f = dir.join(name).open('wb')
            data = rffi.cast(rffi.CCHARP, addr)
            for i in range(self.currpos()):
                f.write(data[i])
            f.close()

    def clear_cache(self, addr):
        if we_are_translated():
            startaddr = rffi.cast(llmemory.Address, addr)
            endaddr = rffi.cast(llmemory.Address,
                            addr + self.get_relative_pos())
            clear_cache(startaddr, endaddr)

    def copy_to_raw_memory(self, addr):
        self._copy_to_raw_memory(addr)
        self.clear_cache(addr)
        self._dump(addr, "jit-backend-dump", 'arm')

    def currpos(self):
        return self.get_relative_pos()
