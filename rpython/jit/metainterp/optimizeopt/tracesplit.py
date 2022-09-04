from rpython.jit.metainterp.optimize import InvalidLoop
from rpython.rlib.debug import debug_print
from rpython.rtyper.lltypesystem.llmemory import AddressAsInt
from rpython.rlib.rjitlog import rjitlog as jl
from rpython.rlib.rstring import find, endswith
from rpython.rlib.objectmodel import specialize, we_are_translated, r_dict
from rpython.jit.metainterp.history import (
    ConstInt, ConstFloat, RefFrontendOp, IntFrontendOp, FloatFrontendOp, INT, REF, FLOAT, VOID)
from rpython.jit.metainterp import compile, jitprof, history
from rpython.jit.metainterp.history import TargetToken
from rpython.jit.metainterp.optimizeopt.optimizer import (
    Optimizer, Optimization, BasicLoopInfo)
from rpython.jit.metainterp.optimizeopt.intutils import (
    IntBound, ConstIntBound, MININT, MAXINT, IntUnbounded)
from rpython.jit.metainterp.optimizeopt.bridgeopt import (
    deserialize_optimizer_knowledge)
from rpython.jit.metainterp.optimizeopt.util import make_dispatcher_method
from rpython.jit.metainterp.opencoder import Trace, TraceIterator
from rpython.jit.metainterp.resoperation import (
    rop, OpHelpers, ResOperation, InputArgRef, InputArgInt,
    InputArgFloat, InputArgVector, GuardResOp)

class TokenMapError(Exception):
    """Raised when KeyError happens at taking a TargetToken from token_map"""
    def __init__(self, key=None,
                 message="KeyError happens when taking token from token_map"):
        self.key = key
        self.message = message
        if key is not None:
            self.message = "%s, key is %d" % (message, key)

class mark(object):
    JUMP = "emit_jump"
    RET = "emit_ret"
    IS_TRUE = "is_true"
    CALL_ASSEMBLER = "CALL_ASSEMBLER"

    IS_TRUE_OBJECT = "_is_true_object"
    IS_FALSE_OBJECT = "_is_false_object"

    @staticmethod
    def is_cond_object(name):
        return name.find(mark.IS_TRUE_OBJECT) != -1 or \
            name.find(mark.IS_FALSE_OBJECT) != -1

    @staticmethod
    def is_pseudo_jump(name):
        return name.find(mark.JUMP) != -1

    @staticmethod
    def is_pseudo_ret(name):
        return name.find(mark.RET) != -1

    @staticmethod
    def is_pseudo_op(name):
        return name.find(mark.JUMP) != -1 or name.find(mark.RET) != -1

class TraceSplitInfo(BasicLoopInfo):
    """ A state after splitting the trace, containing the following:

    * target_token - generated target token for a bridge ("false" branch)
    * label_op - label operations
    * inputargs - input arguments
    * faildescr - used in the case of a bridge trace; for attaching
    """
    def __init__(self, target_token, label_op, inputargs, faildescr=None):
        self.target_token = target_token
        self.label_op = label_op
        self.inputargs = inputargs
        self.faildescr = faildescr

    def final(self):
        return True

    def __copy__(self, target_token, label_op, inputargs, faildescr=None):
        return TraceSplitInfo(target_token, label_op, inputargs, faildescr)

    def set_token(self, target_token):
        self.target_token = target_token

    def set_label(self, label_op):
        self.label_op = label_op

    def set_inputargs(self, inputargs):
        self.inputargs = inputargs

    def set_faildescr(self, faildescr):
        self.faildescr = faildescr

