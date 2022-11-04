import py
import sys
import re
import pytest

from rpython.rlib.rarithmetic import intmask
from rpython.rlib.rarithmetic import LONG_BIT
from rpython.rlib.rjitlog import rjitlog as jl
from rpython.rtyper import rclass
from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.rtyper.annlowlevel import llhelper
from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.jit.backend.llgraph import runner
from rpython.jit.metainterp.jitprof import EmptyProfiler
from rpython.jit.metainterp.optimize import InvalidLoop
from rpython.jit.metainterp.history import (
    JitCellToken, TargetToken, BasicFinalDescr, BasicFailDescr, ConstInt, INT, Stats, get_const_ptr_for_string)
from rpython.jit.metainterp import compile, executor, pyjitpl, history
from rpython.jit.metainterp.resoperation import (
    rop, ResOperation, InputArgInt, OpHelpers, InputArgRef)
from rpython.jit.metainterp.support import ptr2int
from rpython.jit.metainterp.optimizeopt.intdiv import magic_numbers
from rpython.jit.metainterp.optimizeopt.tracesplit import OptTraceSplit, mark
from rpython.jit.metainterp.test.test_resume import (
    ResumeDataFakeReader, MyMetaInterp)
from rpython.jit.metainterp.optimizeopt.test import test_util, test_dependency
from rpython.jit.metainterp.optimizeopt.test.test_util import (
    BaseTest, FakeDescr, convert_old_style_to_targets)
from rpython.jit.tool.oparser import parse, convert_loop_to_trace

from pprint import pprint

class FakeCPU(object):
    supports_guard_gc_type = True

    class Storage:
        pass

    class tracker:
        pass

    def __init__(self):
        self.seen = []

    def calldescrof(self, FUNC, ARGS, RESULT, effect_info):
        from rpython.jit.backend.llgraph.runner import CallDescr
        return CallDescr(RESULT, ARGS, effect_info)

    def compile_loop(self, inputargs, operations, token, jd_id=0,
                     unique_id=0, log=True, name='',
                     logger=None):
        token.compiled_loop_token = self.Storage()
        self.seen.append((inputargs, operations, token))

    def compile_bridge(self, faildescr, inputargs, operations,
                       original_loop_token, log=True, logger=None):
        original_loop_token.compiled_loop_token = self.Storage()
        self.seen.append((inputargs, operations, original_loop_token))

# ____________________________________________________________


def merge_dicts(*dict_args):
    """
    Given any number of dictionaries, shallow copy and merge into a new dict,
    precedence goes to key-value pairs in latter dictionaries.
    """
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result

class FakeMetaInterpStaticData(object):
    all_descrs = []
    done_with_this_frame_descr_ref = compile.DoneWithThisFrameDescrRef()

    def __init__(self, cpu):
        self.cpu = cpu
        self.stats = Stats(None)
        self.profiler = EmptyProfiler()
        self.options = test_util.Fake()
        self.globaldata = test_util.Fake()
        self.config = test_util.get_combined_translation_config(translating=True)
        self.jitlog = jl.JitLogger()
        self.callinfocollection = test_util.FakeCallInfoCollection()

    class logger_noopt:
        @classmethod
        def log_loop(*args, **kwds):
            pass

        @classmethod
        def log_loop_from_trace(*args, **kwds):
            pass

    class logger_ops:
        repr_of_resop = repr

    class warmrunnerdesc:
        class memory_manager:
            retrace_limit = 5
            max_retrace_guards = 15
        jitcounter = test_util.DeterministicJitCounter()

class FakeMetaInterp(object):
    cpu = FakeCPU()
    staticdata = FakeMetaInterpStaticData(cpu)

class FakeJitDriver(object):
    conditions = ["is_true"]

class FakeJitDriverSD(test_util.FakeJitDriverStaticData):
    result_type = history.REF
    index = 0
    jitdriver = FakeJitDriver()
    num_green_args = 3
    num_red_args = 1

