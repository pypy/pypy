import py
from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.jit.codewriter import heaptracker
from rpython.jit.backend.test.runner_test import LLtypeBackendTest
from rpython.jit.backend.llgraph.runner import LLGraphCPU

class TestLLTypeLLGraph(LLtypeBackendTest):
    # for individual tests see:
    # ====> ../../test/runner_test.py


    def get_cpu(self):
        return LLGraphCPU(None)

    def test_memoryerror(self):
        py.test.skip("does not make much sense on the llgraph backend")

    def test_call_release_gil_variable_function_and_arguments(self):
        py.test.skip("the arguments seem not correctly casted")


def test_cast_adr_to_int_and_back():
    X = lltype.Struct('X', ('foo', lltype.Signed))
    x = lltype.malloc(X, immortal=True)
    x.foo = 42
    a = llmemory.cast_ptr_to_adr(x)
    i = heaptracker.adr2int(a)
    assert lltype.typeOf(i) is lltype.Signed
    a2 = heaptracker.int2adr(i)
    assert llmemory.cast_adr_to_ptr(a2, lltype.Ptr(X)) == x
    assert heaptracker.adr2int(llmemory.NULL) == 0
    assert heaptracker.int2adr(0) == llmemory.NULL
