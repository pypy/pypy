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
        out = [BoxInt(i) for i in range(1, 15)]
        #out.reverse()
        looptoken = LoopToken()
        operations = [
            ResOperation(rop.INT_ADD, [inp[0] , inp[1]], out[0]),
            ResOperation(rop.INT_ADD, [inp[2] , inp[3]], out[1]),
            ResOperation(rop.INT_ADD, [inp[4] , inp[5]], out[2]),
            ResOperation(rop.INT_ADD, [inp[6] , inp[7]], out[3]),
            ResOperation(rop.INT_ADD, [inp[8] , inp[9]], out[4]),
            ResOperation(rop.INT_ADD, [inp[10], inp[11]], out[5]),
            ResOperation(rop.INT_ADD, [inp[12], inp[13]], out[6]),
            ResOperation(rop.INT_ADD, [inp[0] , inp[1]], out[7]),
            ResOperation(rop.INT_ADD, [inp[2] , inp[3]], out[8]),
            ResOperation(rop.INT_ADD, [inp[4] , inp[5]], out[9]),
            ResOperation(rop.INT_ADD, [inp[6] , inp[7]], out[10]),
            ResOperation(rop.INT_ADD, [inp[8] , inp[9]], out[11]),
            ResOperation(rop.INT_ADD, [inp[10], inp[11]], out[12]),
            ResOperation(rop.INT_ADD, [inp[12], inp[13]], out[13]),
            ResOperation(rop.FINISH, out, None, descr=BasicFailDescr(1)),
            ]
        cpu.compile_loop(inp, operations, looptoken)
        for i in range(1, 15):
            self.cpu.set_future_value_int(i-1, i)
        res = self.cpu.execute_token(looptoken)
        output = [self.cpu.get_latest_value_int(i-1) for i in range(1, 15)]
        expected = [3, 7, 11, 15, 19, 23, 27, 3, 7, 11, 15, 19, 23, 27]
        assert output == expected
