import py
import os
from pypy.jit.metainterp.history import (AbstractFailDescr,
                                         AbstractDescr,
                                         BasicFailDescr,
                                         BoxInt, Box, BoxPtr,
                                         LoopToken,
                                         ConstInt, ConstPtr,
                                         BoxObj, Const,
                                         ConstObj, BoxFloat, ConstFloat)
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.rpython.test.test_llinterp import interpret
from pypy.jit.backend.detect_cpu import getcpuclass
from pypy.jit.backend.arm.runner import ArmCPU
from pypy.tool.udir import udir
from pypy.jit.backend.arm.test.support import skip_unless_arm
skip_unless_arm()

class FakeStats(object):
    pass
cpu = getcpuclass()(rtyper=None, stats=FakeStats(), translate_support_code=True)
class TestBackendTranslation(object):
    def test_compile_bridge(self):
        def loop():
            i0 = BoxInt()
            i1 = BoxInt()
            i2 = BoxInt()
            faildescr1 = BasicFailDescr(1)
            faildescr2 = BasicFailDescr(2)
            looptoken = LoopToken()
            operations = [
                ResOperation(rop.INT_ADD, [i0, ConstInt(1)], i1),
                ResOperation(rop.INT_LE, [i1, ConstInt(9)], i2),
                ResOperation(rop.GUARD_TRUE, [i2], None, descr=faildescr1),
                ResOperation(rop.JUMP, [i1], None, descr=looptoken),
                ]
            inputargs = [i0]
            operations[2].setfailargs([i1])
            cpu.setup_once()
            cpu.compile_loop(inputargs, operations, looptoken)

            i1b = BoxInt()
            i3 = BoxInt()
            bridge = [
                ResOperation(rop.INT_LE, [i1b, ConstInt(19)], i3),
                ResOperation(rop.GUARD_TRUE, [i3], None, descr=faildescr2),
                ResOperation(rop.JUMP, [i1b], None, descr=looptoken),
            ]
            bridge[1].setfailargs([i1b])
            assert looptoken._arm_bootstrap_code != 0
            assert looptoken._arm_loop_code != 0
            cpu.compile_bridge(faildescr1, [i1b], bridge, looptoken, True)

            cpu.set_future_value_int(0, 2)
            fail = cpu.execute_token(looptoken)
            res = cpu.get_latest_value_int(0)
            return fail.identifier * 1000 + res

        logfile = udir.join('test_ztranslation.log')
        os.environ['PYPYLOG'] = 'jit-log-opt:%s' % (logfile,)
        res = interpret(loop, [], insist=True)
        assert res == 2020

