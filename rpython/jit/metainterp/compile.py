import weakref
from rpython.rtyper.lltypesystem import lltype
from rpython.rtyper.annlowlevel import cast_instance_to_gcref
from rpython.rlib.objectmodel import we_are_translated
from rpython.rlib.debug import debug_start, debug_stop, debug_print
from rpython.rlib import rstack
from rpython.rlib.jit import JitDebugInfo, Counters, dont_look_inside
from rpython.conftest import option
from rpython.tool.sourcetools import func_with_new_name

from rpython.jit.metainterp.resoperation import ResOperation, rop, get_deep_immutable_oplist
from rpython.jit.metainterp.history import (TreeLoop, Box, JitCellToken,
    TargetToken, AbstractFailDescr, BoxInt, BoxPtr, BoxFloat, ConstInt)
from rpython.jit.metainterp import history, jitexc
from rpython.jit.metainterp.optimize import InvalidLoop
from rpython.jit.metainterp.inliner import Inliner
from rpython.jit.metainterp.resume import NUMBERING, PENDINGFIELDSP, ResumeDataDirectReader
from rpython.jit.codewriter import heaptracker, longlong


def giveup():
    from rpython.jit.metainterp.pyjitpl import SwitchToBlackhole
    raise SwitchToBlackhole(Counters.ABORT_BRIDGE)


def show_procedures(metainterp_sd, procedure=None, error=None):
    # debugging
    if option and (option.view or option.viewloops):
        if error:
            errmsg = error.__class__.__name__
            if str(error):
                errmsg += ': ' + str(error)
        else:
            errmsg = None
        if procedure is None:
            extraprocedures = []
        else:
            extraprocedures = [procedure]
        metainterp_sd.stats.view(errmsg=errmsg,
                                 extraprocedures=extraprocedures,
                                 metainterp_sd=metainterp_sd)

def create_empty_loop(metainterp, name_prefix=''):
    name = metainterp.staticdata.stats.name_for_new_loop()
    loop = TreeLoop(name_prefix + name)
    loop.call_pure_results = metainterp.call_pure_results
    return loop


def make_jitcell_token(jitdriver_sd):
    jitcell_token = JitCellToken()
    jitcell_token.outermost_jitdriver_sd = jitdriver_sd
    return jitcell_token

def record_loop_or_bridge(metainterp_sd, loop):
    """Do post-backend recordings and cleanups on 'loop'.
    """
    # get the original jitcell token corresponding to jitcell form which
    # this trace starts
    original_jitcell_token = loop.original_jitcell_token
    assert original_jitcell_token is not None
    if metainterp_sd.warmrunnerdesc is not None:    # for tests
        assert original_jitcell_token.generation > 0     # has been registered with memmgr
    wref = weakref.ref(original_jitcell_token)
    for op in loop.operations:
        descr = op.getdescr()
        if isinstance(descr, ResumeDescr):
            descr.wref_original_loop_token = wref   # stick it there
            n = descr.index
            if n >= 0:       # we also record the resumedescr number
                original_jitcell_token.compiled_loop_token.record_faildescr_index(n)
        elif isinstance(descr, JitCellToken):
            # for a CALL_ASSEMBLER: record it as a potential jump.
            if descr is not original_jitcell_token:
                original_jitcell_token.record_jump_to(descr)
            descr.exported_state = None
            op.cleardescr()    # clear reference, mostly for tests
        elif isinstance(descr, TargetToken):
            # for a JUMP: record it as a potential jump.
            # (the following test is not enough to prevent more complicated
            # cases of cycles, but at least it helps in simple tests of
            # test_memgr.py)
            if descr.original_jitcell_token is not original_jitcell_token:
                assert descr.original_jitcell_token is not None
                original_jitcell_token.record_jump_to(descr.original_jitcell_token)
            # exported_state is clear by optimizeopt when the short preamble is
            # constrcucted. if that did not happen the label should not show up
            # in a trace that will be used
            assert descr.exported_state is None
            if not we_are_translated():
                op._descr_wref = weakref.ref(op._descr)
            op.cleardescr()    # clear reference to prevent the history.Stats
                               # from keeping the loop alive during tests
    # record this looptoken on the QuasiImmut used in the code
    if loop.quasi_immutable_deps is not None:
        for qmut in loop.quasi_immutable_deps:
            qmut.register_loop_token(wref)
        # XXX maybe we should clear the dictionary here
    # mostly for tests: make sure we don't keep a reference to the LoopToken
    loop.original_jitcell_token = None
    if not we_are_translated():
        loop._looptoken_number = original_jitcell_token.number

# ____________________________________________________________

