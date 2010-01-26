import py
from pypy.rpython.lltypesystem import lltype, llmemory, rstr, rclass
from pypy.rpython.test.test_llinterp import interpret
from pypy.rlib.unroll import unrolling_iterable

from pypy.jit.metainterp.history import BoxInt, BoxPtr, Const, ConstInt,\
     TreeLoop
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.metainterp.executor import execute
from pypy.jit.backend.test.runner_test import LLtypeBackendTest

class TestLLTypeLLGraph(LLtypeBackendTest):
    # for individual tests see:
    # ====> ../../test/runner_test.py
    
    from pypy.jit.backend.llgraph.runner import LLtypeCPU as cpu_type

    def setup_method(self, _):
        self.cpu = self.cpu_type(None)

    def test_cast_adr_to_int_and_back(self):
        cpu = self.cpu
        X = lltype.Struct('X', ('foo', lltype.Signed))
        x = lltype.malloc(X, immortal=True)
        x.foo = 42
        a = llmemory.cast_ptr_to_adr(x)
        i = cpu.cast_adr_to_int(a)
        assert isinstance(i, int)
        a2 = cpu.cast_int_to_adr(i)
        assert llmemory.cast_adr_to_ptr(a2, lltype.Ptr(X)) == x
        assert cpu.cast_adr_to_int(llmemory.NULL) == 0
        assert cpu.cast_int_to_adr(0) == llmemory.NULL


## these tests never worked
## class TestOOTypeLLGraph(LLGraphTest):
##     from pypy.jit.backend.llgraph.runner import OOtypeCPU as cpu_type

def test_fielddescr_ootype():
    from pypy.rpython.ootypesystem import ootype
    from pypy.jit.backend.llgraph.runner import OOtypeCPU
    A = ootype.Instance("A", ootype.ROOT, {"foo": ootype.Signed})
    B = ootype.Instance("B", A)
    cpu = OOtypeCPU(None)
    descr1 = cpu.fielddescrof(A, "foo")
    descr2 = cpu.fielddescrof(B, "foo")
    assert descr1 is descr2
