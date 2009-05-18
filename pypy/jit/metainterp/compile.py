
from pypy.rpython.ootypesystem import ootype
from pypy.objspace.flow.model import Constant, Variable
from pypy.rlib.objectmodel import we_are_translated
from pypy.conftest import option

from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.metainterp.history import TreeLoop, log, Box, History
from pypy.jit.metainterp.history import AbstractDescr, BoxInt, BoxPtr, BoxObj,\
     Const
from pypy.jit.metainterp import history
from pypy.jit.metainterp.specnode import NotSpecNode
from pypy.rlib.debug import debug_print

def compile_new_loop(metainterp, old_loops, greenkey, start=0):
    """Try to compile a new loop by closing the current history back
    to the first operation.
    """
    if we_are_translated():
        return compile_fresh_loop(metainterp, old_loops, greenkey, start)
    else:
        return _compile_new_loop_1(metainterp, old_loops, greenkey, start)

def compile_new_bridge(metainterp, old_loops, resumekey):
    """Try to compile a new bridge leading from the beginning of the history
    to some existing place.
    """
    if we_are_translated():
        return compile_fresh_bridge(metainterp, old_loops, resumekey)
    else:
        return _compile_new_bridge_1(metainterp, old_loops, resumekey)

class BridgeInProgress(Exception):
    pass


# the following is not translatable
def _compile_new_loop_1(metainterp, old_loops, greenkey, start):
    old_loops_1 = old_loops[:]
    try:
        loop = compile_fresh_loop(metainterp, old_loops, greenkey, start)
    except Exception, exc:
        show_loop(metainterp, error=exc)
        raise
    else:
        if loop in old_loops_1:
            log.info("reusing loop at %r" % (loop,))
        else:
            show_loop(metainterp, loop)
    loop.check_consistency()
    return loop

def _compile_new_bridge_1(metainterp, old_loops, resumekey):
    try:
        target_loop = compile_fresh_bridge(metainterp, old_loops,
                                           resumekey)
    except Exception, exc:
        show_loop(metainterp, error=exc)
        raise
    else:
        if target_loop is not None:
            show_loop(metainterp, target_loop)
    if target_loop is not None and type(target_loop) is not TerminatingLoop:
        target_loop.check_consistency()
    return target_loop

def show_loop(metainterp, loop=None, error=None):
    # debugging
    if option.view:
        if error:
            errmsg = error.__class__.__name__
            if str(error):
                errmsg += ': ' + str(error)
        else:
            errmsg = None
        if loop is None or type(loop) is TerminatingLoop:
            extraloops = []
        else:
            extraloops = [loop]
        metainterp.staticdata.stats.view(errmsg=errmsg, extraloops=extraloops)

def create_empty_loop(metainterp):
    if we_are_translated():
        name = 'Loop'
    else:
        name = 'Loop #%d' % len(metainterp.staticdata.stats.loops)
    return TreeLoop(name)

# ____________________________________________________________

def compile_fresh_loop(metainterp, old_loops, greenkey, start):
    from pypy.jit.metainterp.pyjitpl import DEBUG

    history = metainterp.history
    loop = create_empty_loop(metainterp)
    loop.greenkey = greenkey
    loop.inputargs = history.inputargs
    if start > 0:
        loop.operations = history.operations[start:]
    else:
        loop.operations = history.operations
    loop.operations[-1].jump_target = loop
    metainterp_sd = metainterp.staticdata
    old_loop = metainterp_sd.optimize_loop(metainterp_sd.options, old_loops,
                                           loop, metainterp.cpu)
    if old_loop is not None:
        if we_are_translated() and DEBUG > 0:
            debug_print("reusing old loop")
        return old_loop
    history.source_link = loop
    send_loop_to_backend(metainterp, loop, "loop")
    metainterp.staticdata.stats.loops.append(loop)
    old_loops.append(loop)
    return loop

def send_loop_to_backend(metainterp, loop, type):
    metainterp.staticdata.profiler.start_backend()
    metainterp.cpu.compile_operations(loop)
    metainterp.staticdata.profiler.end_backend()
    if not we_are_translated():
        if type != "entry bridge":
            metainterp.staticdata.stats.compiled_count += 1
        else:
            loop._ignore_during_counting = True
        log.info("compiled new " + type)
    else:
        from pypy.jit.metainterp.pyjitpl import DEBUG
        if DEBUG > 0:
            debug_print("compiled new " + type)

# ____________________________________________________________

