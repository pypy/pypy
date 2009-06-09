import py
from pypy.jit.backend.llvm.runner import LLVMCPU
from pypy.jit.backend.test.runner_test import LLtypeBackendTest


class TestLLVM(LLtypeBackendTest):

    # for the individual tests see
    # ====> ../../test/runner_test.py

    def setup_class(cls):
        cls.cpu = LLVMCPU(None)
        cls.cpu.setup_once()
