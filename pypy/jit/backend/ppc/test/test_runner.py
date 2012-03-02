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
from pypy.jit.metainterp.resoperation import ResOperation, rop
import py

class FakeStats(object):
    pass

class TestPPC(LLtypeBackendTest):
   
    def setup_method(self, meth):
        self.cpu = PPC_64_CPU(rtyper=None, stats=FakeStats())
        self.cpu.setup_once()

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
  
    def test_return_spilled_args(self):
        numargs = 50
        for _ in range(numargs):
            self.cpu.reserve_some_free_fail_descr_number()
        ops = []
        arglist = "[%s]\n" % ", ".join(["i%d" % i for i in range(numargs)])
        ops.append(arglist)
        
        # spill every inputarg
        for i in range(numargs):
            ops.append("force_spill(i%d)\n" % i)
        ops.append("guard_value(i0, -1) %s" % arglist)
        ops = "".join(ops)
        loop = parse(ops)
        looptoken = JitCellToken()
        faildescr = loop.operations[-1].getdescr()
        done_number = self.cpu.get_fail_descr_number(faildescr)
        self.cpu.compile_loop(loop.inputargs, loop.operations, looptoken)
        ARGS = [lltype.Signed] * numargs
        RES = lltype.Signed
        args = [i+1 for i in range(numargs)]
        res = self.cpu.execute_token(looptoken, *args)
        assert res is faildescr
        for i in range(numargs):
            assert self.cpu.get_latest_value_int(i) == i + 1

        bridgeops = [arglist]
        bridgeops.append("guard_value(i1, -5) %s" % arglist)
        bridgeops = "".join(bridgeops)
        bridge = parse(bridgeops)
        faildescr2 = bridge.operations[-1].getdescr()

        self.cpu.compile_bridge(faildescr, bridge.inputargs, bridge.operations, looptoken)
        res2 = self.cpu.execute_token(looptoken, *args)
        assert res2 is faildescr2
        for i in range(numargs):
            assert self.cpu.get_latest_value_int(i) == i + 1

    def test_unicodesetitem_really_needs_temploc(self):
        u_box = self.alloc_unicode(u"abcdsdasdsaddefg")
        
        i0 = BoxInt()
        i1 = BoxInt()
        i2 = BoxInt()
        i3 = BoxInt()
        i4 = BoxInt()
        i5 = BoxInt()
        i6 = BoxInt()
        i7 = BoxInt()
        i8 = BoxInt()
        i9 = BoxInt()
        p10 = BoxPtr()

        inputargs = [i0,i1,i2,i3,i4,i5,i6,i7,i8,i9,p10]
        looptoken = JitCellToken()
        targettoken = TargetToken()
        faildescr = BasicFailDescr(1)

        operations = [
            ResOperation(rop.LABEL, inputargs, None, descr=targettoken),
            ResOperation(rop.UNICODESETITEM, 
                         [p10, i6, ConstInt(123)], None),
            ResOperation(rop.FINISH, inputargs, None, descr=faildescr)
            ]

        args = [(i + 1) for i in range(10)] + [u_box.getref_base()]
        self.cpu.compile_loop(inputargs, operations, looptoken)
        fail = self.cpu.execute_token(looptoken, *args)
        assert fail.identifier == 1
        for i in range(10):
            assert self.cpu.get_latest_value_int(i) == args[i]
