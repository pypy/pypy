from pypy.rpython.lltypesystem import lltype
from pypy.jit.codegen.i386.rgenop import RI386GenOp
from pypy.jit.codegen.test.rgenop_tests import AbstractRGenOpTests

class TestRI386Genop(AbstractRGenOpTests):
    RGenOp = RI386GenOp

    # for the individual tests see
    # ====> ../../test/rgenop_tests.py

    def test_array_of_ints(self):
        from pypy.jit.codegen.i386.test.test_operation import RGenOpPacked
        rgenop = RGenOpPacked()
        A = lltype.GcArray(lltype.Signed)
        FUNC3 = lltype.FuncType([lltype.Signed]*3, lltype.Signed)
        varsizealloctoken = rgenop.varsizeAllocToken(A)
        arraytoken = rgenop.arrayToken(A)
        signed_kind = rgenop.kindToken(lltype.Signed)
        # ------------------------------------------------------------
        builder0, gv_callable, [v0, v1, v2] = rgenop.newgraph(
            rgenop.sigToken(FUNC3), 'generated')
        builder0.start_writing()
        v3 = builder0.genop_malloc_varsize(varsizealloctoken,
                                           rgenop.genconst(2))
        v4 = builder0.genop1('ptr_iszero', v3)
        builder1 = builder0.jump_if_false(v4, [v2, v0, v3, v1])
        builder2 = builder0.pause_writing([])
        builder1.start_writing()
        builder1.genop_setarrayitem(arraytoken, v3, rgenop.genconst(0), v0)
        builder1.genop_setarrayitem(arraytoken, v3, rgenop.genconst(1), v1)
        v5 = builder1.genop_getarrayitem(arraytoken, v3, v2)
        v6 = builder1.genop_getarraysize(arraytoken, v3)
        v7 = builder1.genop2('int_mul', v5, v6)
        builder3 = builder1.pause_writing([v7])
        builder3.start_writing()
        args_gv = [v7]
        label0 = builder3.enter_next_block([signed_kind], args_gv)
        [v8] = args_gv
        builder4 = builder3.pause_writing([v8])
        builder2.start_writing()
        builder2.finish_and_goto([rgenop.genconst(-1)], label0)
        builder4.start_writing()
        args_gv = [v8]
        label1 = builder4.enter_next_block([signed_kind], args_gv)
        [v9] = args_gv
        builder4.finish_and_return(rgenop.sigToken(FUNC3), v9)
        builder0.end()
        
        fnptr = self.cast(gv_callable, 3)
        res = fnptr(21, -21, 0)
        assert res == 42
