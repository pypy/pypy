from pypy.jit.codegen.test.operation_tests import OperationTests
from pypy.jit.codegen.ppc.rgenop import RPPCGenOp
from pypy.rpython.memory.lltypelayout import convert_offset_to_int
from pypy.rlib.objectmodel import specialize

def conv(n):
    if not isinstance(n, int):
        n = convert_offset_to_int(n)
    return n


class RGenOpPacked(RPPCGenOp):
    """Like RPPCGenOp, but produces concrete offsets in the tokens
    instead of llmemory.offsets.  These numbers may not agree with
    your C compiler's.
    """

    @staticmethod
    @specialize.memo()
    def fieldToken(T, name):
        return tuple(map(conv, RPPCGenOp.fieldToken(T, name)))

    @staticmethod
    @specialize.memo()
    def arrayToken(A):
        return tuple(map(conv, RPPCGenOp.arrayToken(A)))

    @staticmethod
    @specialize.memo()
    def allocToken(T):
        return conv(RPPCGenOp.allocToken(T))

    @staticmethod
    @specialize.memo()
    def varsizeAllocToken(A):
        return tuple(map(conv, RPPCGenOp.varsizeAllocToken(A)))


class PPCTestMixin(object):
    RGenOp = RGenOpPacked

class TestOperation(PPCTestMixin, OperationTests):
    pass