class OptTraceSplit(Optimizer):

    def __init__(self, metainterp_sd, jitdriver_sd,
                 optimizations=None, resumekey=None):
        Optimizer.__init__(self, metainterp_sd, jitdriver_sd)
        self.metainterp_sd = metainterp_sd
        self.jitdriver_sd = jitdriver_sd
        self.trace = None
        self.optimizations = optimizations
        self.resumekey = resumekey

        self.inputargs = None
        self.token = None
        self.token_map = {}

        self._pseudoops = []
        self._specialguardop = []
        self._newopsandinfo = []
        self._fdescrstack = []

        self.set_optimizations(optimizations)
        self.setup()

    def split(self, trace, resumestorage, call_pure_results, token):
        traceiter = trace.get_iter()
        self.token = token
        self.propagate_all_forward(traceiter, call_pure_results)
        return self._newopsandinfo

    def propagate_all_forward(self, trace, call_pure_results=None, flush=True):
        self.trace = trace
        deadranges = trace.get_dead_ranges()
        self.inputargs = trace.inputargs
        self.call_pure_results = call_pure_results
        last_op = None
        i = 0

        self.emit(ResOperation(rop.LABEL, self.inputargs, self.token))

        already_setup_current_token = False
        while not trace.done():
            self._really_emitted_operation = None
            op = trace.next()
            opnum = op.getopnum()

            # remove real ops related to pseudo ops
            can_emit = True
            for arg in op.getarglist():
                if arg in self._pseudoops:
                    can_emit = False
                    self.emit_pseudoop(op)
                    break

            if not can_emit:
                continue

            if not already_setup_current_token and \
               opnum == rop.DEBUG_MERGE_POINT:
                arglist = op.getarglist()
                # TODO: look up `pc' by name
                if self.jitdriver_sd.num_red_args < 3:
                    greens = arglist[3:]
                else:
                    greens = arglist[self.jitdriver_sd.num_red_args:]
                box = greens[0]
                assert isinstance(box, ConstInt)
                self.token_map[box.getint()] = self.token
                already_setup_current_token = True

            if opnum in (rop.FINISH, rop.JUMP):
                last_op = op
                break

            # shallow tracing: turn on flags
            if rop.is_plain_call(opnum) or rop.is_call_may_force(opnum):
                numargs = op.numargs()
                lastarg = op.getarg(numargs - 1)
                if isinstance(lastarg, ConstInt) and lastarg.getint() == 1:
                    op.setarg(numargs - 1, ConstInt(0))

            self.send_extra_operation(op)
            trace.kill_cache_at(deadranges[i + trace.start_index])
            if op.type != 'v':
                i += 1

        # accumulate counters
        if flush:
            self.flush()
            if last_op:
                self.send_extra_operation(last_op)

        if len(self._newoperations) and \
           self._newoperations[-1].getopnum() in (rop.JUMP, rop.FINISH):
            token = self._create_token(self.token)
            label = ResOperation(rop.LABEL, self.inputargs, token)
            info = TraceSplitInfo(token, label, self.inputargs, self.resumekey)
            self._newopsandinfo.append((info, self._newoperations))

        self.resumedata_memo.update_counters(self.metainterp_sd.profiler)
        # XXX: workaround to pass the type checking
        return self._newopsandinfo[0]

    def emit_pseudoop(self, op):
        self._pseudoops.append(op)

    def propagate_forward(self, op):
        dispatch_opt(self, op)

    def optimize_GUARD_VALUE(self, op):
        self.emit(op)
        if self._is_guard_marked(op, mark.IS_TRUE) or \
           self._is_guard_marked(op, mark.IS_TRUE_OBJECT) or \
           self._is_guard_marked(op, mark.IS_FALSE_OBJECT):
            newfailargs = []
            for farg in op.getfailargs():
                if not farg in self._specialguardop:
                    newfailargs.append(farg)

            op.setfailargs(newfailargs)
            self._fdescrstack.append(op.getdescr())

    optimize_GUARD_TRUE = optimize_GUARD_VALUE
    optimize_GUARD_FALSE = optimize_GUARD_VALUE

    def optimize_CALL_N(self, op):
        arg0 = op.getarg(0)
        name = self._get_name_from_arg(arg0)
        if endswith(name, mark.JUMP):
            self.emit_pseudoop(op)
            self.handle_emit_jump(op)
        elif endswith(name, mark.RET):
            self.emit_pseudoop(op)
            self.handle_emit_ret(op)
        elif endswith(name, mark.IS_TRUE) or \
             endswith(name, mark.IS_TRUE_OBJECT) or \
             endswith(name, mark.IS_FALSE_OBJECT):
            self._specialguardop.append(op)
            self.emit(op)
        else:
            self.emit(op)

    def optimize_CALL_MAY_FORCE_R(self, op):
        arg0 = op.getarg(0)
        name = self._get_name_from_arg(arg0)
        if endswith(name, mark.CALL_ASSEMBLER):
            self.handle_call_assembler(op)
        else:
            self.emit(op)

    optimize_CALL_I = optimize_CALL_N
    optimize_CALL_F = optimize_CALL_N
    optimize_CALL_R = optimize_CALL_N

    def handle_emit_ret(self, op, emit_label=True):
        inputargs = self.inputargs
        jd_no = self.jitdriver_sd.index
        result_type = self.jitdriver_sd.result_type
        sd = self.metainterp_sd
        if result_type == history.VOID:
            exits = []
            finishtoken = sd.done_with_this_frame_descr_void
        elif result_type == history.INT:
            exits = [op.getarg(2)]
            finishtoken = sd.done_with_this_frame_descr_int
        elif result_type == history.REF:
            exits = [op.getarg(2)]
            finishtoken = sd.done_with_this_frame_descr_ref
        elif result_type == history.FLOAT:
            exits = [op.getarg(2)]
            finishtoken = sd.done_with_this_frame_descr_float
        else:
            assert False

        # host-stack style
        ret_ops = [
            ResOperation(rop.LEAVE_PORTAL_FRAME, [ConstInt(jd_no)], None),
            ResOperation(rop.FINISH, exits, finishtoken)
        ]

        currentbox = op.getarg(1)
        assert isinstance(currentbox, ConstInt)
        target_token = self._create_token(self.token)

        label_op, residual_ops = self._newoperations[0], self._newoperations[1:]
        info = TraceSplitInfo(target_token, label_op, inputargs, self.resumekey)
        self._newopsandinfo.append((info, residual_ops + ret_ops))
        self._newoperations = []

        next_token = self._create_token(self.token)
        self.token_map[currentbox.getint()] = next_token

        if emit_label:
            self.emit(ResOperation(rop.LABEL, inputargs, next_token))
        if len(self._fdescrstack) > 0:
            self.resumekey = self._fdescrstack.pop()

    def handle_emit_jump(self, op, emit_label=True):
        # backward jump
        inputargs = self.inputargs
        currentbox, targetbox = op.getarg(1), op.getarg(2)
        assert isinstance(currentbox, ConstInt)
        assert isinstance(targetbox, ConstInt)

        key = targetbox.getint()
        try:
            target_token = self.get_from_token_map(key)
        except TokenMapError as e:
            debug_print("Token is not found at " + str(key))
            raise InvalidLoop

        jump_op = ResOperation(rop.JUMP, inputargs, target_token)
        label_op, residual_ops = self._newoperations[0], self._newoperations[1:]
        info = TraceSplitInfo(target_token, label_op, inputargs, self.resumekey)
        self._newoperations = []

        next_token = self._create_token(self.token)
        self.token_map[currentbox.getint()] = next_token

        self._newopsandinfo.append((info, residual_ops + [jump_op]))
        if emit_label:
            self.emit(ResOperation(rop.LABEL, inputargs, next_token))
        if len(self._fdescrstack) > 0:
            self.resumekey = self._fdescrstack.pop()

    def handle_call_assembler(self, op):
        # a hack to convert recursive calls to an op using `call_assembler_x'
        jd = self.jitdriver_sd

        arglist = op.getarglist()
        num_green_args = jd.num_green_args
        num_red_args = jd.num_red_args
        greenargs = arglist[1+num_red_args:1+num_red_args+num_green_args]
        args = arglist[1:num_red_args+1]

        warmrunnerstate = jd.warmstate
        new_token = warmrunnerstate.get_assembler_token(greenargs)
        opnum = OpHelpers.call_assembler_for_descr(op.getdescr())
        newop = op.copy_and_change(opnum, args, new_token)
        op.set_forwarded(newop)
        self.emit(newop)

    def get_from_token_map(self, key):
        if self.token_map is None:
            raise Exception("token_map is None")

        try:
            return self.token_map[key]
        except KeyError:
            raise TokenMapError(key=key)

    def _create_token(self, token):
        if len(self._newopsandinfo) > 0:
            jitcell_token = compile.make_jitcell_token(self.jitdriver_sd)
            original_jitcell_token = token.original_jitcell_token
            return TargetToken(jitcell_token,
                               original_jitcell_token=original_jitcell_token)
        else:
            return token

    def _get_name_from_arg(self, arg):
        if isinstance(arg, ConstInt):
            addr = arg.getaddr()
            res = self.metainterp_sd.get_name_from_address(addr)
            if res:
                return res

        # TODO: explore more precise way
        return ''

    def _is_guard_marked(self, op, mark):
        "Check if the guard_op is marked"
        assert op.is_guard()
        failargs = op.getarglist()
        for op in self._newoperations:
            opnum = op.getopnum()
            if rop.is_plain_call(opnum) or rop.is_call_may_force(opnum):
                if op in failargs:
                    name = self._get_name_from_arg(op.getarg(0))
                    if name is None:
                        return False
                    else:
                        return name.find(mark) != -1
        return False

