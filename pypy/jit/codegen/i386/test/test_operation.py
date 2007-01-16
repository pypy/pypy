from pypy.rlib.objectmodel import specialize
from pypy.jit.codegen.test.operation_tests import OperationTests
from pypy.jit.codegen.i386.rgenop import RI386GenOp
from pypy.rpython.memory.lltypelayout import convert_offset_to_int

def conv(n):
    if not isinstance(n, int):
        if isinstance(n, tuple):
            n = tuple(map(conv, n))
        else:
            n = convert_offset_to_int(n)
    return n


class RGenOpPacked(RI386GenOp):
    """Like RI386GenOp, but produces concrete offsets in the tokens
    instead of llmemory.offsets.  These numbers may not agree with
    your C compiler's.
    """

    @staticmethod
    @specialize.memo()
    def fieldToken(T, name):
        return conv(RI386GenOp.fieldToken(T, name))

    @staticmethod
    @specialize.memo()
    def arrayToken(A):
        return conv(RI386GenOp.arrayToken(A))

    @staticmethod
    @specialize.memo()
    def allocToken(T):
        return conv(RI386GenOp.allocToken(T))

    @staticmethod
    @specialize.memo()
    def varsizeAllocToken(A):
        return conv(RI386GenOp.varsizeAllocToken(A))


class I386TestMixin(object):
    RGenOp = RGenOpPacked

class TestOperation(I386TestMixin, OperationTests):
    pass

    # for the individual tests see
    # ====> ../../test/operation_tests.py
