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

    add_loop_instructions = "lg; lgr; larl; agr; cgfi; je; j;$"
    # realloc frame takes the most space (from just after larl, to lay)
    bridge_loop_instructions = "larl; lg; cgfi; je; lghi; stg; " \
                               "lay; lgfi;( iihf;)? lgfi;( iihf;)? basr; lay; lg; br;$"
