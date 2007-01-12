import py
from pypy.jit.codegen.ppc.rgenop import RPPCGenOp
from pypy.rpython.lltypesystem import lltype
from pypy.jit.codegen.test.rgenop_tests import AbstractRGenOpTests, FUNC, FUNC2
from ctypes import cast, c_int, c_void_p, CFUNCTYPE
from pypy.jit.codegen.ppc import instruction as insn

class FewRegisters(RPPCGenOp):
    freeregs = {
        insn.GP_REGISTER:insn.gprs[3:6],
        insn.FP_REGISTER:insn.fprs,
        insn.CR_FIELD:insn.crfs[:1],
        insn.CT_REGISTER:[insn.ctr]}

class TestRPPCGenop(AbstractRGenOpTests):
    RGenOp = RPPCGenOp

    def test_multiple_cmps(self):
        # return x>y + 10*x<y + 100*x<=y + 1000*x>=y + 10000*x==y + 100000*x!=y
        rgenop = self.RGenOp()
        signed_kind = rgenop.kindToken(lltype.Signed)
        sigtoken = rgenop.sigToken(FUNC2)
        builder, gv_callable, [gv_x, gv_y] = rgenop.newgraph(sigtoken,
                                                             "multicmp")

        args_gv = [gv_x, gv_y]
        builder.enter_next_block([signed_kind, signed_kind], args_gv)
        [gv_x, gv_y] = args_gv

        gv_gt = builder.genop2("int_gt", gv_x, gv_y)
        gv_lt = builder.genop2("int_lt", gv_x, gv_y)
        gv_ge = builder.genop2("int_ge", gv_x, gv_y)
        gv_le = builder.genop2("int_le", gv_x, gv_y)
        gv_eq = builder.genop2("int_eq", gv_x, gv_y)
        gv_ne = builder.genop2("int_ne", gv_x, gv_y)

        gv_gt2 = gv_gt
        gv_lt2 = builder.genop2("int_mul", rgenop.genconst(10), gv_lt)
        gv_ge2 = builder.genop2("int_mul", rgenop.genconst(100), gv_ge)
        gv_le2 = builder.genop2("int_mul", rgenop.genconst(1000), gv_le)
        gv_eq2 = builder.genop2("int_mul", rgenop.genconst(10000), gv_eq)
        gv_ne2 = builder.genop2("int_mul", rgenop.genconst(100000), gv_ne)

        gv_r0 = gv_gt
        gv_r1 = builder.genop2("int_add", gv_r0, gv_lt2)
        gv_r2 = builder.genop2("int_add", gv_r1, gv_ge2)
        gv_r3 = builder.genop2("int_add", gv_r2, gv_le2)
        gv_r4 = builder.genop2("int_add", gv_r3, gv_eq2)
        gv_r5 = builder.genop2("int_add", gv_r4, gv_ne2)

        builder.finish_and_return(sigtoken, gv_r5)
        builder.end()
        fnptr = cast(c_void_p(gv_callable.value), CFUNCTYPE(c_int, c_int))
        res = fnptr(1, 2)
        assert res == 101010
        res = fnptr(1, 1)
        assert res ==  11100
        res = fnptr(2, 1)
        assert res == 100101

    def test_flipped_cmpwi(self):
        # return
        # 1>x + 10*(1<x) + 100*(1>=x) + 1000*(1<=x) + 10000*(1==x) + 100000*(1!=x)
        rgenop = self.RGenOp()
        signed_kind = rgenop.kindToken(lltype.Signed)
        sigtoken = rgenop.sigToken(FUNC)
        builder, gv_callable, [gv_x] = rgenop.newgraph(sigtoken,
                                                       "multicmp")
        gv_one = rgenop.genconst(1)

        gv_gt = builder.genop2("int_gt", gv_one, gv_x)
        gv_lt = builder.genop2("int_lt", gv_one, gv_x)
        gv_ge = builder.genop2("int_ge", gv_one, gv_x)
        gv_le = builder.genop2("int_le", gv_one, gv_x)
        gv_eq = builder.genop2("int_eq", gv_one, gv_x)
        gv_ne = builder.genop2("int_ne", gv_one, gv_x)

        gv_gt2 = gv_gt
        gv_lt2 = builder.genop2("int_mul", rgenop.genconst(10), gv_lt)
        gv_ge2 = builder.genop2("int_mul", rgenop.genconst(100), gv_ge)
        gv_le2 = builder.genop2("int_mul", rgenop.genconst(1000), gv_le)
        gv_eq2 = builder.genop2("int_mul", rgenop.genconst(10000), gv_eq)
        gv_ne2 = builder.genop2("int_mul", rgenop.genconst(100000), gv_ne)

        gv_r0 = gv_gt
        gv_r1 = builder.genop2("int_add", gv_r0, gv_lt2)
        gv_r2 = builder.genop2("int_add", gv_r1, gv_ge2)
        gv_r3 = builder.genop2("int_add", gv_r2, gv_le2)
        gv_r4 = builder.genop2("int_add", gv_r3, gv_eq2)
        gv_r5 = builder.genop2("int_add", gv_r4, gv_ne2)

        builder.finish_and_return(sigtoken, gv_r5)
        builder.end()
        fnptr = cast(c_void_p(gv_callable.value), CFUNCTYPE(c_int))

        res = fnptr(0)
        assert res == 100101

        res = fnptr(1)
        assert res ==  11100

        res = fnptr(2)
        assert res == 101010

    def test_longwinded_and_direct(self):
        py.test.skip("failing right now")

class TestRPPCGenopNoRegs(TestRPPCGenop):
    RGenOp = FewRegisters

    def compile(self, runner, argtypes):
        py.test.skip("Skip compiled tests w/ restricted register allocator")
