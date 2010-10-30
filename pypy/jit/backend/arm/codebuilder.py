from pypy.jit.backend.arm import arch
from pypy.jit.backend.arm import conditions as cond
from pypy.jit.backend.arm import registers as reg
from pypy.jit.backend.arm.arch import (WORD, FUNC_ALIGN)
from pypy.jit.backend.arm.instruction_builder import define_instructions

from pypy.rlib.rmmap import alloc, PTR
from pypy.rpython.annlowlevel import llhelper
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.jit.metainterp.history import ConstInt, BoxInt, Box, BasicFailDescr

def binary_helper_call(name):
    signature = getattr(arch, 'arm_%s_sign' % name)
    function = getattr(arch, 'arm_%s' % name)
    def f(self, cond=cond.AL):
        """Generates a call to a helper function, takes its
        arguments in r0 and r1, result is placed in r0"""
        self.ensure_can_fit(self.size_of_gen_load_int*2+3*WORD)
        self.PUSH(range(2, 12), cond=cond)
        addr = rffi.cast(lltype.Signed, llhelper(signature, function))
        self.gen_load_int(reg.r2.value, addr, cond=cond)
        self.gen_load_int(reg.lr.value, self.curraddr()+self.size_of_gen_load_int+WORD, cond=cond)
        self.MOV_rr(reg.pc.value, reg.r2.value, cond=cond)
        self.LDM(reg.sp.value, range(2, 12), w=1, cond=cond) # XXX Replace with POP instr. someday
    return f

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

    def ensure_can_fit(self, n):
        raise NotImplentedError

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

    DIV = binary_helper_call('int_div')
    MOD = binary_helper_call('int_mod')
    UDIV = binary_helper_call('uint_div')

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


class ARMv7InMemoryBuilder(AbstractARMv7Builder):
    def __init__(self, start, end):
        map_size = end - start
        data = rffi.cast(PTR, start)
        self._init(data, map_size)


class ARMv7Builder(AbstractARMv7Builder):

    def __init__(self):
        map_size = 4096
        data = alloc(map_size)
        self._pos = 0
        self._init(data, map_size)
        self.checks = True
        self.n_data=0

    _space_for_jump = 2 * WORD
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
        self.LDR_ri(reg.pc.value, reg.pc.value, -4)
        self.write32(new_mem_addr)
        self._dump_trace('data%d.asm' % self.n_data)
        self.n_data += 1
        self._data = new_mem
        self._pos = 0

    def ensure_can_fit(self, n):
        """ensure after this call there is enough space for n instructions
        in a contiguous memory chunk"""
        if not self._pos + n + self._space_for_jump < self._size:
            self._add_more_mem()

define_instructions(AbstractARMv7Builder)
