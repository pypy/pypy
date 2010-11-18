from pypy.jit.backend.arm import arch
from pypy.jit.backend.arm import conditions as cond
from pypy.jit.backend.arm import registers as reg
from pypy.jit.backend.arm.arch import (WORD, FUNC_ALIGN)
from pypy.jit.backend.arm.instruction_builder import define_instructions

from pypy.rlib.rmmap import alloc, PTR
from pypy.rpython.annlowlevel import llhelper
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.jit.metainterp.history import ConstInt, BoxInt, BasicFailDescr

def binary_helper_call(name):
    signature = getattr(arch, 'arm_%s_sign' % name)
    function = getattr(arch, 'arm_%s' % name)
    def f(self, c=cond.AL):
        """Generates a call to a helper function, takes its
        arguments in r0 and r1, result is placed in r0"""
        addr = rffi.cast(lltype.Signed, llhelper(signature, function))
        if c == cond.AL:
            self.BL(addr)
        else:
            self.PUSH(range(2, 4), cond=c)
            self.BL(addr, cond=c, some_reg=reg.r2)
            self.POP(range(2,4), cond=c)
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

    def NOP(self):
        self.MOV_rr(0, 0)

    def PUSH(self, regs, cond=cond.AL):
        assert reg.sp.value not in regs
        instr = self._encode_reg_list(cond << 28 | 0x92D << 16, regs)
        self.write32(instr)

    def POP(self, regs, cond=cond.AL):
        assert reg.lr.value not in regs
        instr = self._encode_reg_list(cond << 28 | 0x8BD << 16, regs)
        self.write32(instr)

    def BKPT(self, cond=cond.AL):
        self.write32(cond << 28 | 0x1200070)

    def B(self, target, c=cond.AL, some_reg=None):
        if c == cond.AL:
            self.ensure_can_fit(2*WORD)
            self.LDR_ri(reg.pc.value, reg.pc.value, -arch.PC_OFFSET/2)
            self.write32(target)
        else:
            assert some_reg is not None
            self.ensure_can_fit(self.size_of_gen_load_int+WORD)
            self.gen_load_int(some_reg.value, target, cond=c)
            self.MOV_rr(reg.pc.value, some_reg.value, cond=c)

    def BL(self, target, c=cond.AL, some_reg=None):
        if c == cond.AL:
            self.ensure_can_fit(3*WORD)
            self.ADD_ri(reg.lr.value, reg.pc.value, arch.PC_OFFSET/2)
            self.LDR_ri(reg.pc.value, reg.pc.value, imm=-arch.PC_OFFSET/2)
            self.write32(target)
        else:
            assert some_reg is not None
            self.ensure_can_fit(self.size_of_gen_load_int*2+WORD)
            self.gen_load_int(some_reg.value, target, cond=c)
            self.gen_load_int(reg.lr.value, self.curraddr()+self.size_of_gen_load_int+WORD, cond=c)
            self.MOV_rr(reg.pc.value, some_reg.value, cond=c)

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

    def currpos(self):
        return self._pos

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

    def ensure_can_fit(self, n):
        """ensure after this call there is enough space for n instructions
        in a contiguous memory chunk or raise an exception"""
        if not self._pos + n < self._size:
            raise ValueError

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
        if self.checks and not self._pos < self._size - self._space_for_jump - WORD:
            self._add_more_mem()
        assert self._pos < self._size - 1
        AbstractARMv7Builder.writechar(self, char)

    def _add_more_mem(self):
        self.checks = False
        new_mem = alloc(self._size)
        new_mem_addr = rffi.cast(lltype.Signed, new_mem)
        self.LDR_ri(reg.pc.value, reg.pc.value, -4)
        self.write32(new_mem_addr)
        self._dump_trace('data%04d.asm' % self.n_data)
        self.n_data += 1
        self._data = new_mem
        self._pos = 0
        self.checks = True

    def ensure_can_fit(self, n):
        """ensure after this call there is enough space for n instructions
        in a contiguous memory chunk"""
        if not self._pos + n + self._space_for_jump < self._size - WORD:
            self._add_more_mem()

define_instructions(AbstractARMv7Builder)
