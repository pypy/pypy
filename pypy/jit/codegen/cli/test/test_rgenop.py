import py
from pypy.rpython.ootypesystem import ootype
from pypy.jit.codegen.cli.rgenop import RCliGenOp
from pypy.jit.codegen.test.rgenop_tests import AbstractRGenOpTests, OOType
from pypy.translator.cli.test.runtest import compile_function

# test disabled, only two pass
class xTestRCliGenop(AbstractRGenOpTests):
    RGenOp = RCliGenOp
    T = OOType

    # for the individual tests see
    # ====> ../../test/rgenop_tests.py

    def getcompiled(self, fn, annotation, annotatorpolicy):
        return compile_function(fn, annotation,
                                annotatorpolicy=annotatorpolicy,
                                nowrap=True)

    def cast(self, gv, nb_args):
        "NOT_RPYTHON"
        def fn(*args):
            return gv.obj.Invoke(*args)
        return fn

    def directtesthelper(self, FUNCTYPE, func):
        py.test.skip('???')

