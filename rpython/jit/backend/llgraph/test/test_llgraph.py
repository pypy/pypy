import sys
import py
from rpython.jit.backend.test.runner_test import LLtypeBackendTest
from rpython.jit.backend.llgraph.runner import LLGraphCPU

IS_32_BIT = sys.maxint < 2**32

class TestLLTypeLLGraph(LLtypeBackendTest):
    # for individual tests see:
    # ====> ../../test/runner_test.py


    def get_cpu(self):
        return LLGraphCPU(None)

    def test_memoryerror(self):
        py.test.skip("does not make much sense on the llgraph backend")

    def test_call_release_gil_variable_function_and_arguments(self):
        py.test.skip("the arguments seem not correctly casted")

    def test_passing_guard_gc_type_array(self):
        if IS_32_BIT:
            py.test.skip("TypeIDSymbolic identity is flaky on 32-bit, "
                         "not worth chasing further")
        LLtypeBackendTest.test_passing_guard_gc_type_array(self)
