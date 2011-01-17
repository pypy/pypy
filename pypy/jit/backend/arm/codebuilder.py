from pypy.jit.backend.arm import arch
from pypy.jit.backend.arm import conditions as cond
from pypy.jit.backend.arm import registers as reg
from pypy.jit.backend.arm.arch import (WORD, FUNC_ALIGN)
from pypy.jit.backend.arm.instruction_builder import define_instructions

from pypy.rlib.rmmap import alloc, PTR
from pypy.rpython.annlowlevel import llhelper
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.jit.metainterp.history import ConstInt, BoxInt, AbstractFailDescr
from pypy.rlib.objectmodel import we_are_translated
from pypy.jit.backend.llsupport.asmmemmgr import BlockBuilderMixin
from pypy.tool.udir import udir

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
            self.BL(addr, c)
            self.POP(range(2,4), cond=c)
    return f

class AbstractARMv7Builder(object):

    def __init__(self):
        pass

    def align(self):
        while(self.currpos() % FUNC_ALIGN != 0):
            self.writechar(chr(0))
    def NOP(self):
        self.MOV_rr(0, 0)

    def PUSH(self, regs, cond=cond.AL):
        assert reg.sp.value not in regs
        instr = self._encode_reg_list(cond << 28 | 0x92D << 16, regs)
        self.write32(instr)

    def VPUSH(self, regs, cond=cond.AL):
        nregs = len(regs) 
        assert nregs > 0 and nregs <= 16
        freg = regs[0]
        D = (freg & 0x10) >> 4
        Dd = (freg & 0xF)
        nregs *= 2 
        instr = (cond << 28 
                | 0xD2D << 16 
                | D << 22 
                | Dd << 12
                | 0xB << 8
                | nregs)
        self.write32(instr)

    def POP(self, regs, cond=cond.AL):
        assert reg.lr.value not in regs
        instr = self._encode_reg_list(cond << 28 | 0x8BD << 16, regs)
        self.write32(instr)

    def BKPT(self, cond=cond.AL):
        self.write32(cond << 28 | 0x1200070)

    def B(self, target, c=cond.AL):
        if c == cond.AL:
            self.LDR_ri(reg.pc.value, reg.pc.value, -arch.PC_OFFSET/2)
            self.write32(target)
        else:
            self.gen_load_int(reg.ip.value, target, cond=c)
            self.MOV_rr(reg.pc.value, reg.ip.value, cond=c)

    def B_offs(self, target_ofs, c=cond.AL):
        pos = self.currpos()
        if target_ofs > pos:
            raise NotImplementedError
        else:
            target_ofs = pos - target_ofs
            target = WORD + target_ofs + arch.PC_OFFSET/2
            if target >= 0 and target <= 0xFF:
                self.SUB_ri(reg.pc.value, reg.pc.value, target, cond=c)
            else:
                assert c == cond.AL
                self.LDR_ri(reg.ip.value, reg.pc.value, cond=c)
                self.SUB_rr(reg.pc.value, reg.pc.value, reg.ip.value, cond=c)
                target += 2 * WORD
                self.write32(target)

    def BL(self, target, c=cond.AL):
        if c == cond.AL:
            self.ADD_ri(reg.lr.value, reg.pc.value, arch.PC_OFFSET/2)
            self.LDR_ri(reg.pc.value, reg.pc.value, imm=-arch.PC_OFFSET/2)
            self.write32(target)
        else:
            self.gen_load_int(reg.ip.value, target, cond=c)
            self.ADD_ri(reg.lr.value, reg.pc.value, arch.PC_OFFSET/2)
            self.MOV_rr(reg.pc.value, reg.ip.value, cond=c)

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
        raise NotImplementedError

    def currpos(self):
        raise NotImplementedError

    size_of_gen_load_int = 4 * WORD
    ofs_shift = zip(range(8, 25, 8), range(12, 0, -4))
    def gen_load_int(self, r, value, cond=cond.AL):
        """r is the register number, value is the value to be loaded to the
        register"""
        self.MOV_ri(r, (value & 0xFF), cond=cond)
        for offset, shift in self.ofs_shift:
            b = (value >> offset) & 0xFF
            if b == 0:
                continue
            t = b | (shift << 8)
            self.ORR_ri(r, r, imm=t, cond=cond)


class OverwritingBuilder(AbstractARMv7Builder):
    def __init__(self, cb, start, size):
        AbstractARMv7Builder.__init__(self)
        self.cb = cb
        self.index = start
        self.end = start + size

    def writechar(self, char):
        assert self.index <= self.end
        self.cb.overwrite(self.index, char)
        self.index += 1

class ARMv7Builder(BlockBuilderMixin, AbstractARMv7Builder):
    def __init__(self):
        AbstractARMv7Builder.__init__(self)
        self.init_block_builder()

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

    # XXX remove and setup aligning in llsupport
    def materialize(self, asmmemmgr, allblocks, gcrootmap=None):
        size = self.get_relative_pos()
        malloced = asmmemmgr.malloc(size, size+7)
        allblocks.append(malloced)
        rawstart = malloced[0]
        while(rawstart % FUNC_ALIGN != 0):
            rawstart += 1
        self.copy_to_raw_memory(rawstart)
        if self.gcroot_markers is not None:
            assert gcrootmap is not None
            for pos, mark in self.gcroot_markers:
                gcrootmap.put(rawstart + pos, mark)
        return rawstart

    def copy_to_raw_memory(self, addr):
        self._copy_to_raw_memory(addr)
        self._dump(addr, "jit-backend-dump", 'arm')

    def currpos(self):
        return self.get_relative_pos()


define_instructions(AbstractARMv7Builder)
