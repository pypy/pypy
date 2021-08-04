from rpython.rtyper.lltypesystem.llmemory import AddressAsInt
from rpython.rlib.rjitlog import rjitlog as jl
from rpython.rlib.objectmodel import specialize, we_are_translated
from rpython.jit.metainterp.history import (
    ConstInt, ConstFloat, RefFrontendOp, IntFrontendOp, FloatFrontendOp)
from rpython.jit.metainterp import compile, jitprof, history
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

from pprint import pprint

class mark(object):
    JUMP = "emit_jump"
    RET = "emit_ret"

class TraceSplitInfo(BasicLoopInfo):
    """ A state after splitting the trace, containing the following:

    * target_token - generated target token for a bridge ("false" branch)
    * label_op - label operations
    """
    def __init__(self, target_token, label_op, inputargs,
                 quasi_immutable_deps, fail_descr=None):
        self.target_token = target_token
        self.label_op = label_op
        self.inputargs = inputargs
        self.quasi_immutable_deps = quasi_immutable_deps
        self.fail_descr = fail_descr

    def final(self):
        return True

class TraceSplitOpt(object):

    def __init__(self, metainterp_sd, jitdriver_sd, optimizations=None,
                 resumekey=None, split_at=None, guard_at=None):
        self.metainterp_sd = metainterp_sd
        self.jitdriver_sd = jitdriver_sd
        self.optimizations = optimizations
        self.resumekey = resumekey
        self.split_at = split_at
        self.guard_at = guard_at

    def split(self, trace, oplist, inputs, body_token, bridge_token):
        """ For threaded code: splitting the given oplist into the two --
        the body and bridge oplists.
        """
        cut_at = 0
        last_op = None
        newops = []
        pseudo_ops = []
        for i in range(len(oplist)):
            op = oplist[i]
            if op.getopnum() in (rop.CALL_I, rop.CALL_R, rop.CALL_F, rop.CALL_N):
                arg = op.getarg(0)
                name = self._get_name_from_arg(arg)
                assert name is not None

                if name.find(self.split_at) != -1:
                    # recording pseudo operations like call_i(ConstClass(emit_jump), ..)
                    # or call_i(ConstClass(emit_ret) ..) to remove guard operations
                    # for checking this pseudo op
                    pseudo_ops.append(op)
                    if self.split_at.find("jump"):
                        last_op = ResOperation(rop.JUMP, inputs, body_token)
                        cut_at = i
                else:
                    newops.append(op)
            elif op.is_guard():
                can_be_recorded = True
                for arg in op.getarglist():
                    if arg in pseudo_ops:
                        can_be_recorded = False
                        break
                if can_be_recorded:
                    newops.append(op)
            else:
                newops.append(op)

        assert last_op is not None

        ops_body = newops[:cut_at] + [last_op]
        ops_bridge = newops[cut_at:]

        ops_body, ops_bridge, inputs_bridge, descr_to_attach = self.invent_failargs(
            inputs, ops_body, ops_bridge, bridge_token)

        # ops_bridge = self.copy_from_body_to_bridge(ops_body, ops_bridge)

        body_label = ResOperation(rop.LABEL, inputs, descr=body_token)
        bridge_label = ResOperation(rop.LABE4L, inputs_bridge, descr=bridge_token)

        return (TraceSplitInfo(body_token, body_label, inputs, None, descr_to_attach), ops_body), \
            (TraceSplitInfo(bridge_token, bridge_label, inputs_bridge, None, None), ops_bridge)

    def split_ops(self, trace, oplist, inputs, body_token):
        data = self.find_cut_points_with_ops(trace, oplist, inputs, body_token)
        splitted = []

        split_range = []
        keys = data.keys()
        for i in range(len(keys)):
            if i == 0:
                split_range.append((-1, keys[i]))
            else:
                split_range.append((keys[i-1], keys[i]))
        split_range.append((keys[-1], len(oplist)))

        for (key_p, key_c) in split_range:
            if split_range.index((key_p, key_c)) == len(split_range) - 1:
                res = oplist[key_p+1:key_c+1]
            else:
                ops = oplist[key_p+1:key_c+1]
                del ops[-1]
                mark, invented_ops = data.get(key_c)
                res = ops + invented_ops
            splitted.append(res)

        return splitted

    def find_cut_points_with_ops(self, trace, oplist, inputargs, body_token):
        dic = {}
        for i in range(len(oplist)):
            op = oplist[i]
            if op.getopnum() in (rop.CALL_I, rop.CALL_N, rop.CALL_F, rop.CALL_N):
                arg = op.getarg(0)
                name = self._get_name_from_arg(arg)
                assert name is not None

                if name.find(mark.JUMP) != -1:
                    jump_op = ResOperation(rop.JUMP, inputargs, body_token)
                    dic[i] = (mark.JUMP, [jump_op])
                elif name.find(mark.RET) != -1:
                    jd_no = self.jitdriver_sd.index
                    result_type = self.jitdriver_sd.result_type
                    sd = self.metainterp_sd
                    if result_type == history.VOID:
                        exits = []
                        token = sd.done_with_this_frame_descr_void
                    elif result_type == history.INT:
                        exits = [op.getarg(2)]
                        token = sd.done_with_this_frame_descr_int
                    elif result_type == history.REF:
                        exits = [op.getarg(2)]
                        token = sd.done_with_this_frame_descr_ref
                    elif result_type == history.FLOAT:
                        exits = [op.getarg(2)]
                        token = sd.done_with_this_frame_descr_float
                    else:
                        assert False

                    # host-stack style
                    ret_ops = [
                        ResOperation(rop.LEAVE_PORTAL_FRAME, [ConstInt(jd_no)], None),
                        ResOperation(rop.FINISH, exits, token)
                    ]

                    dic[i] = (mark.RET, ret_ops)
        return dic

    def invent_failargs(self, inputs, ops_body, ops_bridge, bridge_token):
        newops_body, newops_bridge, inputs_bridge = [], [], []
        descr_to_attach = None
        for i in range(len(ops_body)):
            op = ops_body[i]
            if op.is_guard():
                arg = op.getarg(0)
                if self._has_marker(ops_body, arg, self.guard_at):
                    # setting up inputargs for the bridge_ops
                    failargs = op.getfailargs()
                    descr_to_attach = op.getdescr()
                    inputs_bridge, new_failargs, newops_bridge = self._invent_failargs(
                        inputs, ops_bridge, failargs)
                    op.setfailargs(new_failargs)
                    ops_body[i] = op
                    break
        return ops_body, newops_bridge, inputs_bridge, descr_to_attach

    def _invent_failargs(self, inputs, oplist, failargs):
        newfargs = []
        for arg in failargs:
            for i in range(len(oplist)):
                op = oplist[i]
                oparglist = op.getarglist()
                if arg in oparglist:
                    if arg not in newfargs:
                        newfargs.append(arg)

        assert len(newfargs) == len(inputs)

        for farg, input in zip(newfargs, inputs):
            for op in oplist:
                args = op.getarglist()
                if farg in args:
                    i = args.index(farg)
                    op.setarg(i, input)
                    n = oplist.index(op)
                    oplist[n] = op

        return inputs, newfargs, oplist

    def copy_from_body_to_bridge(self, ops_body, ops_bridge):

        def copy_transitively(oplist, arg, res=[]):
            for op in oplist:
                if op == arg:
                    res.append(op)
                    for arg in op.getarglist():
                        copy_transitively(oplist, arg, res)
            return res

        l = []
        for op in ops_bridge:
            args = op.getarglist()
            for arg in args:
                if arg in ops_body:
                    l = copy_transitively(ops_body, arg)

        return l + ops_bridge

    def _has_op(self, op1, oplist):
        for op2 in oplist:
            if op1 in op2.getarglist():
                return True
        return False

    def _get_name_from_arg(self, arg):
        marker = self.metainterp_sd
        box = arg.getvalue()
        if isinstance(box, AddressAsInt):
            return str(box.adr.ptr)
        else:
            return self.metainterp_sd.get_name_from_address(box)

    def _has_marker(self, oplist, arg, marker):
        metainterp_sd = self.metainterp_sd
        for op in oplist:
            if op == arg:
                call_to = op.getarg(0)
                name = self._get_name_from_arg(call_to)
                if name.find(marker) != -1:
                    return True
        return False


class OptTraceSplit(Optimization):

    def __init__(self, metainterp_sd, jitdriver_sd):
        Optimizer.__init__(self, metainterp_sd, jitdriver_sd)
        self.split_at = None
        self.guard_at = None
        self.body_ops = []
        self.bridge_ops = []


dispatch_opt = make_dispatcher_method(OptTraceSplit, 'optimize_',
                                      default=OptTraceSplit.emit)
OptTraceSplit.propagate_forward = dispatch_opt