def compile_loop(metainterp, greenkey, start,
                 inputargs, jumpargs,
                 resume_at_jump_descr, full_preamble_needed=True,
                 try_disabling_unroll=False):
    """Try to compile a new procedure by closing the current history back
    to the first operation.
    """
    from rpython.jit.metainterp.optimizeopt import optimize_trace

    metainterp_sd = metainterp.staticdata
    jitdriver_sd = metainterp.jitdriver_sd
    history = metainterp.history

    enable_opts = jitdriver_sd.warmstate.enable_opts
    if try_disabling_unroll:
        if 'unroll' not in enable_opts:
            return None
        enable_opts = enable_opts.copy()
        del enable_opts['unroll']

    jitcell_token = make_jitcell_token(jitdriver_sd)
    part = create_empty_loop(metainterp)
    part.inputargs = inputargs[:]
    h_ops = history.operations
    part.resume_at_jump_descr = resume_at_jump_descr
    part.operations = [ResOperation(rop.LABEL, inputargs, None, descr=TargetToken(jitcell_token))] + \
                      [h_ops[i].clone() for i in range(start, len(h_ops))] + \
                      [ResOperation(rop.LABEL, jumpargs, None, descr=jitcell_token)]

    try:
        optimize_trace(metainterp_sd, part, enable_opts)
    except InvalidLoop:
        return None
    target_token = part.operations[0].getdescr()
    assert isinstance(target_token, TargetToken)
    all_target_tokens = [target_token]

    loop = create_empty_loop(metainterp)
    loop.inputargs = part.inputargs
    loop.operations = part.operations
    loop.quasi_immutable_deps = {}
    if part.quasi_immutable_deps:
        loop.quasi_immutable_deps.update(part.quasi_immutable_deps)
    while part.operations[-1].getopnum() == rop.LABEL:
        inliner = Inliner(inputargs, jumpargs)
        part.quasi_immutable_deps = None
        part.operations = [part.operations[-1]] + \
                          [inliner.inline_op(h_ops[i]) for i in range(start, len(h_ops))] + \
                          [ResOperation(rop.JUMP, [inliner.inline_arg(a) for a in jumpargs],
                                        None, descr=jitcell_token)]
        target_token = part.operations[0].getdescr()
        assert isinstance(target_token, TargetToken)
        all_target_tokens.append(target_token)
        inputargs = jumpargs
        jumpargs = part.operations[-1].getarglist()

        try:
            optimize_trace(metainterp_sd, part, enable_opts)
        except InvalidLoop:
            return None

        loop.operations = loop.operations[:-1] + part.operations
        if part.quasi_immutable_deps:
            loop.quasi_immutable_deps.update(part.quasi_immutable_deps)

    if not loop.quasi_immutable_deps:
        loop.quasi_immutable_deps = None
    for box in loop.inputargs:
        assert isinstance(box, Box)

    loop.original_jitcell_token = jitcell_token
    for label in all_target_tokens:
        assert isinstance(label, TargetToken)
        if label.virtual_state and label.short_preamble:
            metainterp_sd.logger_ops.log_short_preamble([], label.short_preamble)
    jitcell_token.target_tokens = all_target_tokens
    propagate_original_jitcell_token(loop)
    send_loop_to_backend(greenkey, jitdriver_sd, metainterp_sd, loop, "loop")
    record_loop_or_bridge(metainterp_sd, loop)
    return all_target_tokens[0]

def compile_retrace(metainterp, greenkey, start,
                    inputargs, jumpargs,
                    resume_at_jump_descr, partial_trace, resumekey):
    """Try to compile a new procedure by closing the current history back
    to the first operation.
    """
    from rpython.jit.metainterp.optimizeopt import optimize_trace

    history = metainterp.history
    metainterp_sd = metainterp.staticdata
    jitdriver_sd = metainterp.jitdriver_sd

    loop_jitcell_token = metainterp.get_procedure_token(greenkey)
    assert loop_jitcell_token
    assert partial_trace.operations[-1].getopnum() == rop.LABEL

    part = create_empty_loop(metainterp)
    part.inputargs = inputargs[:]
    part.resume_at_jump_descr = resume_at_jump_descr
    h_ops = history.operations

    part.operations = [partial_trace.operations[-1]] + \
                      [h_ops[i].clone() for i in range(start, len(h_ops))] + \
                      [ResOperation(rop.JUMP, jumpargs, None, descr=loop_jitcell_token)]
    label = part.operations[0]
    orignial_label = label.clone()
    assert label.getopnum() == rop.LABEL
    try:
        optimize_trace(metainterp_sd, part, jitdriver_sd.warmstate.enable_opts)
    except InvalidLoop:
        # Fall back on jumping to preamble
        target_token = label.getdescr()
        assert isinstance(target_token, TargetToken)
        assert target_token.exported_state
        part.operations = [orignial_label] + \
                          [ResOperation(rop.JUMP, inputargs[:],
                                        None, descr=loop_jitcell_token)]
        try:
            optimize_trace(metainterp_sd, part, jitdriver_sd.warmstate.enable_opts,
                           inline_short_preamble=False)
        except InvalidLoop:
            return None
    assert part.operations[-1].getopnum() != rop.LABEL
    target_token = label.getdescr()
    assert isinstance(target_token, TargetToken)
    assert loop_jitcell_token.target_tokens
    loop_jitcell_token.target_tokens.append(target_token)
    if target_token.short_preamble:
        metainterp_sd.logger_ops.log_short_preamble([], target_token.short_preamble)

    loop = partial_trace
    loop.operations = loop.operations[:-1] + part.operations

    quasi_immutable_deps = {}
    if loop.quasi_immutable_deps:
        quasi_immutable_deps.update(loop.quasi_immutable_deps)
    if part.quasi_immutable_deps:
        quasi_immutable_deps.update(part.quasi_immutable_deps)
    if quasi_immutable_deps:
        loop.quasi_immutable_deps = quasi_immutable_deps

    for box in loop.inputargs:
        assert isinstance(box, Box)

    target_token = loop.operations[-1].getdescr()
    resumekey.compile_and_attach(metainterp, loop)

    target_token = label.getdescr()
    assert isinstance(target_token, TargetToken)
    record_loop_or_bridge(metainterp_sd, loop)
    return target_token

