import py
from pypy.jit.codegen.dump.rgenop import RDumpGenOp
from pypy.jit.timeshifter.test.test_timeshift import Whatever
from pypy.rpython.lltypesystem import lltype
from pypy.jit.codegen.test.rgenop_tests import AbstractRGenOpTests

class TestRDumpGenop(AbstractRGenOpTests):
    RGenOp = RDumpGenOp

    def cast(self, gv, nb_args):
        def dummyfn(*whatever):
            return Whatever()
        return dummyfn

    def compile(self, runner, argtypes):
        py.test.skip("cannot compile tests for now")

    # for the individual tests see
    # ====> ../../test/rgenop_tests.py
