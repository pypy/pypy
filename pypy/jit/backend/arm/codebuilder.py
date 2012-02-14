from pypy.jit.backend.arm import arch
from pypy.jit.backend.arm import conditions as cond
from pypy.jit.backend.arm import registers as reg
from pypy.jit.backend.arm.arch import (WORD, FUNC_ALIGN)
from pypy.jit.backend.arm.instruction_builder import define_instructions
from pypy.jit.backend.llsupport.asmmemmgr import BlockBuilderMixin
from pypy.rlib.objectmodel import we_are_translated
from pypy.rpython.lltypesystem import lltype, rffi, llmemory
from pypy.tool.udir import udir

clear_cache = rffi.llexternal(
    "__clear_cache",
    [llmemory.Address, llmemory.Address],
    lltype.Void,
    _nowrapper=True,
    sandboxsafe=True)


def binary_helper_call(name):
    function = getattr(arch, 'arm_%s' % name)

    def f(self, c=cond.AL):
        """Generates a call to a helper function, takes its
        arguments in r0 and r1, result is placed in r0"""
        addr = rffi.cast(lltype.Signed, function)
        self.BL(addr, c)
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

    def VPOP(self, regs, cond=cond.AL):
        nregs = len(regs)
        assert nregs > 0 and nregs <= 16
        freg = regs[0]
        D = (freg & 0x10) >> 4
        Dd = (freg & 0xF)
        nregs *= 2
        instr = (cond << 28
                | 0xCBD << 16
                | D << 22
                | Dd << 12
                | 0xB << 8
                | nregs)
        self.write32(instr)

    def VMOV_rc(self, rt, rt2, dm, cond=cond.AL):
        """This instruction copies two words from two ARM core registers into a
        doubleword extension register, or from a doubleword extension register
        to two ARM core registers.
        """
        op = 1
        instr = (cond << 28
                | 0xC << 24
                | 0x4 << 20
                | op << 20
                | (rt2 & 0xF) << 16
                | (rt & 0xF) << 12
                | 0xB << 8
                | 0x1 << 4
                | (dm & 0xF))
        self.write32(instr)

    # VMOV<c> <Dm>, <Rt>, <Rt2>
    def VMOV_cr(self, dm, rt, rt2, cond=cond.AL):
        """This instruction copies two words from two ARM core registers into a
        doubleword extension register, or from a doubleword extension register
        to two ARM core registers.
        """
        op = 0
        instr = (cond << 28
                | 0xC << 24
                | 0x4 << 20
                | op << 20
                | (rt2 & 0xF) << 16
                | (rt & 0xF) << 12
                | 0xB << 8
                | 0x1 << 4
                | (dm & 0xF))
        self.write32(instr)

    def VMOV_cc(self, dd, dm, cond=cond.AL):
        sz = 1  # for 64-bit mode
        instr = (cond << 28
                | 0xEB << 20
                | (dd & 0xF) << 12
                | 0x5 << 9
                | (sz & 0x1) << 8
                | 0x1 << 6
                | (dm & 0xF))
        self.write32(instr)

    def VCVT_float_to_int(self, target, source, cond=cond.AL):
        opc2 = 0x5
        sz = 1
        self._VCVT(target, source, cond, opc2, sz)

    def VCVT_int_to_float(self, target, source, cond=cond.AL):
        self._VCVT(target, source, cond, 0, 1)

    def _VCVT(self, target, source, cond, opc2, sz):
        D = 0x0
        M = 0
        op = 1
        instr = (cond << 28
                | 0xEB8 << 16
                | D << 22
                | opc2 << 16
                | (target & 0xF) << 12
                | 0x5 << 9
                | sz << 8
                | op << 7
                | 1 << 6
                | M << 5
                | (source & 0xF))
        self.write32(instr)

    def POP(self, regs, cond=cond.AL):
        instr = self._encode_reg_list(cond << 28 | 0x8BD << 16, regs)
        self.write32(instr)

    def BKPT(self):
        """Unconditional breakpoint"""
        self.write32(cond.AL << 28 | 0x1200070)

    # corresponds to the instruction vmrs APSR_nzcv, fpscr
    def VMRS(self, cond=cond.AL):
        self.write32(cond << 28 | 0xEF1FA10)

    def B(self, target, c=cond.AL):
        self.gen_load_int(reg.ip.value, target, cond=c)
        self.BX(reg.ip.value, c=c)

    def BX(self, reg, c=cond.AL):
        self.write32(c << 28 | 0x12FFF1 << 4 | (reg & 0xF))

    def B_offs(self, target_ofs, c=cond.AL):
        pos = self.currpos()
        target_ofs = target_ofs - (pos + arch.PC_OFFSET)
        assert target_ofs & 0x3 == 0
        self.write32(c << 28 | 0xA << 24 | (target_ofs >> 2) & 0xFFFFFF)

    def BL(self, addr, c=cond.AL):
        target = rffi.cast(rffi.INT, addr)
        self.gen_load_int(reg.ip.value, target, cond=c)
        self.BLX(reg.ip.value, c)

    def BLX(self, reg, c=cond.AL):
        self.write32(c << 28 | 0x12FFF3 << 4 | (reg & 0xF))

    def MOVT_ri(self, rd, imm16, c=cond.AL):
        """Move Top writes an immediate value to the top halfword of the
        destination register. It does not affect the contents of the bottom
        halfword."""
        self.write32(c << 28
                    | 0x3 << 24
                    | (1 << 22)
                    | ((imm16 >> 12) & 0xF) << 16
                    | (rd & 0xF) << 12
                    | imm16 & 0xFFF)

    def MOVW_ri(self, rd, imm16, c=cond.AL):
        """Encoding A2 of MOV, that allow to load a 16 bit constant"""
        self.write32(c << 28
                    | 0x3 << 24
                    | ((imm16 >> 12) & 0xF) << 16
                    | (rd & 0xF) << 12
                    | imm16 & 0xFFF)

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

    def gen_load_int(self, r, value, cond=cond.AL):
        """r is the register number, value is the value to be loaded to the
        register"""
        bottom = value & 0xFFFF
        top = value >> 16
        self.MOVW_ri(r, bottom, cond)
        if top:
            self.MOVT_ri(r, top, cond)
    size_of_gen_load_int = 2 * WORD


class OverwritingBuilder(AbstractARMv7Builder):
    def __init__(self, cb, start, size):
        AbstractARMv7Builder.__init__(self)
        self.cb = cb
        self.index = start
        self.end = start + size

    def currpos(self):
        return self.index

    def writechar(self, char):
        assert self.index <= self.end
        self.cb.overwrite(self.index, char)
        self.index += 1


class ARMv7Builder(BlockBuilderMixin, AbstractARMv7Builder):
    def __init__(self):
        AbstractARMv7Builder.__init__(self)
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

    # XXX remove and setup aligning in llsupport
    def materialize(self, asmmemmgr, allblocks, gcrootmap=None):
        size = self.get_relative_pos()
        malloced = asmmemmgr.malloc(size, size + 7)
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


define_instructions(AbstractARMv7Builder)
