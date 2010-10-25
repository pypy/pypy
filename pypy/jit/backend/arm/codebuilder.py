from pypy.jit.backend.arm import conditions as cond
from pypy.jit.backend.arm import registers as reg
from pypy.jit.backend.arm.arch import WORD
from pypy.jit.backend.arm.instruction_builder import define_instructions

from pypy.rlib.rmmap import alloc, PTR
from pypy.rpython.lltypesystem import lltype, rffi

class AbstractARMv7Builder(object):
    def _init(self, data, map_size):
        self._data = data
        self._size = map_size
        self._pos = 0

    def _dump_trace(self, name):
        f = open('output/%s' % name, 'wb')
        for i in range(self._pos):
            f.write(self._data[i])
        f.close()

    def PUSH(self, regs, cond=cond.AL):
        assert reg.sp not in regs
        instr = self._encode_reg_list(cond << 28 | 0x92D << 16, regs)
        self.write32(instr)

    def LDM(self, rn, regs, w=0, cond=cond.AL):
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

    def BKPT(self, cond=cond.AL):
        self.write32(cond << 28 | 0x1200070)

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

    size_of_gen_load_int = 7 * WORD
    def gen_load_int(self, r, value, cond=cond.AL):
        assert r != reg.ip, 'ip is used to load int'
        self.MOV_ri(r, (value & 0xFF), cond=cond)

        for offset in range(8, 25, 8):
            t = (value >> offset) & 0xFF
            #if t == 0:
            #    continue
            self.MOV_ri(reg.ip, t, cond=cond)
            self.ORR_rr(r, r, reg.ip, offset, cond=cond)

class ARMv7InMemoryBuilder(AbstractARMv7Builder):
    def __init__(self, start, end):
        map_size = end - start
        data = rffi.cast(PTR, start)
        self._init(data, map_size)

class ARMv7Builder(AbstractARMv7Builder):

    def __init__(self):
        map_size = 1024
        data = alloc(map_size)
        self._pos = 0
        self._init(data, map_size)

define_instructions(AbstractARMv7Builder)
