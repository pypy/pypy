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
from rpython.jit.metainterp import compile, executor, pyjitpl
from rpython.jit.metainterp.resoperation import (
    rop, ResOperation, InputArgInt, OpHelpers, InputArgRef)
from rpython.jit.metainterp.support import ptr2int
from rpython.jit.metainterp.optimizeopt.intdiv import magic_numbers
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

    def emit_jump_if(x, y, z):
        return x
    FPTR3 = Ptr(FuncType([lltype.Signed, lltype.Signed, lltype.Signed], lltype.Signed))
    emit_jump_ptr = llhelper(FPTR3, emit_jump_if)
    emit_jump_descr = cpu.calldescrof(FPTR2.TO, (lltype.Signed, lltype.Signed), lltype.Signed,
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
        info, ops = compile_data.optimize_trace(self.metainterp_sd, None, {})
        return trace, info, ops, token

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
