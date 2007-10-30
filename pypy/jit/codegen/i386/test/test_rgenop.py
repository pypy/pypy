import py
from pypy.rpython.lltypesystem import lltype
from pypy.jit.codegen.i386.rgenop import RI386GenOp
from pypy.jit.codegen.test.rgenop_tests import AbstractRGenOpTests

class TestRI386Genop(AbstractRGenOpTests):
    RGenOp = RI386GenOp
    from pypy.jit.codegen.i386.test.test_operation import RGenOpPacked

    # for the individual tests see
    # ====> ../../test/rgenop_tests.py