class BaseTestTraceSplit(test_dependency.DependencyBaseTest):

    enable_opts = "intbounds:rewrite:string:earlyforce:pure:heap"

    cpu = runner.LLGraphCPU(None)
    Ptr = lltype.Ptr
    FuncType = lltype.FuncType
    FPTR = Ptr(FuncType([lltype.Char], lltype.Char))

    def pop(x, y):
        return x

    FPTR = Ptr(FuncType([lltype.Signed,], lltype.Signed))
    pop = llhelper(FPTR, pop)
    popdescr = cpu.calldescrof(FPTR.TO, (lltype.Signed,), lltype.Signed,
                               EffectInfo.MOST_GENERAL)
    def emit_jump(x, y):
        return x
    FPTR2 = Ptr(FuncType([lltype.Signed, lltype.Signed, lltype.Signed], lltype.Signed))
    emit_jump_ptr = llhelper(FPTR2, emit_jump)
    emit_jump_descr = cpu.calldescrof(FPTR2.TO, (lltype.Signed, lltype.Signed), lltype.Signed,
                                         EffectInfo.MOST_GENERAL)

    def emit_ret(x, y):
        return x
    FPTR3 = Ptr(FuncType([lltype.Signed, lltype.Signed, lltype.Signed], lltype.Signed))
    emit_ret_ptr = llhelper(FPTR3, emit_ret)
    emit_ret_descr = cpu.calldescrof(FPTR3.TO, (lltype.Signed, lltype.Signed), lltype.Signed,
                                     EffectInfo.MOST_GENERAL)


    def func(x):
        return x
    FPTR = Ptr(FuncType([lltype.Signed], lltype.Signed))
    func_ptr = llhelper(FPTR, func)
    calldescr = cpu.calldescrof(FPTR.TO, (lltype.Signed,), lltype.Signed,
                                EffectInfo.MOST_GENERAL)

    def is_true(x, y):
        return True
    FPTR = Ptr(FuncType([lltype.Signed, lltype.Signed, lltype.Signed], lltype.Bool))
    is_true_ptr = llhelper(FPTR, is_true)
    istruedescr = cpu.calldescrof(FPTR.TO, (lltype.Signed,lltype.Signed), lltype.Bool,
                                EffectInfo.MOST_GENERAL)

    finaldescr = BasicFinalDescr(0)
    faildescr  = compile.ResumeGuardDescr()

    namespace = merge_dicts(test_util.LLtypeMixin.__dict__.copy(), locals().copy())
    metainterp = FakeMetaInterp()
    metainterp_sd = FakeMetaInterpStaticData(cpu)
    metainterp.staticdata = metainterp_sd
    jitdriver_sd = FakeJitDriverSD()

    def optimize(self, ops, call_pure_results=None):
        loop = self.parse(ops)
        jitcell_token = compile.make_jitcell_token(self.jitdriver_sd)
        token = TargetToken(jitcell_token, original_jitcell_token=jitcell_token)
        if loop.operations[-1].getopnum() == rop.JUMP:
            loop.operations[-1].setdescr(token)
        call_pure_results = self._convert_call_pure_results(call_pure_results)
        trace = convert_loop_to_trace(loop, self.metainterp_sd)
        compile_data = compile.SimpleCompileData(
            trace, call_pure_results=call_pure_results,
            enable_opts=self.enable_opts)
        info, ops = compile_data.optimize_trace(self.metainterp_sd, self.jitdriver_sd, {})
        return trace, info, ops, token

    def create_opt(self):
        return OptTraceSplit(self.metainterp_sd, self.jitdriver_sd, {}, None)

    def split(self, ops, call_pure_results=None):
        # trace, info, ops, token = self.optimize(ops, call_pure_results)
        loop = self.parse(ops)
        jitcell_token = compile.make_jitcell_token(self.jitdriver_sd)
        token = TargetToken(jitcell_token, original_jitcell_token=jitcell_token)
        if loop.operations[-1].getopnum() == rop.JUMP:
            loop.operations[-1].setdescr(token)
        call_pure_results = self._convert_call_pure_results(call_pure_results)
        trace = convert_loop_to_trace(loop, self.metainterp_sd)
        data = compile.SimpleSplitCompileData(
            trace, None, enable_opts=self.enable_opts, body_token=token)
        return data.optimize_trace(self.metainterp_sd, self.jitdriver_sd, {})

    def optimize_and_split(self, ops, call_pure_results=None):
        """
        - ops: operations represented as a string
        - call_pure_results
        - split_func: where to split
        """
        splitted = self.split(ops, call_pure_results)
        (body_info, body_ops), bridges = splitted[0], splitted[1:]

        body_label_op = ResOperation(rop.LABEL, body_info.inputargs,
                                     descr=body_info.target_token)
        body_label_op.setdescr(body_info.target_token)
        body_loop = compile.create_empty_loop(self.metainterp)
        body_loop.inputargs = body_info.inputargs
        body_loop.operations = body_ops

        loops = [(body_info, body_loop)]
        for (bridge_info, bridge_ops) in bridges:
            # bridge_token = bridge_info.target_token
            # bridge_label_op = ResOperation(rop.LABEL, bridge_info.inputargs)
            # bridge_label_op.setdescr(bridge_token)
            bridge_loop = compile.create_empty_loop(self.metainterp)
            bridge_loop.inputargs = bridge_info.inputargs
            #import pdb; pdb.set_trace()
            bridge_loop.operations = bridge_ops
            loops.append((bridge_info, bridge_loop))

        return loops

    def assert_target_token(self, ops, call_pure_results=None):
        trace, info, ops, token = self.optimize(ops, call_pure_results)
        data = compile.SimpleSplitCompileData(trace, None,
                                              enable_opts=self.enable_opts,
                                              body_token=token)
        # loops = data.split(self.metainterp_sd, self.jitdriver_sd, {}, ops, info.inputargs)
        loops = data.optimize_trace(self.metainterp_sd, self.jitdriver_sd, {})
        orig_loop, bridges = loops[0], loops[1:]
        orig_loop_info, orig_loop_ops = orig_loop

        fdescr_stack = []
        for op in orig_loop_ops:
            opnum = op.getopnum()
            if rop.is_guard(opnum):
                fdescr = op.getdescr()
                assert isinstance(fdescr, compile.ResumeGuardDescr)
                fdescr_stack.append(fdescr)

        for bridge_info, bridge_ops in bridges:
            assert bridge_info.faildescr == fdescr_stack.pop()
            for op in bridge_ops:
                if rop.is_guard(op.getopnum()):
                    fdescr = op.getdescr()
                    assert isinstance(fdescr, compile.ResumeGuardDescr)
                    fdescr_stack.append(fdescr)

    def assert_equal_split(self, ops, bodyops, bridgeops,
                           call_pure_results=None):
        loops = self.optimize_and_split(ops, call_pure_results)
        (body_info, body), (bridge_info, bridge) = loops[0], loops[1]
        body.check_consistency(check_descr=False)
        bridge.check_consistency(check_descr=False)
        body_exp_opts = parse(bodyops, namespace=self.namespace)
        body_exp = convert_old_style_to_targets(body_exp_opts, jump=True)
        bridge_exp_opts = parse(bridgeops, namespace=self.namespace)
        bridge_exp = convert_old_style_to_targets(bridge_exp_opts, jump=True)
        self.assert_equal(body, body_exp)
        self.assert_equal(bridge, bridge_exp)

    def optimize_loop(self, ops, optops, call_pure_results=None):
        loop = self.parse(ops)
        token = JitCellToken()
        if loop.operations[-1].getopnum() == rop.JUMP:
            loop.operations[-1].setdescr(token)
        exp = parse(optops, namespace=namespace)
        expected = convert_old_style_to_targets(exp, jump=True)
        call_pure_results = self._convert_call_pure_results(call_pure_results)
        trace = convert_loop_to_trace(loop, self.metainterp_sd)
        compile_data = compile.SimpleCompileData(
            trace, call_pure_results=call_pure_results,
            enable_opts=self.enable_opts)
        info, ops = compile_data.optimize_trace(self.metainterp_sd, None, {})
        label_op = ResOperation(rop.LABEL, info.inputargs)
        loop.inputargs = info.inputargs
        loop.operations = [label_op] + ops
        self.loop = loop
        self.assert_equal(loop, expected)

