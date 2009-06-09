import py
from pypy.jit.metainterp.test.test_basic import BasicTests
from pypy.jit.backend.test.support import CCompiledMixin
from pypy.jit.backend.llvm.runner import LLVMCPU


class JitLLVMMixin(CCompiledMixin):
    CPUClass = LLVMCPU

class TestZRPyBasic(JitLLVMMixin, BasicTests):
    def setup_class(cls):
        py.test.skip("in-progress")

