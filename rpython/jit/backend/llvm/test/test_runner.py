from rpython.jit.backend.test.runner_test import LLtypeBackendTest
from rpython.jit.backend.llvm.runner import LLVM_CPU
from rpython.jit.tool.oparser import parse
from rpython.jit.metainterp.history import JitCellToken, BasicFinalDescr

class FakeStats(object):
    pass

class TestLLVM(LLtypeBackendTest):
    def get_cpu(self):
        cpu = LLVM_CPU(rtyper=None, stats=FakeStats())
        cpu.setup_once()
        return cpu

    #def test_compile_linear_loop(self):
    #    loop = parse("""
    #    [i0]
    #    i1 = int_add(i0, 1)
    #    finish(i1, descr=faildescr)
    #    """, namespace={"faildescr": BasicFinalDescr(1)})
    #    looptoken = JitCellToken()
    #    self.cpu.compile_loop(loop.inputargs, loop.operations, looptoken)
    #    deadframe = self.cpu.execute_token(looptoken, 2)
    #    fail = self.cpu.get_latest_descr(deadframe)
    #    res = self.cpu.get_int_value(deadframe, 0)
    #    assert res == 3
    #    assert fail.identifier == 1
