from pypy.jit.backend.arm.runner import ArmCPU
from pypy.jit.backend.test.runner_test import LLtypeBackendTest
from pypy.jit.backend.arm.test.support import skip_unless_arm
from pypy.jit.metainterp.history import (AbstractFailDescr,
                                         AbstractDescr,
                                         BasicFailDescr,
                                         BoxInt, Box, BoxPtr,
                                         LoopToken,
                                         ConstInt, ConstPtr,
                                         BoxObj, Const,
                                         ConstObj, BoxFloat, ConstFloat)
from pypy.jit.metainterp.resoperation import ResOperation, rop

skip_unless_arm()

class FakeStats(object):
    pass

class TestARM(LLtypeBackendTest):

    # for the individual tests see
    # ====> ../../test/runner_test.py

    def setup_method(self, meth):
        self.cpu = ArmCPU(rtyper=None, stats=FakeStats())

    def test_result_is_spilled(self):
        cpu = self.cpu
        inp = [BoxInt(i) for i in range(1, 15)]
        out = list(inp)
        out.reverse()
        looptoken = LoopToken()
        operations = [
            ResOperation(rop.INT_ADD, [inp[0], inp[1]], inp[2]),
            ResOperation(rop.INT_SUB, [inp[1], ConstInt(1)], inp[4]),
            ResOperation(rop.INT_ADD, [inp[4], ConstInt(0)], inp[3]),
            ResOperation(rop.INT_ADD, [inp[5], inp[6]], inp[7]),
            ResOperation(rop.INT_SUB, [inp[8], ConstInt(1)], inp[9]),
            ResOperation(rop.INT_ADD, [inp[10], ConstInt(1)], inp[3]),
            ResOperation(rop.INT_ADD, [inp[11], inp[12]], inp[13]),
            ResOperation(rop.FINISH, out, None, descr=BasicFailDescr(1)),
            ]
        cpu.compile_loop(inp, operations, looptoken)
        for i in range(1, 15):
            self.cpu.set_future_value_int(i-1, i)
        res = self.cpu.execute_token(looptoken)
        output = [self.cpu.get_latest_value_int(i-1) for i in range(1, 15)]
        expected = [25,13,12,11,8,9,13,7,6,1,12,3,2,1]
        assert output == expected