def patch_new_loop_to_load_virtualizable_fields(loop, jitdriver_sd):
    vinfo = jitdriver_sd.virtualizable_info
    extra_ops = []
    inputargs = loop.inputargs
    vable_box = inputargs[jitdriver_sd.index_of_virtualizable]
    i = jitdriver_sd.num_red_args
    loop.inputargs = inputargs[:i]
    for descr in vinfo.static_field_descrs:
        assert i < len(inputargs)
        box = inputargs[i]
        extra_ops.append(
            ResOperation(rop.GETFIELD_GC, [vable_box], box, descr))
        i += 1
    arrayindex = 0
    for descr in vinfo.array_field_descrs:
        vable = vable_box.getref_base()
        arraylen = vinfo.get_array_length(vable, arrayindex)
        arraybox = BoxPtr()
        extra_ops.append(
            ResOperation(rop.GETFIELD_GC, [vable_box], arraybox, descr))
        arraydescr = vinfo.array_descrs[arrayindex]
        assert i + arraylen <= len(inputargs)
        for index in range(arraylen):
            box = inputargs[i]
            extra_ops.append(
                ResOperation(rop.GETARRAYITEM_GC,
                             [arraybox, ConstInt(index)],
                             box, descr=arraydescr))
            i += 1
        arrayindex += 1
    assert i == len(inputargs)
    loop.operations = extra_ops + loop.operations

def propagate_original_jitcell_token(trace):
    for op in trace.operations:
        if op.getopnum() == rop.LABEL:
            token = op.getdescr()
            assert isinstance(token, TargetToken)
            assert token.original_jitcell_token is None
            token.original_jitcell_token = trace.original_jitcell_token


def do_compile_loop(metainterp_sd, inputargs, operations, looptoken,
                    log=True, name=''):
    metainterp_sd.logger_ops.log_loop(inputargs, operations, -2,
                                      'compiling', name=name)
    return metainterp_sd.cpu.compile_loop(inputargs, operations, looptoken,
                                          log=log, name=name,
                                          logger=metainterp_sd.logger_ops)

def do_compile_bridge(metainterp_sd, faildescr, inputargs, operations,
                      original_loop_token, log=True):
    metainterp_sd.logger_ops.log_bridge(inputargs, operations, "compiling")
    assert isinstance(faildescr, AbstractFailDescr)
    return metainterp_sd.cpu.compile_bridge(faildescr, inputargs, operations,
                                            original_loop_token, log=log,
                                            logger=metainterp_sd.logger_ops)

def send_loop_to_backend(greenkey, jitdriver_sd, metainterp_sd, loop, type):
    vinfo = jitdriver_sd.virtualizable_info
    if vinfo is not None:
        patch_new_loop_to_load_virtualizable_fields(loop, jitdriver_sd)

    original_jitcell_token = loop.original_jitcell_token
    loopname = jitdriver_sd.warmstate.get_location_str(greenkey)
    globaldata = metainterp_sd.globaldata
    original_jitcell_token.number = n = globaldata.loopnumbering
    globaldata.loopnumbering += 1

    if not we_are_translated():
        show_procedures(metainterp_sd, loop)
        loop.check_consistency()

    if metainterp_sd.warmrunnerdesc is not None:
        hooks = metainterp_sd.warmrunnerdesc.hooks
        debug_info = JitDebugInfo(jitdriver_sd, metainterp_sd.logger_ops,
                                  original_jitcell_token, loop.operations,
                                  type, greenkey)
        hooks.before_compile(debug_info)
    else:
        debug_info = None
        hooks = None
    operations = get_deep_immutable_oplist(loop.operations)
    metainterp_sd.profiler.start_backend()
    debug_start("jit-backend")
    try:
        asminfo = do_compile_loop(metainterp_sd, loop.inputargs,
                                  operations, original_jitcell_token,
                                  name=loopname)
    finally:
        debug_stop("jit-backend")
    metainterp_sd.profiler.end_backend()
    if hooks is not None:
        debug_info.asminfo = asminfo
        hooks.after_compile(debug_info)
    metainterp_sd.stats.add_new_loop(loop)
    if not we_are_translated():
        metainterp_sd.stats.compiled()
    metainterp_sd.log("compiled new " + type)
    #
    if asminfo is not None:
        ops_offset = asminfo.ops_offset
    else:
        ops_offset = None
    metainterp_sd.logger_ops.log_loop(loop.inputargs, loop.operations, n,
                                      type, ops_offset,
                                      name=loopname)
    #
    if metainterp_sd.warmrunnerdesc is not None:    # for tests
        metainterp_sd.warmrunnerdesc.memory_manager.keep_loop_alive(original_jitcell_token)

