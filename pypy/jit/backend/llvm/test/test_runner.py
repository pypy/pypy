import py
from pypy.jit.backend.llvm.runner import LLVMCPU
from pypy.jit.backend.test.runner_test import LLtypeBackendTest


class TestLLVM(LLtypeBackendTest):

    # for the individual tests see
    # ====> ../../test/runner_test.py

    def setup_class(cls):
        cls.cpu = LLVMCPU(None)
        cls.cpu.setup_once()

    def _skip(self):
        py.test.skip("in-progress")

    test_do_call = _skip
    test_executor = _skip
    test_passing_guard_class = _skip
    test_failing_guard_class = _skip
    test_casts = _skip
    test_ooops_non_gc = _skip
