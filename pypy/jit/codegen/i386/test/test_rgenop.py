from pypy.jit.codegen.i386.rgenop import RI386GenOp
from pypy.jit.codegen.test.rgenop_tests import AbstractRGenOpTests

class TestRI386Genop(AbstractRGenOpTests):
    RGenOp = RI386GenOp

    # for the individual tests see
    # ====> ../../test/rgenop_tests.py