def send_bridge_to_backend(jitdriver_sd, metainterp_sd, faildescr, inputargs,
                           operations, original_loop_token):
    if not we_are_translated():
        show_procedures(metainterp_sd)
        seen = dict.fromkeys(inputargs)
        TreeLoop.check_consistency_of_branch(operations, seen)
    if metainterp_sd.warmrunnerdesc is not None:
        hooks = metainterp_sd.warmrunnerdesc.hooks
        debug_info = JitDebugInfo(jitdriver_sd, metainterp_sd.logger_ops,
                                  original_loop_token, operations, 'bridge',
                                  fail_descr=faildescr)
        hooks.before_compile_bridge(debug_info)
    else:
        hooks = None
        debug_info = None
    operations = get_deep_immutable_oplist(operations)
    metainterp_sd.profiler.start_backend()
    debug_start("jit-backend")
    try:
        asminfo = do_compile_bridge(metainterp_sd, faildescr, inputargs,
                                    operations,
                                    original_loop_token)
    finally:
        debug_stop("jit-backend")
    metainterp_sd.profiler.end_backend()
    if hooks is not None:
        debug_info.asminfo = asminfo
        hooks.after_compile_bridge(debug_info)
    if not we_are_translated():
        metainterp_sd.stats.compiled()
    metainterp_sd.log("compiled new bridge")
    #
    if asminfo is not None:
        ops_offset = asminfo.ops_offset
    else:
        ops_offset = None
    metainterp_sd.logger_ops.log_bridge(inputargs, operations, None, faildescr,
                                        ops_offset)
    #
    #if metainterp_sd.warmrunnerdesc is not None:    # for tests
    #    metainterp_sd.warmrunnerdesc.memory_manager.keep_loop_alive(
    #        original_loop_token)

# ____________________________________________________________

class _DoneWithThisFrameDescr(AbstractFailDescr):
    final_descr = True

class DoneWithThisFrameDescrVoid(_DoneWithThisFrameDescr):
    def handle_fail(self, deadframe, metainterp_sd, jitdriver_sd):
        assert jitdriver_sd.result_type == history.VOID
        raise jitexc.DoneWithThisFrameVoid()

class DoneWithThisFrameDescrInt(_DoneWithThisFrameDescr):
    def handle_fail(self, deadframe, metainterp_sd, jitdriver_sd):
        assert jitdriver_sd.result_type == history.INT
        result = metainterp_sd.cpu.get_int_value(deadframe, 0)
        raise jitexc.DoneWithThisFrameInt(result)

class DoneWithThisFrameDescrRef(_DoneWithThisFrameDescr):
    def handle_fail(self, deadframe, metainterp_sd, jitdriver_sd):
        assert jitdriver_sd.result_type == history.REF
        cpu = metainterp_sd.cpu
        result = cpu.get_ref_value(deadframe, 0)
        raise jitexc.DoneWithThisFrameRef(cpu, result)

class DoneWithThisFrameDescrFloat(_DoneWithThisFrameDescr):
    def handle_fail(self, deadframe, metainterp_sd, jitdriver_sd):
        assert jitdriver_sd.result_type == history.FLOAT
        result = metainterp_sd.cpu.get_float_value(deadframe, 0)
        raise jitexc.DoneWithThisFrameFloat(result)

class ExitFrameWithExceptionDescrRef(_DoneWithThisFrameDescr):
    def handle_fail(self, deadframe, metainterp_sd, jitdriver_sd):
        cpu = metainterp_sd.cpu
        value = cpu.get_ref_value(deadframe, 0)
        raise jitexc.ExitFrameWithExceptionRef(cpu, value)


class TerminatingLoopToken(JitCellToken): # FIXME: kill?
    terminating = True

    def __init__(self, nargs, finishdescr):
        self.finishdescr = finishdescr