class TraceSplitOpt(object):

    def __init__(self, metainterp_sd, jitdriver_sd,
                 optimizations=None, resumekey=None):
        self.metainterp_sd = metainterp_sd
        self.jitdriver_sd = jitdriver_sd
        self.optimizations = optimizations
        self.resumekey = resumekey
        self.first_cut = True

        self._newopsandinfo = []
        self._token_map = None

    def split_ops(self, trace, token):
        "Threaded code: splitting the given ops into several op lists"

        residual_ops = []         # store ops temporarily
        pseudo_ops = []           # for removing useless guards
        fdescr_stack = []         # for bridges

        oplist = trace._ops

        oplist = self.remove_ops_assoc_pseudo_op(oplist)
        self.token_map = self.create_token_dic(oplist, token)

        label_op = ResOperation(rop.LABEL, inputargs, token)
        residual_ops.append(label_op)

        if oplist[0].getopnum() == rop.DEBUG_MERGE_POINT:
            arglist = oplist[0].getarglist()
            greens = arglist[2+self.jitdriver_sd.num_red_args:]
            # pc is in the first
            box = greens[0]
            assert isinstance(box, ConstInt)
            self.token_map[box.getint()] = token

        opindex = 0
        while opindex < len(oplist):
            op = oplist[opindex]
            opindex += 1

            opnum = op.getopnum()
            if op.is_guard():
                failargs = op.getfailargs()
                if self._is_guard_marked(op, oplist, mark.IS_TRUE):
                    descr = op.getdescr()
                    fdescr_stack.append(descr)
                    newfailargs = []
                    for farg in failargs:
                        if not farg in pseudo_ops:
                            newfailargs.append(farg)
                    op.setfailargs(newfailargs)

                residual_ops.append(op)
            elif rop.is_plain_call(opnum) or rop.is_call_may_force(opnum):
                name = self._get_name_from_arg(op.getarg(0))
                numargs = op.numargs()
                lastarg = op.getarg(numargs - 1)
                if isinstance(lastarg, ConstInt) and lastarg.getint() == 1:
                    op.setarg(numargs - 1, ConstInt(0))
                if endswith(name, mark.JUMP):
                    pseudo_ops.append(op)
                    current, target = op.getarg(1), op.getarg(2)
                    assert isinstance(current, ConstInt)
                    assert isinstance(target, ConstInt)
                    target_token = self.get_from_token_map(target.getint())

                    jump_op = ResOperation(rop.JUMP, inputargs, target_token)
                    label_op, residual_ops = residual_ops[0], residual_ops[1:]
                    info = TraceSplitInfo(target_token, label_op, inputargs, self.resumekey)

                    next_token = self.get_from_token_map(current.getint())
                    self._newopsandinfo.append((info, residual_ops + [jump_op]))
                    # t_lst.append((info, residual_ops + [jump_op]))
                    residual_ops = [ResOperation(rop.LABEL, inputargs, next_token)]
                    if len(fdescr_stack) > 0:
                        self.resumekey = fdescr_stack.pop()
                elif endswith(name, mark.RET):
                    pseudo_ops.append(op)
                    jd_no = self.jitdriver_sd.index
                    result_type = self.jitdriver_sd.result_type
                    sd = self.metainterp_sd
                    if result_type == history.VOID:
                        exits = []
                        finishtoken = sd.done_with_this_frame_descr_void
                    elif result_type == history.INT:
                        exits = [op.getarg(2)]
                        finishtoken = sd.done_with_this_frame_descr_int
                    elif result_type == history.REF:
                        exits = [op.getarg(2)]
                        finishtoken = sd.done_with_this_frame_descr_ref
                    elif result_type == history.FLOAT:
                        exits = [op.getarg(2)]
                        finishtoken = sd.done_with_this_frame_descr_float
                    else:
                        assert False

                    # host-stack style
                    ret_ops = [
                        ResOperation(rop.LEAVE_PORTAL_FRAME, [ConstInt(jd_no)], None),
                        ResOperation(rop.FINISH, exits, finishtoken)
                    ]

                    current = op.getarg(1)
                    assert isinstance(current, ConstInt)
                    target_token = self._create_token(token)

                    label_op, residual_ops = residual_ops[0], residual_ops[1:]
                    info = TraceSplitInfo(target_token, label_op, inputargs,
                                          self.resumekey)
                    self._newopsandinfo.append((info, residual_ops + ret_ops))
                    # t_lst.append((info, residual_ops + ret_ops))

                    next_token = self.get_from_token_map(currejnt.getint())
                    residual_ops = [ResOperation(rop.LABEL, inputargs, next_token)]
                    if len(fdescr_stack) > 0:
                        self.resumekey = fdescr_stack.pop()
                elif endswith(name, mark.IS_TRUE):
                    pseudo_ops.append(op)
                    residual_ops.append(op)
                elif endswith(name, mark.CALL_ASSEMBLER):
                    # a hack to convert recursive calls to an op using `call_assembler_x'
                    pseudo_ops.append(op)
                    jd = self.jitdriver_sd

                    arglist = op.getarglist()
                    num_green_args = jd.num_green_args
                    num_red_args = jd.num_red_args
                    greenargs = arglist[1+num_red_args:1+num_red_args+num_green_args]
                    args = arglist[1:num_red_args+1]

                    warmrunnerstate = jd.warmstate
                    new_token = warmrunnerstate.get_assembler_token(greenargs)
                    opnum = OpHelpers.call_assembler_for_descr(op.getdescr())
                    newop = op.copy_and_change(opnum, args, new_token)
                    oplist = self._change_call_op(newop, op, oplist, opindex)
                    residual_ops.append(newop)
                else:
                    residual_ops.append(op)
            elif op.getopnum() == rop.FINISH:
                target_token = self._create_token(token)

                label = ResOperation(rop.LABEL, inputargs, target_token)
                info = TraceSplitInfo(target_token, label, inputargs, self.resumekey)
                residual_ops.append(op)

                # t_lst.append((info, residual_ops))
                residual_ops = []
                break
            elif op.getopnum() == rop.JUMP:
                target_token = self._create_token(token)
                label = ResOperation(rop.LABEL, inputargs, target_token)
                info = TraceSplitInfo(target_token, label, inputargs,
                                      faildescr=self.resumekey)
                residual_ops.append(op)
                self._newopsandinfo.append((info, residual_ops))
                residual_ops = []
                break
            else:
                residual_ops.append(op)


        _, body_ops = self._newopsandinfo[0]
        for i, (newinfo, newops) in enumerate(self._newopsandinfo[1:]):
            new_bridge_ops = self.copy_from_body_to_bridge(body_ops, newops)
            self._newopsandinfo[i+1] = newinfo, new_bridge_ops

        return self._newopsandinfo

    def get_from_token_map(self, key):
        if self.token_map is None:
            raise Exception("token_map is None")

        try:
            return self.token_map[key]
        except KeyError:
            raise TokenMapError(key=key)

    def create_token_dic(self, ops, orig_token):
        def myeq(x, y):
            return x == y

        def myhash(n):
            if n < 0:
                raise Exception
            else:
                return -n

        token_map = r_dict(myeq, myhash)

        for op in ops:
            opnum = op.getopnum()
            if rop.is_call(opnum):
                arg = op.getarg(0)
                name = self._get_name_from_arg(arg)
                if endswith(name, mark.JUMP):
                    nextbox, targetbox = op.getarg(1), op.getarg(2)
                    assert isinstance(nextbox, ConstInt)
                    assert isinstance(targetbox, ConstInt)
                    next, target = nextbox.getint(), targetbox.getint()
                    if target not in token_map:
                        token_map[target] = self._create_token(orig_token)
                    if next not in token_map:
                        token_map[next] = self._create_token(orig_token)
                elif endswith(name, mark.RET):
                    targetbox, retvalbox = op.getarg(1), op.getarg(2)
                    assert isinstance(targetbox, ConstInt)
                    target = targetbox.getint()
                    if target not in token_map:
                        token_map[target] = self._create_token(orig_token)

        return token_map

    def _create_token(self, token):
        if len(self._newopsandinfo):
            jitcell_token = compile.make_jitcell_token(self.jitdriver_sd)
            original_jitcell_token = token.original_jitcell_token
            return TargetToken(jitcell_token,
                               original_jitcell_token=original_jitcell_token)
        else:
            return token

    def remove_ops_assoc_pseudo_op(self, oplist):
        "Remove guard_ops assosiated with pseudo ops"
        pseudo_ops = []
        for op in oplist:
            if self._is_pseudo_op(op):
                pseudo_ops.append(op)

        newops = []
        for op in oplist:
            can_be_recorded = True
            args = op.getarglist()
            for arg in args:
                if arg in pseudo_ops:
                    can_be_recorded = False
                    pseudo_ops.append(op)
                    break
            if can_be_recorded:
                newops.append(op)

        return newops

    def _change_call_op(self, newcallop, oldcallop, oplist, opindex):
        assert oplist[opindex] != oldcallop
        assert opindex < len(oplist)

        newoplist = oplist[:]
        assert len(newoplist) == len(oplist)
        index = opindex
        while index < len(oplist):
            op = oplist[index]
            if op == oldcallop:
                newoplist[index] = newcallop
                continue

            numargs = op.numargs()
            for i in range(numargs):
                arg = op.getarg(i)
                if arg is oldcallop:
                    op.setarg(i, newcallop)
            if op.is_guard():
                failargs = op.getfailargs()
                newfailargs = []
                for failarg in failargs:
                    if failarg is oldcallop:
                        newfailargs.append(newcallop)
                    else:
                        newfailargs.append(failarg)
                op.setfailargs(newfailargs)
            newoplist[index] = op
            index += 1

        return newoplist

    def copy_from_body_to_bridge(self, body_ops, bridge_ops):
        l = []
        for op in bridge_ops:
            args = op.getarglist()
            for arg in args:
                if arg in body_ops:
                    l = self._copy_transitively(body_ops, arg)

        return l + bridge_ops

    def _copy_transitively(self, oplist, arg, res=[]):
        for op in oplist:
            if op == arg:
                res.append(op)
                for arg in op.getarglist():
                    self._copy_transitively(oplist, arg, res)
        return res

    def _has_op(self, op1, oplist):
        for op2 in oplist:
            if op1 in op2.getarglist():
                return True
        return False

    def _is_pseudo_op(self, op):
        opnum = op.getopnum()
        if rop.is_plain_call(opnum) or rop.is_call_may_force(opnum):
            arg = op.getarg(0)
            name = self._get_name_from_arg(arg)
            if name:
                return mark.is_pseudo_op(name)
            else:
                return False
        return False

    def _get_name_from_arg(self, arg):
        if isinstance(arg, ConstInt):
            addr = arg.getaddr()
            res = self.metainterp_sd.get_name_from_address(addr)
            if res:
                return res

        # TODO: explore more precise way
        return ''


    def _is_guard_marked(self, guard_op, ops, mark):
        "Check if the guard_op is marked"
        assert guard_op.is_guard()
        guard_args = guard_op.getarglist()
        for op in ops:
            opnum = op.getopnum()
            if rop.is_plain_call(opnum) or rop.is_call_may_force(opnum):
                if op in guard_args:
                    name = self._get_name_from_arg(op.getarg(0))
                    if name is None:
                        return False
                    else:
                        return name.find(mark) != -1
        return False

    def _has_marker(self, oplist, arg, marker):
        for op in oplist:
            if op == arg:
                call_to = op.getarg(0)
                name = self._get_name_from_arg(call_to)
                if name.find(marker) != -1:
                    return True
        return False


dispatch_opt = make_dispatcher_method(OptTraceSplit, 'optimize_',
                                      default=OptTraceSplit.emit)
OptTraceSplit.propagate_forward = dispatch_opt
