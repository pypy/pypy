import py
from pypy.jit.codegen.llvm.rgenop import RLLVMGenOp
from pypy.jit.codegen.llvm.llvmjit import llvm_version, MINIMAL_VERSION
from pypy.jit.codegen.test.rgenop_tests import AbstractRGenOpTests
from sys import platform


class TestRLLVMGenop(AbstractRGenOpTests):
    RGenOp = RLLVMGenOp

    if platform == 'darwin':
        def compile(self, runner, argtypes):
            py.test.skip('Compilation for Darwin not fully support yet (static/dyn lib issue')

    def skip(self):
        py.test.skip('WIP')

    def skip_too_minimal(self):
        py.test.skip('found llvm %.1f, requires at least llvm %.1f(cvs)' % (
            llvm_version(), MINIMAL_VERSION))

    if llvm_version() < 2.0:
        test_goto_direct = skip_too_minimal #segfault
        test_goto_compile = skip_too_minimal #segfault
        test_fact_direct = skip_too_minimal #segfault
        test_fact_compile= skip_too_minimal #segfault
        test_tight_loop = skip_too_minimal #llvm 1.9 assertion failure
        test_from_random_2_direct = skip_too_minimal #segfault
        test_from_random_3_direct = skip_too_minimal #segfault
        test_from_random_4_direct = skip_too_minimal #segfault

    test_read_frame_var_direct   = skip
    test_read_frame_var_compile  = skip
    test_write_frame_place_direct  = skip
    test_write_frame_place_compile = skip
    test_read_frame_place_direct  = skip
    test_read_frame_place_compile = skip
