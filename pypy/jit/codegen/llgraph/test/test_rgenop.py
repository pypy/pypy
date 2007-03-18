import py
from pypy.rpython.lltypesystem import lltype
from pypy.jit.codegen.llgraph.rgenop import RGenOp
from pypy.jit.codegen.llgraph.llimpl import testgengraph
from pypy.jit.codegen.test.rgenop_tests import AbstractRGenOpTests
from pypy.rpython.test.test_llinterp import gengraph, interpret


class TestLLGraphRGenop(AbstractRGenOpTests):
    RGenOp = RGenOp

    def setup_method(self, meth):
        if 'ovfcheck' in meth.__name__:
            py.test.skip("no chance (the llinterpreter has no rtyper)")
        AbstractRGenOpTests.setup_method(self, meth)

    def getcompiled(self, runner, argtypes, annotatorpolicy):
        def quasi_compiled_runner(*args):
            return interpret(runner, args, policy=annotatorpolicy)
        return quasi_compiled_runner

    def directtesthelper(self, FUNC, func):
        from pypy.annotation import model as annmodel
        argtypes = [annmodel.lltype_to_annotation(T) for T in FUNC.TO.ARGS]
        t, rtyper, graph = gengraph(func, argtypes)
        return rtyper.getcallable(graph)

    # for the individual tests see
    # ====> ../../test/rgenop_tests.py


def test_not_calling_end_explodes():
    F1 = lltype.FuncType([lltype.Signed], lltype.Signed)
    rgenop = RGenOp()
    sigtoken = rgenop.sigToken(F1)
    builder, gv_adder, [gv_x] = rgenop.newgraph(sigtoken, "adder")
    builder.start_writing()
    gv_result = builder.genop2("int_add", gv_x, rgenop.genconst(5))
    builder.finish_and_return(sigtoken, gv_result)
    #builder.end() <--- the point
    ptr = gv_adder.revealconst(lltype.Ptr(F1))
    py.test.raises(AssertionError, "testgengraph(ptr._obj.graph, [1])")