class DoneWithThisFrameDescrVoid(AbstractDescr):
    def handle_fail_op(self, metainterp_sd, fail_op):
        assert metainterp_sd.result_type == 'void'
        raise metainterp_sd.DoneWithThisFrameVoid()

class DoneWithThisFrameDescrInt(AbstractDescr):
    def handle_fail_op(self, metainterp_sd, fail_op):
        assert metainterp_sd.result_type == 'int'
        resultbox = fail_op.args[0]
        if isinstance(resultbox, BoxInt):
            result = metainterp_sd.cpu.get_latest_value_int(0)
        else:
            assert isinstance(resultbox, history.Const)
            result = resultbox.getint()
        raise metainterp_sd.DoneWithThisFrameInt(result)

class DoneWithThisFrameDescrPtr(AbstractDescr):
    def handle_fail_op(self, metainterp_sd, fail_op):
        assert metainterp_sd.result_type == 'ptr'
        resultbox = fail_op.args[0]
        if isinstance(resultbox, BoxPtr):
            result = metainterp_sd.cpu.get_latest_value_ptr(0)
        else:
            assert isinstance(resultbox, history.Const)
            result = resultbox.getptr_base()
        raise metainterp_sd.DoneWithThisFramePtr(result)

class DoneWithThisFrameDescrObj(AbstractDescr):
    def handle_fail_op(self, metainterp_sd, fail_op):
        assert metainterp_sd.result_type == 'obj'
        resultbox = fail_op.args[0]
        if isinstance(resultbox, BoxObj):
            result = metainterp_sd.cpu.get_latest_value_obj(0)
        else:
            assert isinstance(resultbox, history.Const)
            result = resultbox.getobj()
        raise metainterp_sd.DoneWithThisFrameObj(result)

class ExitFrameWithExceptionDescrPtr(AbstractDescr):
    def handle_fail_op(self, metainterp_sd, fail_op):
        assert len(fail_op.args) == 1
        valuebox = fail_op.args[0]
        if isinstance(valuebox, BoxPtr):
            value = metainterp_sd.cpu.get_latest_value_ptr(0)
        else:
            assert isinstance(valuebox, history.Const)
            value = valuebox.getptr_base()
        raise metainterp_sd.ExitFrameWithExceptionPtr(value)

class ExitFrameWithExceptionDescrObj(AbstractDescr):
    def handle_fail_op(self, metainterp_sd, fail_op):
        assert len(fail_op.args) == 1
        valuebox = fail_op.args[0]
        if isinstance(valuebox, BoxObj):
            value = metainterp_sd.cpu.get_latest_value_obj(0)
        else:
            assert isinstance(valuebox, history.Const)
            value = valuebox.getobj()
        raise metainterp_sd.ExitFrameWithExceptionObj(value)

done_with_this_frame_descr_void = DoneWithThisFrameDescrVoid()
done_with_this_frame_descr_int = DoneWithThisFrameDescrInt()
done_with_this_frame_descr_ptr = DoneWithThisFrameDescrPtr()
done_with_this_frame_descr_obj = DoneWithThisFrameDescrObj()
exit_frame_with_exception_descr_ptr = ExitFrameWithExceptionDescrPtr()
exit_frame_with_exception_descr_obj = ExitFrameWithExceptionDescrObj()

class TerminatingLoop(TreeLoop):
    pass

# pseudo-loops to make the life of optimize.py easier
_loop = TerminatingLoop('done_with_this_frame_int')
_loop.specnodes = [NotSpecNode()]
_loop.inputargs = [BoxInt()]
_loop.finishdescr = done_with_this_frame_descr_int
loops_done_with_this_frame_int = [_loop]

_loop = TerminatingLoop('done_with_this_frame_ptr')
_loop.specnodes = [NotSpecNode()]
_loop.inputargs = [BoxPtr()]
_loop.finishdescr = done_with_this_frame_descr_ptr
loops_done_with_this_frame_ptr = [_loop]

_loop = TerminatingLoop('done_with_this_frame_obj')
_loop.specnodes = [NotSpecNode()]
_loop.inputargs = [BoxObj()]
_loop.finishdescr = done_with_this_frame_descr_obj
loops_done_with_this_frame_obj = [_loop]

_loop = TerminatingLoop('done_with_this_frame_void')
_loop.specnodes = []
_loop.inputargs = []
_loop.finishdescr = done_with_this_frame_descr_void
loops_done_with_this_frame_void = [_loop]

