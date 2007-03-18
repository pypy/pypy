import py
from pypy.jit.codegen.dump.rgenop import RDumpGenOp
from pypy.rpython.lltypesystem import lltype
from pypy.jit.codegen.test.rgenop_tests import AbstractRGenOpTests, FUNC, FUNC2
from ctypes import cast, c_int, c_void_p, CFUNCTYPE

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


class Whatever(object):
    def __eq__(self, other):
        return True
    def __ne__(self, other):
        return False
