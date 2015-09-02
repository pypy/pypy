from rpython.jit.backend.test.runner_test import LLtypeBackendTest
from rpython.jit.backend.ppc.runner import PPC_CPU
from rpython.jit.tool.oparser import parse
from rpython.jit.metainterp.history import (AbstractFailDescr,
                                            AbstractDescr,
                                            BasicFailDescr,
                                            BoxInt, Box, BoxPtr,
                                            JitCellToken, TargetToken,
                                            ConstInt, ConstPtr,
                                            Const,
                                            BoxFloat, ConstFloat)
from rpython.rtyper.lltypesystem import lltype
from rpython.jit.metainterp.resoperation import ResOperation, rop
from rpython.jit.backend.ppc.arch import IS_PPC_32
import py

class FakeStats(object):
    pass

class TestPPC(LLtypeBackendTest):

    # for the individual tests see
    # ====> ../../test/runner_test.py

    if IS_PPC_32:
        add_loop_instructions = ["mr", "add", "cmpwi", "beq", "b"]
    else:
        add_loop_instructions = ["mr", "add", "cmpdi", "beq", "b"]
    bridge_loop_instructions_short = ["lis", "ori", "mtctr", "bctr"]
    bridge_loop_instructions_long = ["lis", "ori", "rldicr", "oris", "ori",
                                     "mtctr", "bctr"]
   
    def setup_method(self, meth):
        self.cpu = PPC_CPU(rtyper=None, stats=FakeStats())
        self.cpu.setup_once()

    def test_compile_loop_many_int_args(self):
        for numargs in range(2, 16):
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
            self.cpu.compile_loop(loop.inputargs, loop.operations, looptoken)
            ARGS = [lltype.Signed] * numargs
            RES = lltype.Signed
            args = [i+1 for i in range(numargs)]
            deadframe = self.cpu.execute_token(looptoken, *args)
            assert self.cpu.get_int_value(deadframe, 0) == sum(args)
  
    def test_return_spilled_args(self):
        numargs = 50
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
        self.cpu.compile_loop(loop.inputargs, loop.operations, looptoken)
        ARGS = [lltype.Signed] * numargs
        RES = lltype.Signed
        args = [i+1 for i in range(numargs)]
        deadframe = self.cpu.execute_token(looptoken, *args)
        fail = self.cpu.get_latest_descr(deadframe)
        assert fail is faildescr
        for i in range(numargs):
            assert self.cpu.get_int_value(deadframe, i) == i + 1

        bridgeops = [arglist]
        bridgeops.append("guard_value(i1, -5) %s" % arglist)
        bridgeops = "".join(bridgeops)
        bridge = parse(bridgeops)
        faildescr2 = bridge.operations[-1].getdescr()

        self.cpu.compile_bridge(faildescr, bridge.inputargs, bridge.operations, looptoken)
        deadframe = self.cpu.execute_token(looptoken, *args)
        fail = self.cpu.get_latest_descr(deadframe)
        assert fail is faildescr2
        for i in range(numargs):
            assert self.cpu.get_int_value(deadframe, i) == i + 1

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

    def test_debugger_on(self):
        py.test.skip("XXX")
        from pypy.rlib import debug

        targettoken, preambletoken = TargetToken(), TargetToken()
        loop = """
        [i0]
        label(i0, descr=preambletoken)
        debug_merge_point('xyz', 0)
        i1 = int_add(i0, 1)
        i2 = int_ge(i1, 10)
        guard_false(i2) []
        label(i1, descr=targettoken)
        debug_merge_point('xyz', 0)
        i11 = int_add(i1, 1)
        i12 = int_ge(i11, 10)
        guard_false(i12) []
        jump(i11, descr=targettoken)
        """
        ops = parse(loop, namespace={'targettoken': targettoken,
                                     'preambletoken': preambletoken})
        debug._log = dlog = debug.DebugLog()
        try:
            self.cpu.assembler.set_debug(True)
            looptoken = JitCellToken()
            self.cpu.compile_loop(ops.inputargs, ops.operations, looptoken)
            self.cpu.execute_token(looptoken, 0)
            # check debugging info
            struct = self.cpu.assembler.loop_run_counters[0]
            assert struct.i == 1
            struct = self.cpu.assembler.loop_run_counters[1]
            assert struct.i == 1
            struct = self.cpu.assembler.loop_run_counters[2]
            assert struct.i == 9
            self.cpu.finish_once()
        finally:
            debug._log = None
        l0 = ('debug_print', 'entry -1:1')
        l1 = ('debug_print', preambletoken.repr_of_descr() + ':1')
        l2 = ('debug_print', targettoken.repr_of_descr() + ':9')
        assert ('jit-backend-counts', [l0, l1, l2]) in dlog

    def test_compile_more_than_32k(self):
        # the guard_true needs a "b.cond" jumping forward more than 32 kb
        i0 = BoxInt()
        i1 = BoxInt()
        looptoken = JitCellToken()
        targettoken = TargetToken()
        operations = [
            ResOperation(rop.LABEL, [i0], None, descr=targettoken),
            ResOperation(rop.INT_LE, [i0, ConstInt(9)], i1),
            ResOperation(rop.GUARD_TRUE, [i1], None, descr=BasicFailDescr(5)),
            ]
        operations[2].setfailargs([i0])
        inputargs = [i0]
        NUM = 8193
        for i in range(NUM):
            i2 = BoxInt()
            operations.append(
                ResOperation(rop.INT_ADD, [i0, ConstInt(1)], i2))
            i0 = i2
        operations.append(
            ResOperation(rop.JUMP, [i0], None, descr=targettoken))

        self.cpu.compile_loop(inputargs, operations, looptoken)
        deadframe = self.cpu.execute_token(looptoken, -42)
        fail = self.cpu.get_latest_descr(deadframe)
        assert fail.identifier == 5
        res = self.cpu.get_int_value(deadframe, 0)
        assert res == -42 + NUM

    def test_call_many_float_args(self):
        from rpython.rtyper.annlowlevel import llhelper
        from rpython.jit.codewriter.effectinfo import EffectInfo

        seen = []
        def func(*args):
            seen.append(args)
            return -42

        F = lltype.Float
        I = lltype.Signed
        FUNC = self.FuncType([F] * 7 + [I] + [F] * 7 + [I] + [F], I)
        FPTR = self.Ptr(FUNC)
        func_ptr = llhelper(FPTR, func)
        cpu = self.cpu
        calldescr = cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT,
                                    EffectInfo.MOST_GENERAL)
        funcbox = self.get_funcbox(cpu, func_ptr)
        argvals = [.1 * i for i in range(15)]
        argvals.insert(7, 77)
        argvals.insert(15, 1515)
        argvals = tuple(argvals)
        argboxes = []
        for x in argvals:
            if isinstance(x, float):
                argboxes.append(BoxFloat(x))
            else:
                argboxes.append(BoxInt(x))
        res = self.execute_operation(rop.CALL,
                                     [funcbox] + argboxes,
                                     'int', descr=calldescr)
        assert res.value == -42
        assert seen == [argvals]