def make_done_loop_tokens():
    done_with_this_frame_descr_void = DoneWithThisFrameDescrVoid()
    done_with_this_frame_descr_int = DoneWithThisFrameDescrInt()
    done_with_this_frame_descr_ref = DoneWithThisFrameDescrRef()
    done_with_this_frame_descr_float = DoneWithThisFrameDescrFloat()
    exit_frame_with_exception_descr_ref = ExitFrameWithExceptionDescrRef()

    # pseudo loop tokens to make the life of optimize.py easier
    d = {'loop_tokens_done_with_this_frame_int': [
                TerminatingLoopToken(1, done_with_this_frame_descr_int)
                ],
            'loop_tokens_done_with_this_frame_ref': [
                TerminatingLoopToken(1, done_with_this_frame_descr_ref)
                ],
            'loop_tokens_done_with_this_frame_float': [
                TerminatingLoopToken(1, done_with_this_frame_descr_float)
                ],
            'loop_tokens_done_with_this_frame_void': [
                TerminatingLoopToken(0, done_with_this_frame_descr_void)
                ],
            'loop_tokens_exit_frame_with_exception_ref': [
                TerminatingLoopToken(1, exit_frame_with_exception_descr_ref)
                ],
    }
    d.update(locals())
    return d

class ResumeDescr(AbstractFailDescr):
    pass

class ResumeGuardDescr(ResumeDescr):
    _counter = 0        # on a GUARD_VALUE, there is one counter per value;
    _counters = None    # they get stored in _counters then.

    # this class also gets the following attributes stored by resume.py code

    # XXX move all of unused stuff to guard_op, now that we can have
    #     a separate class, so it does not survive that long
    rd_snapshot = None
    rd_frame_info_list = None
    rd_numb = lltype.nullptr(NUMBERING)
    rd_count = 0
    rd_consts = None
    rd_virtuals = None
    rd_pendingfields = lltype.nullptr(PENDINGFIELDSP.TO)

    CNT_BASE_MASK  =  0x0FFFFFFF     # the base counter value
    CNT_BUSY_FLAG  =  0x10000000     # if set, busy tracing from the guard
    CNT_TYPE_MASK  =  0x60000000     # mask for the type

    CNT_INT        =  0x20000000
    CNT_REF        =  0x40000000
    CNT_FLOAT      =  0x60000000

    def store_final_boxes(self, guard_op, boxes):
        guard_op.setfailargs(boxes)
        self.rd_count = len(boxes)
        self.guard_opnum = guard_op.getopnum()

    def make_a_counter_per_value(self, guard_value_op):
        assert guard_value_op.getopnum() == rop.GUARD_VALUE
        box = guard_value_op.getarg(0)
        try:
            i = guard_value_op.getfailargs().index(box)
        except ValueError:
            return     # xxx probably very rare
        else:
            if i > self.CNT_BASE_MASK:
                return    # probably never, but better safe than sorry
            if box.type == history.INT:
                cnt = self.CNT_INT
            elif box.type == history.REF:
                cnt = self.CNT_REF
            elif box.type == history.FLOAT:
                cnt = self.CNT_FLOAT
            else:
                assert 0, box.type
            assert cnt > self.CNT_BASE_MASK
            self._counter = cnt | i

    def handle_fail(self, deadframe, metainterp_sd, jitdriver_sd):
        if self.must_compile(deadframe, metainterp_sd, jitdriver_sd):
            self.start_compiling()
            try:
                self._trace_and_compile_from_bridge(deadframe, metainterp_sd,
                                                    jitdriver_sd)
            finally:
                self.done_compiling()
        else:
            from rpython.jit.metainterp.blackhole import resume_in_blackhole
            resume_in_blackhole(metainterp_sd, jitdriver_sd, self, deadframe)
        assert 0, "unreachable"

    def _trace_and_compile_from_bridge(self, deadframe, metainterp_sd,
                                       jitdriver_sd):
        # 'jitdriver_sd' corresponds to the outermost one, i.e. the one
        # of the jit_merge_point where we started the loop, even if the
        # loop itself may contain temporarily recursion into other
        # jitdrivers.
        from rpython.jit.metainterp.pyjitpl import MetaInterp
        metainterp = MetaInterp(metainterp_sd, jitdriver_sd)
        metainterp.handle_guard_failure(self, deadframe)
    _trace_and_compile_from_bridge._dont_inline_ = True

    def must_compile(self, deadframe, metainterp_sd, jitdriver_sd):
        trace_eagerness = jitdriver_sd.warmstate.trace_eagerness
        #
        if self._counter <= self.CNT_BASE_MASK:
            # simple case: just counting from 0 to trace_eagerness
            self._counter += 1
            return self._counter >= trace_eagerness
        #
        # do we have the BUSY flag?  If so, we're tracing right now, e.g. in an
        # outer invocation of the same function, so don't trace again for now.
        elif self._counter & self.CNT_BUSY_FLAG:
            return False
        #
        else: # we have a GUARD_VALUE that fails.  Make a _counters instance
            # (only now, when the guard is actually failing at least once),
            # and use it to record some statistics about the failing values.
            index = self._counter & self.CNT_BASE_MASK
            typetag = self._counter & self.CNT_TYPE_MASK
            counters = self._counters
            if typetag == self.CNT_INT:
                intvalue = metainterp_sd.cpu.get_int_value(
                    deadframe, index)
                if counters is None:
                    self._counters = counters = ResumeGuardCountersInt()
                else:
                    assert isinstance(counters, ResumeGuardCountersInt)
                counter = counters.see_int(intvalue)
            elif typetag == self.CNT_REF:
                refvalue = metainterp_sd.cpu.get_ref_value(
                    deadframe, index)
                if counters is None:
                    self._counters = counters = ResumeGuardCountersRef()
                else:
                    assert isinstance(counters, ResumeGuardCountersRef)
                counter = counters.see_ref(refvalue)
            elif typetag == self.CNT_FLOAT:
                floatvalue = metainterp_sd.cpu.get_float_value(
                    deadframe, index)
                if counters is None:
                    self._counters = counters = ResumeGuardCountersFloat()
                else:
                    assert isinstance(counters, ResumeGuardCountersFloat)
                counter = counters.see_float(floatvalue)
            else:
                assert 0, typetag
            return counter >= trace_eagerness

    def start_compiling(self):
        # start tracing and compiling from this guard.
        self._counter |= self.CNT_BUSY_FLAG

    def done_compiling(self):
        # done tracing and compiling from this guard.  Either the bridge has
        # been successfully compiled, in which case whatever value we store
        # in self._counter will not be seen any more, or not, in which case
        # we should reset the counter to 0, in order to wait a bit until the
        # next attempt.
        if self._counter >= 0:
            self._counter = 0
        self._counters = None

    def compile_and_attach(self, metainterp, new_loop):
        # We managed to create a bridge.  Attach the new operations
        # to the corresponding guard_op and compile from there
        assert metainterp.resumekey_original_loop_token is not None
        new_loop.original_jitcell_token = metainterp.resumekey_original_loop_token
        inputargs = metainterp.history.inputargs
        if not we_are_translated():
            self._debug_suboperations = new_loop.operations
        propagate_original_jitcell_token(new_loop)
        send_bridge_to_backend(metainterp.jitdriver_sd, metainterp.staticdata,
                               self, inputargs, new_loop.operations,
                               new_loop.original_jitcell_token)

    def copy_all_attributes_into(self, res):
        # XXX a bit ugly to have to list them all here
        res.rd_snapshot = self.rd_snapshot
        res.rd_frame_info_list = self.rd_frame_info_list
        res.rd_numb = self.rd_numb
        res.rd_consts = self.rd_consts
        res.rd_virtuals = self.rd_virtuals
        res.rd_pendingfields = self.rd_pendingfields
        res.rd_count = self.rd_count

    def _clone_if_mutable(self):
        res = ResumeGuardDescr()
        self.copy_all_attributes_into(res)
        return res

