import pypy.jit.backend.ppc.ppcgen.condition as c
from pypy.rlib.rarithmetic import r_uint, r_longlong, intmask
from pypy.jit.backend.ppc.ppcgen.arch import (MAX_REG_PARAMS, IS_PPC_32, WORD,
                                              BACKCHAIN_SIZE)
from pypy.jit.metainterp.history import FLOAT
from pypy.rlib.unroll import unrolling_iterable
import pypy.jit.backend.ppc.ppcgen.register as r
from pypy.rpython.lltypesystem import rffi, lltype

def gen_emit_cmp_op(condition, signed=True):
    def f(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        # do the comparison
        self.mc.cmp_op(0, l0.value, l1.value,
                       imm=l1.is_imm(), signed=signed)
        # After the comparison, place the result
        # in the first bit of the CR
        if condition == c.LT or condition == c.U_LT:
            self.mc.cror(0, 0, 0)
        elif condition == c.LE or condition == c.U_LE:
            self.mc.cror(0, 0, 2)
        elif condition == c.EQ:
            self.mc.cror(0, 2, 2)
        elif condition == c.GE or condition == c.U_GE:
            self.mc.cror(0, 1, 2)
        elif condition == c.GT or condition == c.U_GT:
            self.mc.cror(0, 1, 1)
        elif condition == c.NE:
            self.mc.cror(0, 0, 1)
        else:
            assert 0, "condition not known"

        resval = res.value 
        # move the content of the CR to resval
        self.mc.mfcr(resval)       
        # zero out everything except of the result
        self.mc.rlwinm(resval, resval, 1, 31, 31)
    return f

def gen_emit_unary_cmp_op(condition):
    def f(self, op, arglocs, regalloc):
        reg, res = arglocs

        self.mc.cmp_op(0, reg.value, 0, imm=True)
        if condition == c.IS_ZERO:
            self.mc.cror(0, 2, 2)
        elif condition == c.IS_TRUE:
            self.mc.cror(0, 0, 1)
        else:
            assert 0, "condition not known"

        self.mc.mfcr(res.value)
        self.mc.rlwinm(res.value, res.value, 1, 31, 31)
    return f

def encode32(mem, i, n):
    mem[i+3] = chr(n & 0xFF)
    mem[i+2] = chr((n >> 8) & 0xFF)
    mem[i+1] = chr((n >> 16) & 0xFF)
    mem[i] = chr((n >> 24) & 0xFF)

# XXX this sign extension looks a bit strange ...
# It is important for PPC64.
def decode32(mem, index):
    value = ( ord(mem[index+3])
            | ord(mem[index+2]) << 8
            | ord(mem[index+1]) << 16
            | ord(mem[index]) << 24)

    rffi_value = rffi.cast(rffi.INT, value)
    # do sign extension
    return rffi.cast(lltype.Signed, rffi_value)

def encode64(mem, i, n):
    mem[i+7] = chr(n & 0xFF)
    mem[i+6] = chr((n >> 8) & 0xFF)
    mem[i+5] = chr((n >> 16) & 0xFF)
    mem[i+4] = chr((n >> 24) & 0xFF)
    mem[i+3] = chr((n >> 32) & 0xFF)
    mem[i+2] = chr((n >> 40) & 0xFF)
    mem[i+1] = chr((n >> 48) & 0xFF)
    mem[i]   = chr((n >> 56) & 0xFF)

def decode64(mem, index):
    value = 0
    for x in range(8):
        value |= (ord(mem[index + x]) << (56 - x * 8))
    return intmask(value)

def count_reg_args(args):
    reg_args = 0
    words = 0
    count = 0
    for x in range(min(len(args), MAX_REG_PARAMS)):
        if args[x].type == FLOAT:
            assert 0, "not implemented yet"
        else:
            count += 1
            words += 1
        reg_args += 1
        if words > MAX_REG_PARAMS:
            reg_args = x
            break
    return reg_args

class saved_registers(object):
    def __init__(self, assembler, regs_to_save, regalloc=None):
        self.mc = assembler
        self.regalloc = regalloc
        if self.regalloc:
            assert 0, "not implemented yet"
        else:
            self.regs = regs_to_save

    def __enter__(self):
        if len(self.regs) > 0:
            if IS_PPC_32:
                space = BACKCHAIN_SIZE + WORD * len(self.regs)
                self.mc.stwu(r.SP.value, r.SP.value, -space)
            else:
                space = (6 + MAX_REG_PARAMS + len(self.regs)) * WORD
                self.mc.stdu(r.SP.value, r.SP.value, -space)
            for i, reg in enumerate(self.regs):
                if IS_PPC_32:
                    self.mc.stw(reg.value, r.SP.value, BACKCHAIN_SIZE + i * WORD)
                else:
                    self.mc.std(reg.value, r.SP.value, (14 + i) * WORD)

    def __exit__(self, *args):
        if len(self.regs) > 0:
            for i, reg in enumerate(self.regs):
                if IS_PPC_32:
                    self.mc.lwz(reg.value, r.SP.value, BACKCHAIN_SIZE + i * WORD)
                else:
                    self.mc.ld(reg.value, r.SP.value, (14 + i) * WORD)
            if IS_PPC_32:
                space = BACKCHAIN_SIZE + WORD * len(self.regs)
            else:
                space = (6 + MAX_REG_PARAMS + len(self.regs)) * WORD
            self.mc.addi(r.SP.value, r.SP.value, space)

class Saved_Volatiles(object):
    """ used in _gen_leave_jitted_hook_code to save volatile registers
        in ENCODING AREA around calls
    """

    def __init__(self, codebuilder):
        self.mc = codebuilder

    def __enter__(self):
        """ before a call, volatile registers are saved in ENCODING AREA
        """
        for i, reg in enumerate(r.VOLATILES):
            if IS_PPC_32:
                self.mc.stw(reg.value, r.SPP.value, i * WORD)
            else:
                self.mc.std(reg.value, r.SPP.value, i * WORD)

    def __exit__(self, *args):
        """ after call, volatile registers have to be restored
        """
        for i, reg in enumerate(r.VOLATILES):
            if IS_PPC_32:
                self.mc.lwz(reg.value, r.SPP.value, i * WORD)
            else:
                self.mc.ld(reg.value, r.SPP.value, i * WORD)
