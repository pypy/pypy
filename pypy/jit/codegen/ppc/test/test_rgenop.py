from pypy.jit.codegen.ppc.rgenop import RPPCGenOp
from pypy.jit.codegen.test.rgenop_tests import AbstractRGenOpTests

class TestRPPCGenop(AbstractRGenOpTests):
    RGenOp = RPPCGenOp