class ResumeGuardNotInvalidated(ResumeGuardDescr):
    def _clone_if_mutable(self):
        res = ResumeGuardNotInvalidated()
        self.copy_all_attributes_into(res)
        return res

class ResumeAtPositionDescr(ResumeGuardDescr):
    def _clone_if_mutable(self):
        res = ResumeAtPositionDescr()
        self.copy_all_attributes_into(res)
        return res

class AllVirtuals:
    llopaque = True
    cache = None

    def __init__(self, cache):
        self.cache = cache

    def hide(self, cpu):
        ptr = cpu.ts.cast_instance_to_base_ref(self)
        return cpu.ts.cast_to_ref(ptr)

    @staticmethod
    def show(cpu, gcref):
        from rpython.rtyper.annlowlevel import cast_base_ptr_to_instance
        ptr = cpu.ts.cast_to_baseclass(gcref)
        return cast_base_ptr_to_instance(AllVirtuals, ptr)


class ResumeGuardForcedDescr(ResumeGuardDescr):

    def __init__(self, metainterp_sd, jitdriver_sd):
        self.metainterp_sd = metainterp_sd
        self.jitdriver_sd = jitdriver_sd

    def handle_fail(self, deadframe, metainterp_sd, jitdriver_sd):
        # Failures of a GUARD_NOT_FORCED are never compiled, but
        # always just blackholed.  First fish for the data saved when
        # the virtualrefs and virtualizable have been forced by
        # handle_async_forcing() just a moment ago.
        from rpython.jit.metainterp.blackhole import resume_in_blackhole
        hidden_all_virtuals = metainterp_sd.cpu.get_savedata_ref(deadframe)
        obj = AllVirtuals.show(metainterp_sd.cpu, hidden_all_virtuals)
        all_virtuals = obj.cache
        if all_virtuals is None:
            all_virtuals = ResumeDataDirectReader.VirtualCache([], [])
        assert jitdriver_sd is self.jitdriver_sd
        resume_in_blackhole(metainterp_sd, jitdriver_sd, self, deadframe,
                            all_virtuals)
        assert 0, "unreachable"

    @staticmethod
    @dont_look_inside
    def force_now(cpu, token):
        # Called during a residual call from the assembler, if the code
        # actually needs to force one of the virtualrefs or the virtualizable.
        # Implemented by forcing *all* virtualrefs and the virtualizable.

        # don't interrupt me! If the stack runs out in force_from_resumedata()
        # then we have seen cpu.force() but not self.save_data(), leaving in
        # an inconsistent state
        rstack._stack_criticalcode_start()
        try:
            deadframe = cpu.force(token)
            # this should set descr to ResumeGuardForceDescr, if it
            # was not that already
            faildescr = cpu.get_latest_descr(deadframe)
            assert isinstance(faildescr, ResumeGuardForcedDescr)
            faildescr.handle_async_forcing(deadframe)
        finally:
            rstack._stack_criticalcode_stop()

    def handle_async_forcing(self, deadframe):
        from rpython.jit.metainterp.resume import (force_from_resumedata,
                                                   AlreadyForced)
        metainterp_sd = self.metainterp_sd
        vinfo = self.jitdriver_sd.virtualizable_info
        ginfo = self.jitdriver_sd.greenfield_info
        # there is some chance that this is already forced. In this case
        # the virtualizable would have a token = NULL
        try:
            all_virtuals = force_from_resumedata(metainterp_sd, self, deadframe,
                                                 vinfo, ginfo)
        except AlreadyForced:
            return
        # The virtualizable data was stored on the real virtualizable above.
        # Handle all_virtuals: keep them for later blackholing from the
        # future failure of the GUARD_NOT_FORCED
        obj = AllVirtuals(all_virtuals)
        hidden_all_virtuals = obj.hide(metainterp_sd.cpu)
        metainterp_sd.cpu.set_savedata_ref(deadframe, hidden_all_virtuals)

    def _clone_if_mutable(self):
        res = ResumeGuardForcedDescr(self.metainterp_sd,
                                     self.jitdriver_sd)
        self.copy_all_attributes_into(res)
        return res


