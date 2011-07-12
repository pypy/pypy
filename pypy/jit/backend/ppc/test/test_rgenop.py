import py
from pypy.jit.codegen.ppc.rgenop import RPPCGenOp
from pypy.rpython.lltypesystem import lltype
from pypy.jit.codegen.test.rgenop_tests import FUNC, FUNC2
from pypy.jit.codegen.test.rgenop_tests import AbstractRGenOpTestsDirect
from pypy.jit.codegen.test.rgenop_tests import AbstractRGenOpTestsCompile
from ctypes import cast, c_int, c_void_p, CFUNCTYPE
from pypy.jit.codegen.ppc import instruction as insn

# for the individual tests see
# ====> ../../test/rgenop_tests.py

class FewRegisters(RPPCGenOp):
    freeregs = {
        insn.GP_REGISTER:insn.gprs[3:6],
        insn.FP_REGISTER:insn.fprs,
        insn.CR_FIELD:insn.crfs[:1],
        insn.CT_REGISTER:[insn.ctr]}

class FewRegistersAndScribble(FewRegisters):
    DEBUG_SCRIBBLE = True

class TestRPPCGenopDirect(AbstractRGenOpTestsDirect):
    RGenOp = RPPCGenOp

class TestRPPCGenopCompile(AbstractRGenOpTestsCompile):
    RGenOp = RPPCGenOp    

class TestRPPCGenopNoRegs(AbstractRGenOpTestsDirect):
    RGenOp = FewRegisters

class TestRPPCGenopNoRegsAndScribble(AbstractRGenOpTestsDirect):
    RGenOp = FewRegistersAndScribble