_loop = TerminatingLoop('exit_frame_with_exception_ptr')
_loop.specnodes = [NotSpecNode()]
_loop.inputargs = [BoxPtr()]
_loop.finishdescr = exit_frame_with_exception_descr_ptr
loops_exit_frame_with_exception_ptr = [_loop]

_loop = TerminatingLoop('exit_frame_with_exception_obj')
_loop.specnodes = [NotSpecNode()]
_loop.inputargs = [BoxObj()]
_loop.finishdescr = exit_frame_with_exception_descr_obj
loops_exit_frame_with_exception_obj = [_loop]
del _loop


class ResumeGuardDescr(AbstractDescr):
    def __init__(self, resume_info, consts, history, history_guard_index):
        self.resume_info = resume_info
        self.counter = 0
        self.history = history
        assert history_guard_index >= 0
        self.history_guard_index = history_guard_index
        self.consts = consts

    def handle_fail_op(self, metainterp_sd, fail_op):
        from pypy.jit.metainterp.pyjitpl import MetaInterp
        metainterp = MetaInterp(metainterp_sd)
        patch = self.patch_boxes_temporarily(metainterp_sd, fail_op)
        try:
            return metainterp.handle_guard_failure(fail_op, self)
        finally:
            self.restore_patched_boxes(metainterp_sd, fail_op, patch)

    def patch_boxes_temporarily(self, metainterp_sd, fail_op):
        # A bit indirect: when we hit a rop.FAIL, the current values are
        # stored somewhere in the CPU backend.  Below we fetch them and
        # copy them into the real boxes, i.e. the 'fail_op.args'.  We
        # are in a try:finally path at the end of which, in
        # restore_patched_boxes(), we can safely undo exactly the
        # changes done here.
        cpu = metainterp_sd.cpu
        patch = []
        for i in range(len(fail_op.args)):
            box = fail_op.args[i]
            patch.append(box.clonebox())
            if isinstance(box, BoxInt):
                srcvalue = cpu.get_latest_value_int(i)
                box.changevalue_int(srcvalue)
            elif isinstance(box, BoxPtr):
                srcvalue = cpu.get_latest_value_ptr(i)
                box.changevalue_ptr(srcvalue)
            elif cpu.is_oo and isinstance(box, BoxObj):
                srcvalue = cpu.get_latest_value_obj(i)
                box.changevalue_obj(srcvalue)
            elif isinstance(box, Const):
                pass # we don't need to do anything
            else:
                assert False
        return patch

    def restore_patched_boxes(self, metainterp_sd, fail_op, patch):
        for i in range(len(patch)-1, -1, -1):
            srcbox = patch[i]
            dstbox = fail_op.args[i]
            if isinstance(dstbox, BoxInt):
                dstbox.changevalue_int(srcbox.getint())
            elif isinstance(dstbox, BoxPtr):
                dstbox.changevalue_ptr(srcbox.getptr_base())
            elif isinstance(dstbox, Const):
                pass
            elif metainterp_sd.cpu.is_oo and isinstance(dstbox, BoxObj):
                dstbox.changevalue_obj(srcbox.getobj())
            else:
                assert False

    def get_guard_op(self):
        guard_op = self.history.operations[self.history_guard_index]
        assert guard_op.is_guard()
        if guard_op.optimized is not None:   # should always be the case,
            return guard_op.optimized        # except if not optimizing at all
        else:
            return guard_op

    def compile_and_attach(self, metainterp, new_loop):
        # We managed to create a bridge.  Attach the new operations
        # to the existing source_loop and recompile the whole thing.
        source_loop = self.find_source_loop()
        metainterp.history.source_link = self.history
        metainterp.history.source_guard_index = self.history_guard_index
        guard_op = self.get_guard_op()
        guard_op.suboperations = new_loop.operations
        send_loop_to_backend(metainterp, source_loop, "bridge")

    def find_source_loop(self):
        # Find the TreeLoop object that contains this guard operation.
        source_loop = self.history.source_link
        while not isinstance(source_loop, TreeLoop):
            source_loop = source_loop.source_link
        return source_loop

    def find_toplevel_history(self):
        # Find the History that describes the start of the loop containing this
        # guard operation.
        history = self.history
        prevhistory = history.source_link
        while isinstance(prevhistory, History):
            history = prevhistory
            prevhistory = history.source_link
        return history


