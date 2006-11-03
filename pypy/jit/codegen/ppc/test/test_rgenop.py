import py
from pypy.jit.codegen.ppc.rgenop import RPPCGenOp
from pypy.jit.codegen.test.rgenop_tests import AbstractRGenOpTests

class FewRegisters(RPPCGenOp):
    MINUSERREG = 29

class TestRPPCGenop(AbstractRGenOpTests):
    RGenOp = RPPCGenOp

class TestRPPCGenopNoRegs(AbstractRGenOpTests):
    RGenOp = FewRegisters

    def compile(self, runner, argtypes):
        py.test.skip("Skip compiled tests w/ restricted register allocator")
