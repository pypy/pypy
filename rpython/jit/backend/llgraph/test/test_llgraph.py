import py
from rpython.rtyper.lltypesystem import lltype, llmemory, rstr, rclass
from rpython.rtyper.test.test_llinterp import interpret
from rpython.rlib.unroll import unrolling_iterable

from rpython.jit.metainterp.history import BoxInt, BoxPtr, Const, ConstInt,\
     TreeLoop
from rpython.jit.metainterp.resoperation import ResOperation, rop
from rpython.jit.metainterp.executor import execute
from rpython.jit.codewriter import heaptracker
from rpython.jit.backend.test.runner_test import LLtypeBackendTest

class TestLLTypeLLGraph(LLtypeBackendTest):
    # for individual tests see:
    # ====> ../../test/runner_test.py
    
    from rpython.jit.backend.llgraph.runner import LLGraphCPU as cpu_type

    def setup_method(self, _):
        self.cpu = self.cpu_type(None)

    def test_memoryerror(self):
        py.test.skip("does not make much sense on the llgraph backend")


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

## these tests never worked
## class TestOOTypeLLGraph(LLGraphTest):
##     from rpython.jit.backend.llgraph.runner import OOtypeCPU as cpu_type

def test_fielddescr_ootype():
    py.test.skip("ootype tests skipped")
    from rpython.rtyper.ootypesystem import ootype
    from rpython.jit.backend.llgraph.runner import OOtypeCPU
    A = ootype.Instance("A", ootype.ROOT, {"foo": ootype.Signed})
    B = ootype.Instance("B", A)
    cpu = OOtypeCPU(None)
    descr1 = cpu.fielddescrof(A, "foo")
    descr2 = cpu.fielddescrof(B, "foo")
    assert descr1 is descr2
