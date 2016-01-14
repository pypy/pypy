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

    def test_multiple_arguments(self):
        from rpython.rtyper.annlowlevel import llhelper
        from rpython.jit.metainterp.typesystem import deref
        from rpython.rlib.jit_libffi import types
        from rpython.jit.codewriter.effectinfo import EffectInfo
        from rpython.rlib.rarithmetic import intmask

        def func_int(a, b, c, d, e, f):
            sum = intmask(a) + intmask(b) + intmask(c) + intmask(d) + intmask(e) + intmask(f)
            return sum

        functions = [
            (func_int, lltype.Signed, types.sint, 655360, 655360),
            (func_int, lltype.Signed, types.sint, 655360, -293999429),
            ]

        cpu = self.cpu
        for func, TP, ffi_type, num, num1 in functions:
            #
            FPTR = self.Ptr(self.FuncType([TP] * 6, TP))
            func_ptr = llhelper(FPTR, func)
            FUNC = deref(FPTR)
            funcbox = self.get_funcbox(cpu, func_ptr)
            # first, try it with the "normal" calldescr
            calldescr = cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
                                        EffectInfo.MOST_GENERAL)
            iargs = [0x7fffFFFFffffFFFF,1,0,0,0,0]
            args = [InputArgInt(num) for num in iargs]
            res = self.execute_operation(rop.CALL_I,
                                         [funcbox] + args,
                                         'int', descr=calldescr)
            assert res == sum(iargs)