class AbstractResumeGuardCounters(object):
    # Completely custom algorithm for now: keep 5 pairs (value, counter),
    # and when we need more, we discard the middle pair (middle in the
    # current value of the counter).  That way, we tend to keep the
    # values with a high counter, but also we avoid always throwing away
    # the most recently added value.  **THIS ALGO MUST GO AWAY AT SOME POINT**
    pass

def _see(self, newvalue):
    # find and update an existing counter
    unused = -1
    for i in range(5):
        cnt = self.counters[i]
        if cnt:
            if self.values[i] == newvalue:
                cnt += 1
                self.counters[i] = cnt
                return cnt
        else:
            unused = i
    # not found.  Use a previously unused entry, if there is one
    if unused >= 0:
        self.counters[unused] = 1
        self.values[unused] = newvalue
        return 1
    # no unused entry.  Overwrite the middle one.  Computed with indices
    # a, b, c meaning the highest, second highest, and third highest
    # entries.
    a = 0
    b = c = -1
    for i in range(1, 5):
        if self.counters[i] > self.counters[a]:
            c = b
            b = a
            a = i
        elif b < 0 or self.counters[i] > self.counters[b]:
            c = b
            b = i
        elif c < 0 or self.counters[i] > self.counters[c]:
            c = i
    self.counters[c] = 1
    self.values[c] = newvalue
    return 1

class ResumeGuardCountersInt(AbstractResumeGuardCounters):
    def __init__(self):
        self.counters = [0] * 5
        self.values = [0] * 5
    see_int = func_with_new_name(_see, 'see_int')

class ResumeGuardCountersRef(AbstractResumeGuardCounters):
    def __init__(self):
        self.counters = [0] * 5
        self.values = [history.ConstPtr.value] * 5
    see_ref = func_with_new_name(_see, 'see_ref')

class ResumeGuardCountersFloat(AbstractResumeGuardCounters):
    def __init__(self):
        self.counters = [0] * 5
        self.values = [longlong.ZEROF] * 5
    see_float = func_with_new_name(_see, 'see_float')


class ResumeFromInterpDescr(ResumeDescr):
    def __init__(self, original_greenkey):
        self.original_greenkey = original_greenkey

    def compile_and_attach(self, metainterp, new_loop):
        # We managed to create a bridge going from the interpreter
        # to previously-compiled code.  We keep 'new_loop', which is not
        # a loop at all but ends in a jump to the target loop.  It starts
        # with completely unoptimized arguments, as in the interpreter.
        metainterp_sd = metainterp.staticdata
        jitdriver_sd = metainterp.jitdriver_sd
        new_loop.original_jitcell_token = jitcell_token = make_jitcell_token(jitdriver_sd)
        propagate_original_jitcell_token(new_loop)
        send_loop_to_backend(self.original_greenkey, metainterp.jitdriver_sd,
                             metainterp_sd, new_loop, "entry bridge")
        # send the new_loop to warmspot.py, to be called directly the next time
        jitdriver_sd.warmstate.attach_procedure_to_interp(
            self.original_greenkey, jitcell_token)
        metainterp_sd.stats.add_jitcell_token(jitcell_token)