class TestOptTraceSplit(BaseTestTraceSplit):

    def test_trace_split_real_trace_1(self):
        setattr(self.metainterp_sd, "done_with_this_frame_descr_ref", compile.DoneWithThisFrameDescrRef())
        setattr(self.jitdriver_sd, "index", 0)
        setattr(self.jitdriver_sd, "num_red_args", 1)

        ops = """
        [p0]
        debug_merge_point(0, 0, 0, 0, '0: DUP ')
        i7 = call_i(ConstClass(func_ptr), p0, 1, 1, descr=calldescr)
        debug_merge_point(0, 0, 0, 1, '1: CONST_INT 1')
        i12 = call_i(ConstClass(func_ptr), p0, 2, 1, descr=calldescr)
        debug_merge_point(0, 0, 0, 3, '3: LT ')
        i16 = call_i(ConstClass(func_ptr), p0, 4, 1, descr=calldescr)
        debug_merge_point(0, 0, 0, 4, '4: JUMP_IF 8')
        p19 = call_r(ConstClass(pop), p0, 1, descr=popdescr)
        i21 = call_i(ConstClass(is_true_ptr), p0, p19, 1, descr=istruedescr)
        guard_true(i21, descr=<Guard0x7f86266bc140>) [i21, p0]
        debug_merge_point(0, 0, 0, 8, '8: CONST_INT 1')
        i29 = call_i(ConstClass(func_ptr), p0, 9, 1, descr=calldescr)
        debug_merge_point(0, 0, 0, 10, '10: SUB ')
        i33 = call_i(ConstClass(func_ptr), p0, 11, 1, descr=calldescr)
        debug_merge_point(0, 0, 0, 11, '11: JUMP 0')
        i38 = call_i(ConstClass(emit_jump_ptr), 6, 0, p0, 1, descr=emit_jump_descr)
        debug_merge_point(0, 0, 0, 6, '6: JUMP 13')
        debug_merge_point(0, 0, 0, 13, '13: EXIT ')
        p41 = call_r(ConstClass(pop), p0, 1, descr=popdescr)
        leave_portal_frame(0)
        finish(p41)
        """

        body = """
        [p0]
        debug_merge_point(0, 0, 0, 0, '0: DUP ')
        i7 = call_i(ConstClass(func_ptr), p0, 1, 0, descr=calldescr)
        debug_merge_point(0, 0, 0, 1, '1: CONST_INT 1')
        i12 = call_i(ConstClass(func_ptr), p0, 2, 0, descr=calldescr)
        debug_merge_point(0, 0, 0, 3, '3: LT ')
        i16 = call_i(ConstClass(func_ptr), p0, 4, 0, descr=calldescr)
        debug_merge_point(0, 0, 0, 4, '4: JUMP_IF 8')
        p19 = call_r(ConstClass(pop), p0, 0, descr=popdescr)
        i21 = call_i(ConstClass(is_true_ptr), p0, p19, 0, descr=istruedescr)
        guard_true(i21, descr=<Guard0x7f86266bc140>) [p0]
        debug_merge_point(0, 0, 0, 8, '8: CONST_INT 1')
        i29 = call_i(ConstClass(func_ptr), p0, 9, 0, descr=calldescr)
        debug_merge_point(0, 0, 0, 10, '10: SUB ')
        i33 = call_i(ConstClass(func_ptr), p0, 11, 0, descr=calldescr)
        debug_merge_point(0, 0, 0, 11, '11: JUMP 0')
        # i38 = call_i(ConstClass(emit_jump_ptr), 6, 0, p0, 0, descr=emit_jump_descr)
        jump(p0)
        """

        # descr
        bridge = """
        [p0]
        debug_merge_point(0, 0, 0, 6, '6: JUMP 13')
        debug_merge_point(0, 0, 0, 13, '13: EXIT ')
        p41 = call_r(ConstClass(pop), p0, 0, descr=popdescr)
        leave_portal_frame(0)
        finish(p41, descr=finaldescr)
        """

        self.assert_equal_split(ops, body, bridge)

    @pytest.mark.skip()
    def test_trace_split_real_trace_2(self):
        setattr(self.metainterp_sd, "done_with_this_frame_descr_ref", compile.DoneWithThisFrameDescrRef())
        setattr(self.jitdriver_sd, "index", 0)
        setattr(self.jitdriver_sd, "num_red_args", 1)

        ops ="""
        [p0]
        debug_merge_point(0, 0, 0, 3, '3: DUP1 1')
        call_n(ConstClass(func_ptr), p0, 4, 1, descr=calldescr)
        debug_merge_point(0, 0, 0, 5, '5: CONST_INT 2')
        call_n(ConstClass(func_ptr), p0, 6, 1, descr=calldescr)
        debug_merge_point(0, 0, 0, 7, '7: LT ')
        call_n(ConstClass(func_ptr), p0, 8, 1, descr=calldescr)
        debug_merge_point(0, 0, 0, 8, '8: JUMP_IF 14')
        p13 = call_r(ConstClass(func_ptr), p0, 1, descr=calldescr)
        i15 = call_i(ConstClass(is_true_ptr), p0, p13, 1, descr=istruedescr)
        guard_true(i15, descr=<Guard0x7f6886462068>) [i15, p0]
        debug_merge_point(0, 0, 0, 14, '14: DUP1 1')
        call_n(ConstClass(func_ptr), p0, 15, 1, descr=calldescr)
        guard_no_exception(descr=<Guard0x7f68864602c0>) [p0]
        debug_merge_point(0, 0, 0, 16, '16: DUP1 2')
        call_n(ConstClass(func_ptr), p0, 17, 1, descr=calldescr)
        guard_no_exception(descr=<Guard0x7f6886460320>) [p0]
        debug_merge_point(0, 0, 0, 18, '18: CONST_INT 1')
        call_n(ConstClass(func_ptr), p0, 19, 1, descr=calldescr)
        guard_no_exception(descr=<Guard0x7f6886460380>) [p0]
        debug_merge_point(0, 0, 0, 20, '20: SUB ')
        call_n(ConstClass(func_ptr), p0, 21, 1, descr=calldescr)
        guard_no_exception(descr=<Guard0x7f68864603e0>) [p0]
        debug_merge_point(0, 0, 0, 21, '21: CALL 3')
        call_may_force_n(ConstClass(func_ptr), p0, 22, 1, descr=calldescr)
        guard_not_forced(descr=<Guard0x7f6886460440>) [p0]
        guard_no_exception(descr=<Guard0x7f68864620b0>) [p0]
        debug_merge_point(0, 0, 0, 23, '23: ADD ')
        call_n(ConstClass(func_ptr), p0, 24, 1, descr=calldescr)
        guard_no_exception(descr=<Guard0x7f68864604a0>) [p0]
        debug_merge_point(0, 0, 0, 24, '24: RET 1')
        p32 = call_r(ConstClass(func_ptr), p0, 25, 1, descr=calldescr)
        i38 = call_i(ConstClass(emit_ret_ptr), 10, p32, descr=emit_ret_descr)
        guard_value(i38, 10, descr=<Guard0x7f6886460500>) [i38, p0]
        debug_merge_point(0, 0, 0, 10, '10: CONST_INT 1')
        call_n(ConstClass(func_ptr), p0, 11, 1, descr=calldescr)
        guard_no_exception(descr=<Guard0x7f6886460560>) [p0]
        debug_merge_point(0, 0, 0, 12, '12: JUMP 24')
        debug_merge_point(0, 0, 0, 24, '24: RET 1')
        p44 = call_r(ConstClass(func_ptr), p0, 25, 1, descr=calldescr)
        guard_no_exception(descr=<Guard0x7f68864605c0>) [p44]
        leave_portal_frame(0)
        finish(p44, descr=<DoneWithThisFrameDescrRef object at 0x55c0fa2d98e0>)
        """

        bodyops = """
        [p0]
        debug_merge_point(0, 0, 0, 3, '3: DUP1 1')
        call_n(ConstClass(func_ptr), p0, 4, 0, descr=calldescr)
        debug_merge_point(0, 0, 0, 5, '5: CONST_INT 2')
        call_n(ConstClass(func_ptr), p0, 6, 0, descr=calldescr)
        debug_merge_point(0, 0, 0, 7, '7: LT ')
        call_n(ConstClass(func_ptr), p0, 8, 0, descr=calldescr)
        debug_merge_point(0, 0, 0, 8, '8: JUMP_IF 14')
        p13 = call_r(ConstClass(func_ptr), p0, 0, descr=calldescr)
        i15 = call_i(ConstClass(is_true_ptr), p0, p13, 0, descr=istruedescr)
        guard_true(i15, descr=<Guard0x7f6886462068>) [p0]
        debug_merge_point(0, 0, 0, 14, '14: DUP1 1')
        call_n(ConstClass(func_ptr), p0, 15, 0, descr=calldescr)
        guard_no_exception(descr=<Guard0x7f68864602c0>) [p0]
        debug_merge_point(0, 0, 0, 16, '16: DUP1 2')
        call_n(ConstClass(func_ptr), p0, 17, 0, descr=calldescr)
        guard_no_exception(descr=<Guard0x7f6886460320>) [p0]
        debug_merge_point(0, 0, 0, 18, '18: CONST_INT 1')
        call_n(ConstClass(func_ptr), p0, 19, 0, descr=calldescr)
        guard_no_exception(descr=<Guard0x7f6886460380>) [p0]
        debug_merge_point(0, 0, 0, 20, '20: SUB ')
        call_n(ConstClass(func_ptr), p0, 21, 0, descr=calldescr)
        guard_no_exception(descr=<Guard0x7f68864603e0>) [p0]
        debug_merge_point(0, 0, 0, 21, '21: CALL 3')
        call_may_force_n(ConstClass(func_ptr), p0, 22, 0, descr=calldescr)
        guard_not_forced(descr=<Guard0x7f6886460440>) [p0]
        guard_no_exception(descr=<Guard0x7f68864620b0>) [p0]
        debug_merge_point(0, 0, 0, 23, '23: ADD ')
        call_n(ConstClass(func_ptr), p0, 24, 0, descr=calldescr)
        guard_no_exception(descr=<Guard0x7f68864604a0>) [p0]
        debug_merge_point(0, 0, 0, 24, '24: RET 1')
        p32 = call_r(ConstClass(func_ptr), p0, 25, 0, descr=calldescr)
        leave_portal_frame(0)
        finish(p32, descr=<DoneWithThisFrameDescrRef object at 0x55c0fa2d98e0>)
        """

        bridgeops = """
        [p0]
        debug_merge_point(0, 0, 0, 10, '10: CONST_INT 1')
        call_n(ConstClass(func_ptr), p0, 11, 0, descr=calldescr)
        guard_no_exception(descr=<Guard0x7f6886460560>) [p0]
        debug_merge_point(0, 0, 0, 12, '12: JUMP 24')
        debug_merge_point(0, 0, 0, 24, '24: RET 1')
        p44 = call_r(ConstClass(func_ptr), p0, 25, 0, descr=calldescr)
        guard_no_exception(descr=<Guard0x7f68864605c0>) [p44]
        leave_portal_frame(0)
        finish(p44, descr=<DoneWithThisFrameDescrRef object at 0x55c0fa2d98e0>)
        """

        self.assert_equal_split(ops, bodyops, bridgeops)

    @pytest.mark.skip()
    def test_trace_split_not_nested_branch_1(self):
        setattr(self.metainterp_sd, "done_with_this_frame_descr_ref", compile.DoneWithThisFrameDescrRef())
        setattr(self.jitdriver_sd, "index", 0)
        setattr(self.jitdriver_sd, "num_red_args", 1)

        ops2 = """
        [p0]
        debug_merge_point(0, 0, 0, 0, '0: LT')
        call_n(ConstClass(func_ptr), p0, 1, descr=calldescr)
        i1 = call_i(ConstClass(is_true_ptr), p0, 0, descr=istruedescr)
        guard_true(i1, descr=<Guard0x7f6886462068>) [p0] # fstack = [<Guard0x7f6886462068>]
        call_n(ConstClass(func_ptr), p0, 2, descr=calldescr)
        i2 = call_i(ConstClass(emit_jump_ptr), 6, 0, p0, descr=emit_jump_descr)

        # info: fdescr = <Guard0x7f6886462068>, fstack = []
        i3 = call_i(ConstClass(func_ptr), p0, descr=calldescr)
        i4 = call_i(ConstClass(is_true_ptr), p0, 2, descr=calldescr)
        guard_true(i4, descr=<Guard0x7f6886462068>) [p0] # fstack = [<Guard0x7f6886462068>]
        call_n(ConstClass(func_ptr), p0, 3, descr=calldescr)
        i5 = call_i(ConstClass(emit_jump_ptr), 6, 0, p0, descr=emit_jump_descr)

        # info: fdescr = <Guard0x7f6886462068>, fstack = []
        call_n(ConstClass(func_ptr), p0, 4, descr=calldescr)
        i6 = call_i(ConstClass(func_ptr), p0, descr=calldescr)
        jump(p0)
        """
        self.assert_target_token(ops2)

    @pytest.mark.skip()
    def test_trace_split_nested_branch_1(self):
        setattr(self.metainterp_sd, "done_with_this_frame_descr_ref", compile.DoneWithThisFrameDescrRef())
        setattr(self.jitdriver_sd, "index", 0)
        setattr(self.jitdriver_sd, "num_red_args", 1)

        ops = """
        [p0]
        debug_merge_point(0, 0, 0, 0, '0: LT')
        call_n(ConstClass(func_ptr), p0, 1, descr=calldescr)
        i1 = call_i(ConstClass(is_true_ptr), p0, 0, descr=istruedescr)
        guard_true(i1, descr=<Guard0x7f6886462068>) [p0] # fstack = [<Guard0x7f6886462068>]
        call_n(ConstClass(func_ptr), p0, 2, descr=calldescr)
        i2 = call_i(ConstClass(is_true_ptr), p0, 2, descr=calldescr)
        guard_true(i2, descr=<Guard0x7f6886462068>) [p0] # fstack = [<Guard0x7f6886462068>, <Guard0x7f6886462068>]
        call_n(ConstClass(func_ptr), p0, 3, descr=calldescr)
        i3 = call_i(ConstClass(emit_jump_ptr), 6, 0, p0, descr=emit_jump_descr)

        # info: resumekey = <Guard0x7f6886462068>, fstack = [<Guard0x7f6886462068>]
        call_n(ConstClass(func_ptr), p0, 4, descr=calldescr)
        i4 = call_i(ConstClass(emit_jump_ptr), 6, 0, p0, descr=emit_jump_descr)

        # info: resumekey = <Guard0x7f6886462068>, fstack = []
        i5 = call_i(ConstClass(func_ptr), p0, descr=calldescr)
        i6 = call_i(ConstClass(func_ptr), p0, descr=calldescr)
        jump(p0)
        """
        self.assert_target_token(ops)

    @pytest.mark.skip()
    def test_trace_split_nested_branch_2(self):
        setattr(self.metainterp_sd, "done_with_this_frame_descr_ref", compile.DoneWithThisFrameDescrRef())
        setattr(self.jitdriver_sd, "index", 0)
        setattr(self.jitdriver_sd, "num_red_args", 1)

        ops = """
        [p0]
        debug_merge_point(0, 0, 0, 0, '0: LT')
        call_n(ConstClass(func_ptr), p0, 1, descr=calldescr)
        i1 = call_i(ConstClass(is_true_ptr), p0, 0, descr=istruedescr)
        guard_true(i1, descr=<Guard0x7f6886462068>) [p0] # fstack = [<Guard0x7f6886462068>]
        call_n(ConstClass(func_ptr), p0, 2, descr=calldescr)
        i2 = call_i(ConstClass(is_true_ptr), p0, 2, descr=calldescr)
        guard_true(i2, descr=<Guard0x7f6886462068>) [p0] # fstack = [<Guard0x7f6886462068>, <Guard0x7f6886462068>]
        call_n(ConstClass(func_ptr), p0, 3, descr=calldescr)
        i3 = call_i(ConstClass(emit_jump_ptr), 6, 0, p0, descr=emit_jump_descr)

        # info: resumekey = <Guard0x7f6886462068>, fstack = [<Guard0x7f6886462068>]
        call_n(ConstClass(func_ptr), p0, 4, descr=calldescr)
        i4 = call_i(ConstClass(emit_jump_ptr), 11, 0, p0, descr=emit_jump_descr)

        # info: resumekey = <Guard0x7f6886462068>, fstack = []
        i5 = call_i(ConstClass(func_ptr), p0, descr=calldescr)
        i6 = call_i(ConstClass(func_ptr), p0, descr=calldescr)
        jump(p0)
        """

        trace, info, ops, token = self.optimize(ops)
        opt = self.create_opt()
        # jump_dic = opt.create_token_dic(ops, token)

        emit_jump_pos = [0, 6, 11]
        for i, key in enumerate(sorted(opt.token_map.keys())):
            assert key == emit_jump_pos[i]

    @pytest.mark.skip()
    def test_remove_useless_guards(self):

        ops = """
        [p0]
        i13 = call_i(ConstClass(emit_jump_ptr), 11, 0, descr=emit_jump_descr)
        i15 = int_lt(i13, 15)
        guard_true(i15, descr=<ResumeGuardDescr object at 0x7f46429a6230>) [i13, p0]
        guard_value(i13, 11, descr=<ResumeGuardCopiedDescr object at 0x7f46429a8060>) [i13, p0]
        call_n(ConstClass(func_ptr), p0, 12, descr=calldescr)
        guard_no_exception(descr=<ResumeGuardExcDescr object at 0x7f46429a6288>) [p0]
        call_n(ConstClass(func_ptr), p0, descr=calldescr)
        guard_no_exception(descr=<ResumeGuardExcDescr object at 0x7f46429a62e0>) [p0]
        p21 = call_r(ConstClass(func_ptr), p0, descr=calldescr)
        guard_no_exception(descr=<ResumeGuardExcDescr object at 0x7f46429a6338>) [p21, p0]
        i24 = call_i(ConstClass(emit_ret_ptr), 0, p21, descr=emit_ret_descr)
        i26 = int_lt(i24, 15)
        guard_true(i26, descr=<ResumeGuardDescr object at 0x7f46429a6390>) [i24, p0]
        guard_value(i24, 0, descr=<ResumeGuardCopiedDescr object at 0x7f46429a80a0>) [i24, p0]
        jump(p0)
        """

        expected = """
        [p0]
        i13 = call_i(ConstClass(emit_jump_ptr), 11, 0, descr=emit_jump_descr)
        call_n(ConstClass(func_ptr), p0, 12, descr=calldescr)
        guard_no_exception(descr=<ResumeGuardExcDescr object at 0x7f46429a6288>) [p0]
        call_n(ConstClass(func_ptr), p0, descr=calldescr)
        guard_no_exception(descr=<ResumeGuardExcDescr object at 0x7f46429a62e0>) [p0]
        p21 = call_r(ConstClass(func_ptr), p0, descr=calldescr)
        guard_no_exception(descr=<ResumeGuardExcDescr object at 0x7f46429a6338>) [p21, p0]
        i24 = call_i(ConstClass(emit_ret_ptr), 0, p21, descr=emit_ret_descr)
        jump(p0)
        """

        trace, info, ops, token = self.optimize(ops)
        optimized = self.create_opt()

        exp = parse(expected, namespace=self.namespace)

        for op1, op2 in zip(optimized, exp.operations):
            assert op1.opnum == op2.opnum
