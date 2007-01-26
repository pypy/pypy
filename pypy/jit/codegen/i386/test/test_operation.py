from pypy.rlib.objectmodel import specialize
from pypy.rpython.lltypesystem import lltype
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

    def test_specific_bug(self):
        rgenop = self.RGenOp()
        FUNC0 = lltype.FuncType([], lltype.Signed)
        A = lltype.GcArray(lltype.Signed)
        a = lltype.malloc(A, 2, immortal=True)
        gv_a = rgenop.genconst(a)
        signed_kind = rgenop.kindToken(lltype.Signed)
        arraytoken = rgenop.arrayToken(A)
        builder0, gv_callable, _ = rgenop.newgraph(rgenop.sigToken(FUNC0),
                                                   'generated')
        builder0.start_writing()
        builder0.genop_setarrayitem(arraytoken, gv_a, rgenop.genconst(0),
                                    rgenop.genconst(1))
        builder0.genop_setarrayitem(arraytoken, gv_a, rgenop.genconst(1),
                                    rgenop.genconst(2))
        v0 = builder0.genop_getarrayitem(arraytoken, gv_a, rgenop.genconst(0))
        v1 = builder0.genop_getarrayitem(arraytoken, gv_a, rgenop.genconst(1))
        v2 = builder0.genop2('int_add', v0, v1)
        builder1 = builder0.pause_writing([v2])
        builder1.start_writing()
        args_gv = [v2]
        label0 = builder1.enter_next_block([signed_kind], args_gv)
        [v3] = args_gv
        args_gv = [v3]
        label1 = builder1.enter_next_block([signed_kind], args_gv)
        [v4] = args_gv
        builder1.finish_and_return(rgenop.sigToken(FUNC0), v4)
        builder0.end()

    def test_idiv_bug(self):
        def fn(x, y):
            return (x+1) // (-y) + x + y      # generated a bogus "idiv edx"
        fp = self.rgen(fn, [int, int])
        assert fp(5, 7) == fn(5, 7)

    def test_imod_bug(self):
        def fn(x, y):
            return (x+1) % (-y) + x + y
        fp = self.rgen(fn, [int, int])
        assert fp(5, 7) == fn(5, 7)

    def test_imod_bug_2(self):
        def fn(x, y):
            z = -y
            z += x % z
            return z
        fp = self.rgen(fn, [int, int])
        assert fp(5, 7) == fn(5, 7)
