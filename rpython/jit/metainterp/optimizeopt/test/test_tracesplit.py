import py
import sys
import re
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
    JitCellToken, BasicFinalDescr, BasicFailDescr, ConstInt, INT, Stats, get_const_ptr_for_string)
from rpython.jit.metainterp import compile, executor, pyjitpl, history
from rpython.jit.metainterp.resoperation import (
    rop, ResOperation, InputArgInt, OpHelpers, InputArgRef)
from rpython.jit.metainterp.support import ptr2int
from rpython.jit.metainterp.optimizeopt.intdiv import magic_numbers
from rpython.jit.metainterp.optimizeopt.tracesplit import TraceSplitOpt
from rpython.jit.metainterp.test.test_resume import (
    ResumeDataFakeReader, MyMetaInterp)
from rpython.jit.metainterp.optimizeopt.test import test_util, test_dependency
from rpython.jit.metainterp.optimizeopt.test.test_util import (
    BaseTest, FakeDescr, convert_old_style_to_targets)
from rpython.jit.tool.oparser import parse, convert_loop_to_trace

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

class FakeJitDriverSD(object):
    result_type = history.REF
    index = 0

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
    emit_jump_if_ptr = llhelper(FPTR2, emit_jump)
    emit_jump_if_descr = cpu.calldescrof(FPTR2.TO, (lltype.Signed, lltype.Signed), lltype.Signed,
                                         EffectInfo.MOST_GENERAL)

    def emit_ret(x, y):
        return x
    FPTR3 = Ptr(FuncType([lltype.Signed, lltype.Char], lltype.Signed))
    emit_ret_ptr = llhelper(FPTR3, emit_ret)
    emit_ret_descr = cpu.calldescrof(FPTR2.TO, (lltype.Signed, lltype.Char), lltype.Signed,
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
        token = JitCellToken()
        if loop.operations[-1].getopnum() == rop.JUMP:
            loop.operations[-1].setdescr(token)
        call_pure_results = self._convert_call_pure_results(call_pure_results)
        trace = convert_loop_to_trace(loop, self.metainterp_sd)
        compile_data = compile.SimpleCompileData(
            trace, call_pure_results=call_pure_results,
            enable_opts=self.enable_opts)
        info, ops = compile_data.optimize_trace(self.metainterp_sd, self.jitdriver_sd, {})
        return trace, info, ops, token

    def optimize_and_make_data(self, ops, call_pure_results=None):
        trace, info, ops, token = self.optimize(ops, call_pure_results)
        return TraceSplitOpt(self.metainterp_sd, self.jitdriver_sd)

    def optimize_and_split(self, ops, split_at, guard_at, call_pure_results=None, split_func=None):
        trace, info, ops, token = self.optimize(ops, call_pure_results)
        bridge_token = JitCellToken()
        assert split_at is not None
        assert guard_at is not None
        data = compile.SimpleSplitCompileData(
            trace, None, enable_opts=self.enable_opts, split_at=split_at, guard_at=guard_at,
            body_token=token, bridge_token=bridge_token)
        (body_info, body_ops), (bridge_info, bridge_ops) = data.split(
            self.metainterp_sd, None, {}, ops, info.inputargs)

        body_label_op = ResOperation(rop.LABEL, body_info.inputargs)
        body_label_op.setdescr(token)
        body_loop = compile.create_empty_loop(self.metainterp)
        body_loop.inputargs = body_info.inputargs
        body_loop.operations = [body_label_op] + body_ops

        bridge_label_op = ResOperation(rop.LABEL, bridge_info.inputargs)
        bridge_label_op.setdescr(bridge_token)
        bridge_loop = compile.create_empty_loop(self.metainterp)
        bridge_loop.inputargs = info.inputargs
        bridge_loop.operations = [bridge_label_op] + bridge_ops
        return body_loop, bridge_loop

    def optimize_and_split2(self, ops, split_at, guard_at, call_pure_results):
        trace, info, ops, token = self.optimize(ops, call_pure_results)
        bridge_token = JitCellToken()
        data = compile.SimpleSplitCompileData(
            trace, None, enable_opts=self.enable_opts)
        (body_info, body_ops), (bridge_info, bridge_ops) = data.split2(
            self.metainterp_sd, None, {}, ops, info.inputargs, split_at, guard_at,
            token, bridge_token)

        body_label_op = ResOperation(rop.LABEL, body_info.inputargs)
        body_label_op.setdescr(token)
        body_loop = compile.create_empty_loop(self.metainterp)
        body_loop.inputargs = body_info.inputargs # prev.inputargs
        body_loop.operations = [body_label_op] + body_ops

        bridge_label_op = ResOperation(rop.LABEL, bridge_info.inputargs)
        bridge_label_op.setdescr(bridge_token)
        bridge_loop = compile.create_empty_loop(self.metainterp)
        bridge_loop.inputargs = info.inputargs
        bridge_loop.operations = [bridge_label_op] + bridge_ops
        return body_loop, bridge_loop

    def assert_equal_split(self, ops, bodyops, bridgeops,
                           split_at=None, guard_at=None, call_pure_results=None):
        body, bridge = self.optimize_and_split(ops, split_at, guard_at,
                                               call_pure_results)
        body_exp_opts = parse(bodyops, namespace=self.namespace)
        body_exp = convert_old_style_to_targets(body_exp_opts, jump=True)
        bridge_exp_opts = parse(bridgeops, namespace=self.namespace)
        bridge_exp = convert_old_style_to_targets(bridge_exp_opts, jump=True)
        self.assert_equal(body, body_exp)
        self.assert_equal(bridge, bridge_exp)

    def assert_equal_guard(self, ops, bodyops, bridgeops,
                           split_at=None, marker=None, call_pure_results=None,):
        body, bridge = self.optimize_and_split(ops, split_at,
                                               call_pure_results)
        body_exp_opts = parse(bodyops, namespace=self.namespace)
        body_exp = convert_old_style_to_targets(body_exp_opts, jump=True)
        bridge_exp_opts = parse(bridgeops, namespace=self.namespace)
        bridge_exp = convert_old_style_to_targets(bridge_exp_opts, jump=True)


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

    def test_find_cut_points_with_ops(self):
        ops = """
        [p0]
        debug_merge_point(0, 0, '24: RET 1')
        p33 = call_r(ConstClass(func_ptr), p0, 25, descr=calldescr)
        i36 = call_i(ConstClass(emit_ret_ptr), 10, p33, descr=emit_ret_descr)
        debug_merge_point(0, 0, '10: CONST_INT 1')
        call_n(ConstClass(func_ptr), p0, 11, descr=calldescr)
        debug_merge_point(0, 0, '12: RET 1')
        p42 = call_r(ConstClass(func_ptr), p0, 13, descr=calldescr)
        leave_portal_frame(0)
        finish(p42, descr=<DoneWithThisFrameDescrRef object at 0x55cf88b4f8c0>)
        """

        setattr(self.metainterp_sd, "done_with_this_frame_descr_ref", compile.DoneWithThisFrameDescrRef())
        setattr(self.jitdriver_sd, "index", 0)
        trace, info, ops, token = self.optimize(ops, call_pure_results=None)
        opt = TraceSplitOpt(self.metainterp_sd, self.jitdriver_sd)
        dic = opt.find_cut_points_with_ops(trace, ops, info.inputargs, token)
        assert len(dic.keys()) == 1
        assert dic.keys()[0] == 2


    def test_trace_split_real_trace_1(self):
        ops = """
        [p0]
        debug_merge_point(0, 0, '0: DUP ')
        i7 = call_i(ConstClass(func_ptr), p0, 1, descr=calldescr)
        debug_merge_point(0, 0, '1: CONST_INT 1')
        i12 = call_i(ConstClass(func_ptr), p0, 2, descr=calldescr)
        debug_merge_point(0, 0, '3: LT ')
        i16 = call_i(ConstClass(func_ptr), p0, 4, descr=calldescr)
        debug_merge_point(0, 0, '4: JUMP_IF 8')
        p19 = call_r(ConstClass(pop), p0, descr=popdescr)
        i21 = call_i(ConstClass(is_true_ptr), p0, p19, descr=istruedescr)
        guard_true(i21, descr=<Guard0x7f86266bc140>) [i21, p0]
        debug_merge_point(0, 0, '8: CONST_INT 1')
        i29 = call_i(ConstClass(func_ptr), p0, 9, descr=calldescr)
        debug_merge_point(0, 0, '10: SUB ')
        i33 = call_i(ConstClass(func_ptr), p0, 11, descr=calldescr)
        debug_merge_point(0, 0, '11: JUMP 0')
        i38 = call_i(ConstClass(emit_jump_ptr), 6, 0, p0, descr=emit_jump_descr)
        debug_merge_point(0, 0, '6: JUMP 13')
        debug_merge_point(0, 0, '13: EXIT ')
        p41 = call_r(ConstClass(pop), p0, descr=popdescr)
        leave_portal_frame(0)
        finish(p41)
        """

        body = """
        [p0]
        debug_merge_point(0, 0, '0: DUP ')
        i7 = call_i(ConstClass(func_ptr), p0, 1, descr=calldescr)
        debug_merge_point(0, 0, '1: CONST_INT 1')
        i12 = call_i(ConstClass(func_ptr), p0, 2, descr=calldescr)
        debug_merge_point(0, 0, '3: LT ')
        i16 = call_i(ConstClass(func_ptr), p0, 4, descr=calldescr)
        debug_merge_point(0, 0, '4: JUMP_IF 8')
        p19 = call_r(ConstClass(pop), p0, descr=popdescr)
        i21 = call_i(ConstClass(is_true_ptr), p0, p19, descr=istruedescr)
        guard_true(i21, descr=<Guard0x7f86266bc140>) [p0]
        debug_merge_point(0, 0, '8: CONST_INT 1')
        i29 = call_i(ConstClass(func_ptr), p0, 9, descr=calldescr)
        debug_merge_point(0, 0, '10: SUB ')
        i33 = call_i(ConstClass(func_ptr), p0, 11, descr=calldescr)
        debug_merge_point(0, 0, '11: JUMP 0')
        # i38 = call_i(ConstClass(emit_jump_ptr), 6, 0, p0, descr=emit_jump_descr)
        jump(p0)
        """

        # descr
        bridge = """
        [p0]
        debug_merge_point(0, 0, '6: JUMP 13')
        debug_merge_point(0, 0, '13: EXIT ')
        p41 = call_r(ConstClass(pop), p0, descr=popdescr)
        leave_portal_frame(0)
        finish(p41, descr=finaldescr)
        """

        self.assert_equal_split(ops, body, bridge, split_at="emit_jump", guard_at="is_true")

    def test_trace_split_real_trace_2(self ):
        ops ="""
        [p0]
        debug_merge_point(0, 0, '3: DUP1 1')
        call_n(ConstClass(func_ptr), p0, 4, descr=calldescr)
        debug_merge_point(0, 0, '5: CONST_INT 2')
        call_n(ConstClass(func_ptr), p0, 6, descr=calldescr)
        debug_merge_point(0, 0, '7: LT ')
        call_n(ConstClass(func_ptr), p0, 8, descr=calldescr)
        debug_merge_point(0, 0, '8: JUMP_IF 14')
        p13 = call_r(ConstClass(func_ptr), p0, descr=calldescr)
        i15 = call_i(ConstClass(is_true_ptr), p0, p13, descr=istruedescr)
        guard_true(i15, descr=<Guard0x7f6886462068>) [i15, p0]
        guard_value(i19, 14, descr=<Guard0x7f6886460260>) [i19, p0]
        debug_merge_point(0, 0, '14: DUP1 1')
        call_n(ConstClass(Frame.tla_DUP1), p0, 15, descr=<Callv 0 ri EF=5>)
        guard_no_exception(descr=<Guard0x7f68864602c0>) [p0]
        debug_merge_point(0, 0, '16: DUP1 2')
        call_n(ConstClass(Frame.tla_DUP1), p0, 17, descr=<Callv 0 ri EF=5>)
        guard_no_exception(descr=<Guard0x7f6886460320>) [p0]
        debug_merge_point(0, 0, '18: CONST_INT 1')
        call_n(ConstClass(Frame.tla_CONST_INT), p0, 19, descr=<Callv 0 ri EF=5>)
        guard_no_exception(descr=<Guard0x7f6886460380>) [p0]
        debug_merge_point(0, 0, '20: SUB ')
        call_n(ConstClass(Frame.tla_SUB), p0, 21, descr=<Callv 0 ri EF=5>)
        guard_no_exception(descr=<Guard0x7f68864603e0>) [p0]
        debug_merge_point(0, 0, '21: CALL 3')
        call_may_force_n(ConstClass(Frame.tla_CALL), p0, 22, ConstPtr(ptr31), descr=<Callv 0 rir EF=7>)
        guard_not_forced(descr=<Guard0x7f6886460440>) [p0]
        guard_no_exception(descr=<Guard0x7f68864620b0>) [p0]
        p32 = getfield_gc_r(p0, descr=<FieldP interp_tc.Frame.inst_bytecode 8>)
        guard_value(p32, ConstPtr(ptr33), descr=<Guard0x7f68864620f8>) [p0]
        debug_merge_point(0, 0, '23: ADD ')
        call_n(ConstClass(Frame.tla_ADD), p0, 24, descr=<Callv 0 ri EF=5>)
        guard_no_exception(descr=<Guard0x7f68864604a0>) [p0]
        debug_merge_point(0, 0, '24: RET 1')
        i38 = call_i(ConstClass(emit_ret), 10, p0, descr=<Calli 8 ir EF=2>)
        guard_value(i38, 10, descr=<Guard0x7f6886460500>) [i38, p0]
        debug_merge_point(0, 0, '10: CONST_INT 1')
        call_n(ConstClass(Frame.tla_CONST_INT), p0, 11, descr=<Callv 0 ri EF=5>)
        guard_no_exception(descr=<Guard0x7f6886460560>) [p0]
        debug_merge_point(0, 0, '12: JUMP 24')
        debug_merge_point(0, 0, '24: RET 1')
        p44 = call_r(ConstClass(Frame.tla_RET), p0, 25, descr=<Callr 8 ri EF=5>)
        guard_no_exception(descr=<Guard0x7f68864605c0>) [p44]
        leave_portal_frame(0)
        finish(p44, descr=<DoneWithThisFrameDescrRef object at 0x55c0fa2d98e0>)
        """