def compile_trace(metainterp, resumekey, resume_at_jump_descr=None):
    """Try to compile a new bridge leading from the beginning of the history
    to some existing place.
    """
    from rpython.jit.metainterp.optimizeopt import optimize_trace

    # The history contains new operations to attach as the code for the
    # failure of 'resumekey.guard_op'.
    #
    # Attempt to use optimize_bridge().  This may return None in case
    # it does not work -- i.e. none of the existing old_loop_tokens match.
    new_trace = create_empty_loop(metainterp)
    new_trace.inputargs = metainterp.history.inputargs[:]
    # clone ops, as optimize_bridge can mutate the ops

    new_trace.operations = [op.clone() for op in metainterp.history.operations]
    new_trace.resume_at_jump_descr = resume_at_jump_descr
    metainterp_sd = metainterp.staticdata
    state = metainterp.jitdriver_sd.warmstate
    if isinstance(resumekey, ResumeAtPositionDescr):
        inline_short_preamble = False
    else:
        inline_short_preamble = True
    try:
        optimize_trace(metainterp_sd, new_trace, state.enable_opts, inline_short_preamble)
    except InvalidLoop:
        debug_print("compile_new_bridge: got an InvalidLoop")
        # XXX I am fairly convinced that optimize_bridge cannot actually raise
        # InvalidLoop
        debug_print('InvalidLoop in compile_new_bridge')
        return None

    if new_trace.operations[-1].getopnum() != rop.LABEL:
        # We managed to create a bridge.  Dispatch to resumekey to
        # know exactly what we must do (ResumeGuardDescr/ResumeFromInterpDescr)
        target_token = new_trace.operations[-1].getdescr()
        resumekey.compile_and_attach(metainterp, new_trace)
        record_loop_or_bridge(metainterp_sd, new_trace)
        return target_token
    else:
        metainterp.retrace_needed(new_trace)
        return None

# ____________________________________________________________

memory_error = MemoryError()

class PropagateExceptionDescr(AbstractFailDescr):
    def handle_fail(self, deadframe, metainterp_sd, jitdriver_sd):
        cpu = metainterp_sd.cpu
        exception = cpu.grab_exc_value(deadframe)
        if not exception:
            exception = cast_instance_to_gcref(memory_error)
        assert exception, "PropagateExceptionDescr: no exception??"
        raise jitexc.ExitFrameWithExceptionRef(cpu, exception)

def compile_tmp_callback(cpu, jitdriver_sd, greenboxes, redargtypes,
                         memory_manager=None):
    """Make a LoopToken that corresponds to assembler code that just
    calls back the interpreter.  Used temporarily: a fully compiled
    version of the code may end up replacing it.
    """
    jitcell_token = make_jitcell_token(jitdriver_sd)
    nb_red_args = jitdriver_sd.num_red_args
    assert len(redargtypes) == nb_red_args
    inputargs = []
    for kind in redargtypes:
        if kind == history.INT:
            box = BoxInt()
        elif kind == history.REF:
            box = BoxPtr()
        elif kind == history.FLOAT:
            box = BoxFloat()
        else:
            raise AssertionError
        inputargs.append(box)
    k = jitdriver_sd.portal_runner_adr
    funcbox = history.ConstInt(heaptracker.adr2int(k))
    callargs = [funcbox] + greenboxes + inputargs
    #
    result_type = jitdriver_sd.result_type
    if result_type == history.INT:
        result = BoxInt()
    elif result_type == history.REF:
        result = BoxPtr()
    elif result_type == history.FLOAT:
        result = BoxFloat()
    elif result_type == history.VOID:
        result = None
    else:
        assert 0, "bad result_type"
    if result is not None:
        finishargs = [result]
    else:
        finishargs = []
    #
    jd = jitdriver_sd
    faildescr = jitdriver_sd.propagate_exc_descr
    operations = [
        ResOperation(rop.CALL, callargs, result, descr=jd.portal_calldescr),
        ResOperation(rop.GUARD_NO_EXCEPTION, [], None, descr=faildescr),
        ResOperation(rop.FINISH, finishargs, None, descr=jd.portal_finishtoken)
    ]
    operations[1].setfailargs([])
    operations = get_deep_immutable_oplist(operations)
    cpu.compile_loop(inputargs, operations, jitcell_token, log=False)
    if memory_manager is not None:    # for tests
        memory_manager.keep_loop_alive(jitcell_token)
    return jitcell_token
