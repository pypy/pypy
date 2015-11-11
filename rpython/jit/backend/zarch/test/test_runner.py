from rpython.jit.backend.test.runner_test import LLtypeBackendTest
from rpython.jit.backend.zarch.runner import CPU_S390_64
from rpython.jit.tool.oparser import parse
from rpython.jit.metainterp.history import (AbstractFailDescr,
                                            AbstractDescr,
                                            BasicFailDescr, BasicFinalDescr,
                                            JitCellToken, TargetToken,
                                            ConstInt, ConstPtr,
                                            Const, ConstFloat)
from rpython.jit.metainterp.resoperation import InputArgInt, InputArgFloat
from rpython.rtyper.lltypesystem import lltype
from rpython.jit.metainterp.resoperation import ResOperation, rop
import py

class FakeStats(object):
    pass

class TestZARCH(LLtypeBackendTest):
    # for the individual tests see
    # ====> ../../test/runner_test.py

    def get_cpu(self):
        cpu = CPU_S390_64(rtyper=None, stats=FakeStats())
        cpu.setup_once()
        return cpu

    @py.test.parametrize('input,opcode,result',
        [30,'i1 = int_mul(i0, 2)',60]
    )
    def test_int_arithmetic_and_logic(self, input, opcode, result):
        loop = parse("""
        [i0]
        {opcode}
        finish(i1, descr=faildescr)
        """.format(opcode=opcode),namespace={"faildescr": BasicFinalDescr(1)})
        looptoken = JitCellToken()
        self.cpu.compile_loop(loop.inputargs, loop.operations, looptoken)
        deadframe = self.cpu.execute_token(looptoken, input)
        fail = self.cpu.get_latest_descr(deadframe)
        res = self.cpu.get_int_value(deadframe, 0)
        assert res == result
        assert fail.identifier == 1 
