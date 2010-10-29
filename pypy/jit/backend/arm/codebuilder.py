from pypy.jit.backend.arm import conditions as cond
from pypy.jit.backend.arm import registers as reg
from pypy.jit.backend.arm.arch import (WORD, FUNC_ALIGN, arm_int_div,
                                        arm_int_div_sign, arm_int_mod_sign, arm_int_mod)
from pypy.jit.backend.arm.instruction_builder import define_instructions

from pypy.rlib.rmmap import alloc, PTR
from pypy.rpython.annlowlevel import llhelper
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.jit.metainterp.history import ConstInt, BoxInt, Box, BasicFailDescr

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

    def DIV(self, cond=cond.AL):
        """Generates a call to a helper function used for division, takes its
        arguments in r0 and r1, result is placed in r0"""
        self.PUSH(range(2, 12), cond=cond)
        div_addr = rffi.cast(lltype.Signed, llhelper(arm_int_div_sign, arm_int_div))
        self.gen_load_int(reg.r2.value, div_addr, cond=cond)
        self.gen_load_int(reg.lr.value, self.curraddr()+self.size_of_gen_load_int+WORD, cond=cond)
        self.MOV_rr(reg.pc.value, reg.r2.value, cond=cond)
        self.LDM(reg.sp.value, range(2, 12), w=1, cond=cond) # XXX Replace with POP instr. someday

    def MOD(self, cond=cond.AL):
        """Generate a call to a helper function used for modulo, takes its
        arguments in r0 and r1, result is placed in r0"""
        self.PUSH(range(2, 12), cond=cond)
        mod_addr = rffi.cast(lltype.Signed, llhelper(arm_int_mod_sign, arm_int_mod))
        self.gen_load_int(reg.r2.value, mod_addr, cond=cond)
        self.gen_load_int(reg.lr.value, self.curraddr()+self.size_of_gen_load_int+WORD, cond=cond)
        self.MOV_rr(reg.pc.value, reg.r2.value, cond=cond)
        self.LDM(reg.sp.value, range(2, 12), w=1, cond=cond) # XXX Replace with POP instr. someday

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
        """r is the register number, value is the value to be loaded to the
        register"""
        assert r != reg.ip.value, 'ip is used to load int'
        ip = reg.ip.value

        self.MOV_ri(r, (value & 0xFF), cond=cond)
        for offset in range(8, 25, 8):
            t = (value >> offset) & 0xFF
            self.MOV_ri(ip, t, cond=cond)
            self.ORR_rr(r, r, ip, offset, cond=cond)

    # regalloc support
    def regalloc_mov(self, prev_loc, loc):
        if isinstance(prev_loc, ConstInt):
            # XXX check size of imm for current instr
            self.gen_load_int(loc.value, prev_loc.getint())
        else:
            self.MOV_rr(loc.value, prev_loc.value)

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
        self.checks = True
        self.n_data=0

    _space_for_jump = 10 * WORD
    def writechar(self, char):
        if self.checks and not self._pos < self._size - self._space_for_jump:
            self.checks = False
            self._add_more_mem()
            self.checks = True
        assert self._pos < self._size
        AbstractARMv7Builder.writechar(self, char)

    def _add_more_mem(self):
        new_mem = alloc(self._size)
        new_mem_addr = rffi.cast(lltype.Signed, new_mem)
        self.PUSH([reg.r0.value])
        self.gen_load_int(reg.r0.value, new_mem_addr)
        self.MOV_rr(reg.pc.value, reg.r0.value)
        self._dump_trace('data%d.asm' % self.n_data)
        self.n_data+=1
        self._data = new_mem
        self._pos = 0
        self.LDM(reg.sp.value, [reg.r0.value], w=1) # XXX Replace with POP instr. someday

define_instructions(AbstractARMv7Builder)
