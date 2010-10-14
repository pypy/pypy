import conditions as cond
import registers as reg
from pypy.rlib.rmmap import alloc
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.jit.backend.arm.instruction_builder import define_instructions

class ARMv7Builder(object):

    def __init__(self):
        self._data = alloc(1024)
        self._pos = 0

    def ADD_ri(self, rt, rn, imm, cond=cond.AL):
        # XXX S bit
        self.write32(cond << 28
                        | 2 << 24
                        | 8 << 20
                        | (rn & 0xF) << 16
                        | (rt & 0xF) << 12
                        | (imm & 0xFFF))

    def SUB_ri(self, rd, rn, imm=0, cond=cond.AL, s=0):
        self.write32(cond << 28
                        | 9 << 22
                        | (s & 0x1) << 20
                        | (rn & 0xF) << 16
                        | (rd & 0xF) << 12
                        | (imm & 0xFFF))

    def MOV_ri(self, rt, imm=0, cond=cond.AL):
        # XXX Check the actual allowed size for imm
        # XXX S bit
        self.write32(cond << 28
                    | 0x3 << 24
                    | 0xA << 20
                    #| 0x0 << 16
                    | (rt & 0xF) << 12
                    | (imm & 0xFFF))

    def PUSH(self, regs, cond=cond.AL):
        assert reg.sp not in regs
        instr = self._encode_reg_list(cond << 28 | 0x92D << 16, regs)
        self.write32(instr)

    def LDM(self, rn, regs, cond=cond.AL):
        w = 0
        instr = cond << 28 | 0x89 << 20 | w << 21 | (rn & 0xFF) << 16
        instr = self._encode_reg_list(instr, regs)
        self.write32(instr)

    def CMP(self, rn, imm, cond=cond.AL):
        if 0 <= imm <= 255:
            self.write32(cond << 28
                        | 0x35 << 20
                        | (rn & 0xFF) <<  16
                        | (imm & 0xFFF))
        else:
            raise NotImplentedError

    def _encode_reg_list(self, instr, regs):
        for reg in regs:
            instr |= 0x1 << reg
        return instr

    def _encode_imm(self, imm):
        u = 1
        if imm < 0:
            u = 0
            imm = -imm
        return u, imm

    def write32(self, word):
        self.writechar(chr(word & 0xFF))
        self.writechar(chr((word >> 8) & 0xFF))
        self.writechar(chr((word >> 16) & 0xFF))
        self.writechar(chr((word >> 24) & 0xFF))

    def writechar(self, char):
        self._data[self._pos] = char
        self._pos += 1

    def baseaddr(self):
        return rffi.cast(lltype.Signed, self._data)

    def curraddr(self):
        return self.baseaddr() + self._pos

define_instructions(ARMv7Builder)
