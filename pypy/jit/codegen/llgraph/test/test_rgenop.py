import py
from pypy.rpython.lltypesystem import lltype
from pypy.jit.codegen.llgraph.rgenop import RGenOp
from pypy.jit.codegen.llgraph.llimpl import testgengraph
from pypy.jit.codegen.test.rgenop_tests import AbstractRGenOpTests
from pypy.rpython.test.test_llinterp import interpret


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
