from pypy.jit.codegen.ppc import codebuf, rgenop
from pypy.rpython.lltypesystem import lltype
from pypy.jit.codegen.test import rgenop_tests
from pypy.rpython.test.test_llinterp import interpret
from pypy.jit.codegen.ppc.test import test_rgenop

class LLTypeRGenOp(rgenop.RPPCGenOp):
    MachineCodeBlock = codebuf.LLTypeMachineCodeBlock
    ExistingCodeBlock = codebuf.LLTypeExistingCodeBlock

def test_simple():
    FUNC = lltype.FuncType([lltype.Signed], lltype.Signed)
    def f(n):
        rgenop = LLTypeRGenOp()
        sigtoken = rgenop.sigToken(FUNC)
        builder, gv_add_one, [gv_x] = rgenop.newgraph(sigtoken, "adder")
        builder.start_writing()
        gv_result = builder.genop2("int_add", gv_x, rgenop.genconst(n))
        builder.finish_and_return(sigtoken, gv_result)
        builder.end()
    res = interpret(f, [5], policy=rgenop_tests.GENOP_POLICY)
    # just testing that this didn't crash
