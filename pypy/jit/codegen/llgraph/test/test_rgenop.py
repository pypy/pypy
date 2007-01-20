import py
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.jit.codegen.llgraph.rgenop import RGenOp
from pypy.jit.codegen.llgraph.llimpl import testgengraph
from pypy.jit.codegen.test.rgenop_tests import AbstractRGenOpTests
from pypy.rpython.test.test_llinterp import gengraph, interpret


class TestLLGraphRGenop(AbstractRGenOpTests):
    RGenOp = RGenOp

    def cast(self, gv, nb_args):
        F1 = lltype.FuncType([lltype.Signed] * nb_args, lltype.Signed)
        ptr = gv.revealconst(lltype.Ptr(F1))
        def runner(*args):
            return testgengraph(ptr._obj.graph, list(args))
        return runner

    def getcompiled(self, runner, argtypes, annotatorpolicy):
        def quasi_compiled_runner(*args):
            return interpret(runner, args, policy=annotatorpolicy)
        return quasi_compiled_runner

    # for the individual tests see
    # ====> ../../test/rgenop_tests.py


def test_read_frame_var():
    from pypy.annotation import model as annmodel

    def reader(base, info):
        return RGenOp.read_frame_var(lltype.Signed, base, info, 0)

    t, rtyper, reader_graph = gengraph(reader,
                                       [annmodel.SomeAddress(),
                                        annmodel.SomePtr(llmemory.GCREF)])
    reader_ptr = rtyper.getcallable(reader_graph)

    F1 = lltype.FuncType([lltype.Signed], lltype.Signed)
    rgenop = RGenOp()
    signed_kind = rgenop.kindToken(lltype.Signed)
    sigtoken = rgenop.sigToken(F1)
    gv_reader = RGenOp.constPrebuiltGlobal(reader_ptr)
    readertoken = rgenop.sigToken(lltype.typeOf(reader_ptr).TO)

    builder, gv_f, [gv_x] = rgenop.newgraph(sigtoken, "f")
    builder.start_writing()

    gv_y = builder.genop2("int_mul", gv_x, rgenop.genconst(2))
    gv_base = builder.get_frame_base()
    gv_info = builder.get_frame_info([gv_y])
    gv_z = builder.genop_call(readertoken, gv_reader, [gv_base, gv_info])
    builder.finish_and_return(sigtoken, gv_z)
    builder.end()

    ptr = gv_f.revealconst(lltype.Ptr(F1))
    res = testgengraph(ptr._obj.graph, [21])
    assert res == 42

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
