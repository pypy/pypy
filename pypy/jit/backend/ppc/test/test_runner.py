from pypy.jit.backend.test.runner_test import LLtypeBackendTest
from pypy.jit.backend.ppc.runner import PPC_64_CPU
from pypy.jit.tool.oparser import parse
from pypy.jit.metainterp.history import (AbstractFailDescr,
                                         AbstractDescr,
                                         BasicFailDescr,
                                         BoxInt, Box, BoxPtr,
                                         JitCellToken, TargetToken,
                                         ConstInt, ConstPtr,
                                         BoxObj, Const,
                                         ConstObj, BoxFloat, ConstFloat)
from pypy.rpython.lltypesystem import lltype, llmemory, rstr, rffi, rclass
from pypy.jit.codewriter.effectinfo import EffectInfo
import py

class FakeStats(object):
    pass

class TestPPC(LLtypeBackendTest):
   
    def setup_class(cls):
        cls.cpu = PPC_64_CPU(rtyper=None, stats=FakeStats())
        cls.cpu.setup_once()

    def test_cond_call_gc_wb_array_card_marking_fast_path(self):
        py.test.skip("unsure what to do here")

    def test_compile_loop_many_int_args(self):
        for numargs in range(2, 16):
            for _ in range(numargs):
                self.cpu.reserve_some_free_fail_descr_number()
            ops = []
            arglist = "[%s]\n" % ", ".join(["i%d" % i for i in range(numargs)])
            ops.append(arglist)
            
            arg1 = 0
            arg2 = 1
            res = numargs
            for i in range(numargs - 1):
                op = "i%d = int_add(i%d, i%d)\n" % (res, arg1, arg2)
                arg1 = res
                res += 1
                arg2 += 1
                ops.append(op)
            ops.append("finish(i%d)" % (res - 1))

            ops = "".join(ops)
            loop = parse(ops)
            looptoken = JitCellToken()
            done_number = self.cpu.get_fail_descr_number(loop.operations[-1].getdescr())
            self.cpu.compile_loop(loop.inputargs, loop.operations, looptoken)
            ARGS = [lltype.Signed] * numargs
            RES = lltype.Signed
            args = [i+1 for i in range(numargs)]
            res = self.cpu.execute_token(looptoken, *args)
            assert self.cpu.get_latest_value_int(0) == sum(args)
        