class ResumeFromInterpDescr(AbstractDescr):
    def __init__(self, original_boxes):
        self.original_boxes = original_boxes

    def compile_and_attach(self, metainterp, new_loop):
        # We managed to create a bridge going from the interpreter
        # to previously-compiled code.  We keep 'new_loop', which is not
        # a loop at all but ends in a jump to the target loop.  It starts
        # with completely unoptimized arguments, as in the interpreter.
        metainterp_sd = metainterp.staticdata
        num_green_args = metainterp_sd.num_green_args
        greenkey = self.original_boxes[:num_green_args]
        redkey = self.original_boxes[num_green_args:]
        metainterp.history.source_link = new_loop
        metainterp.history.inputargs = redkey
        new_loop.greenkey = greenkey
        new_loop.inputargs = redkey
        send_loop_to_backend(metainterp, new_loop, "entry bridge")
        metainterp_sd.stats.loops.append(new_loop)
        # send the new_loop to warmspot.py, to be called directly the next time
        metainterp_sd.state.attach_unoptimized_bridge_from_interp(greenkey,
                                                                  new_loop)
        # store the new_loop in compiled_merge_points too
        # XXX it's probably useless to do so when optimizing
        glob = metainterp_sd.globaldata
        greenargs = glob.unpack_greenkey(greenkey)
        old_loops = glob.compiled_merge_points.setdefault(greenargs, [])
        old_loops.append(new_loop)


def compile_fresh_bridge(metainterp, old_loops, resumekey):
    # The history contains new operations to attach as the code for the
    # failure of 'resumekey.guard_op'.
    #
    # Attempt to use optimize_bridge().  This may return None in case
    # it does not work -- i.e. none of the existing old_loops match.
    new_loop = create_empty_loop(metainterp)
    new_loop.operations = metainterp.history.operations
    metainterp_sd = metainterp.staticdata
    target_loop = metainterp_sd.optimize_bridge(metainterp_sd.options,
                                                old_loops, new_loop,
                                                metainterp.cpu)
    # Did it work?  If not, prepare_loop_from_bridge() will probably be used.
    if target_loop is not None:
        # Yes, we managed to create a bridge.  Dispatch to resumekey to
        # know exactly what we must do (ResumeGuardDescr/ResumeFromInterpDescr)
        prepare_last_operation(new_loop, target_loop)
        resumekey.compile_and_attach(metainterp, new_loop)
    return target_loop

def prepare_last_operation(new_loop, target_loop):
    op = new_loop.operations[-1]
    if not isinstance(target_loop, TerminatingLoop):
        # normal case
        op.jump_target = target_loop
    else:
        # The target_loop is a pseudo-loop, e.g. done_with_this_frame.
        # Replace the operation with the real operation we want, i.e. a FAIL.
        descr = target_loop.finishdescr
        new_op = ResOperation(rop.FAIL, op.args, None, descr=descr)
        new_loop.operations[-1] = new_op


def prepare_loop_from_bridge(metainterp, resumekey):
    # To handle this case, we prepend to the history the unoptimized
    # operations coming from the loop, in order to make a (fake) complete
    # unoptimized trace.  (Then we will just compile this loop normally.)
    raise PrepareLoopFromBridgeIsDisabled
    if not we_are_translated():
        log.info("completing the bridge into a stand-alone loop")
    else:
        debug_print("completing the bridge into a stand-alone loop")
    operations = metainterp.history.operations
    metainterp.history.operations = []
    assert isinstance(resumekey, ResumeGuardDescr)
    append_full_operations(metainterp.history,
                           resumekey.history,
                           resumekey.history_guard_index)
    metainterp.history.operations.extend(operations)

def append_full_operations(history, sourcehistory, guard_index):
    prev = sourcehistory.source_link
    if isinstance(prev, History):
        append_full_operations(history, prev, sourcehistory.source_guard_index)
    history.operations.extend(sourcehistory.operations[:guard_index])
    op = inverse_guard(sourcehistory.operations[guard_index])
    history.operations.append(op)

def inverse_guard(guard_op):
    suboperations = guard_op.suboperations
    assert guard_op.is_guard()
    if guard_op.opnum == rop.GUARD_TRUE:
        guard_op = ResOperation(rop.GUARD_FALSE, guard_op.args, None)
    elif guard_op.opnum == rop.GUARD_FALSE:
        guard_op = ResOperation(rop.GUARD_TRUE, guard_op.args, None)
    else:
        # XXX other guards have no inverse so far
        raise InverseTheOtherGuardsPlease(guard_op)
    #
    guard_op.suboperations = suboperations
    return guard_op

class InverseTheOtherGuardsPlease(Exception):
    pass

class PrepareLoopFromBridgeIsDisabled(Exception):
    pass
