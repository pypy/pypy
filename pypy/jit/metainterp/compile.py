
from pypy.rpython.ootypesystem import ootype
from pypy.objspace.flow.model import Constant, Variable
from pypy.rlib.objectmodel import we_are_translated
from pypy.conftest import option

from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.metainterp.history import TreeLoop, log, Box
from pypy.jit.metainterp import optimize


def compile_new_loop(metainterp, old_loops):
    """Try to compile a new loop by closing the current history back
    to the first operation.
    """
    if we_are_translated():
        try:
            loop = compile_fresh_loop(metainterp, old_loops)
            return loop
        except optimize.CancelInefficientLoop:
            return None
    else:
        return _compile_new_loop_1(metainterp, old_loops)

def compile_new_bridge(metainterp, old_loops, resumekey):
    """Try to compile a new bridge leading from the beginning of the history
    to some existing place.
    """
    if we_are_translated():
        try:
            target_loop = compile_fresh_bridge(metainterp, old_loops,
                                               resumekey)
            return target_loop
        except optimize.CancelInefficientLoop:
            return None
    else:
        return _compile_new_bridge_1(metainterp, old_loops, resumekey)

class BridgeInProgress(Exception):
    pass


# the following is not translatable
def _compile_new_loop_1(metainterp, old_loops):
    try:
        old_loops_1 = old_loops[:]
        try:
            loop = compile_fresh_loop(metainterp, old_loops)
        except Exception, exc:
            show_loop(metainterp, error=exc)
            raise
        else:
            if loop in old_loops_1:
                log.info("reusing loop at %r" % (loop,))
            else:
                show_loop(metainterp, loop)
    except optimize.CancelInefficientLoop:
        return None
    loop.check_consistency()
    return loop

def _compile_new_bridge_1(metainterp, old_loops, resumekey):
    try:
        try:
            target_loop = compile_fresh_bridge(metainterp, old_loops,
                                               resumekey)
        except Exception, exc:
            show_loop(metainterp, error=exc)
            raise
        else:
            if target_loop is None:
                log.info("compile_fresh_bridge() returned None")
            else:
                show_loop(metainterp, target_loop)
    except optimize.CancelInefficientLoop:
        return None
    if target_loop is not None:
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
        if loop is None:
            metainterp.stats.view(errmsg=errmsg)
        else:
            loop.show(errmsg=errmsg)

def create_empty_loop(metainterp):
    if we_are_translated():
        name = 'Loop'
    else:
        name = 'Loop #%d' % len(metainterp.stats.loops)
    return TreeLoop(name)

# ____________________________________________________________

def compile_fresh_loop(metainterp, old_loops):
    history = metainterp.history
    old_loop = optimize.optimize_loop(metainterp.options, old_loops,
                                      history, metainterp.cpu)
    if old_loop is not None:
        return old_loop
    loop = create_empty_loop(metainterp)
    loop.inputargs = history.inputargs
    loop.specnodes = history.specnodes
    loop.operations = history.operations
    loop.operations[-1].jump_target = loop
    mark_keys_in_loop(loop, loop.operations)
    send_loop_to_backend(metainterp, loop, True)
    metainterp.stats.loops.append(loop)
    old_loops.append(loop)
    return loop

def mark_keys_in_loop(loop, operations):
    for op in operations:
        if op.is_guard():
            mark_keys_in_loop(loop, op.suboperations)
    op = operations[-1]
    if op.opnum == rop.FAIL:
        op.key.loop = loop

def send_loop_to_backend(metainterp, loop, is_loop):
    metainterp.cpu.compile_operations(loop)
    metainterp.stats.compiled_count += 1
    if not we_are_translated():
        if is_loop:
            log.info("compiling new loop")
        else:
            log.info("compiling new bridge")

# ____________________________________________________________

def update_loop(loop, spec):
    pass

def compile_fresh_bridge(metainterp, old_loops, resumekey):
    #temp = TreeLoop('temp')
    #temp.operations = metainterp.history.operations
    #metainterp.stats.view(extraloops=[temp])
    target_loop = optimize.optimize_bridge(metainterp.options, old_loops,
                                           metainterp.history, metainterp.cpu)
    if target_loop is None:
        return None
    source_loop = resumekey.loop
    guard_op = resumekey.guard_op
    guard_op.suboperations = metainterp.history.operations
    op = guard_op.suboperations[-1]
    op.jump_target = target_loop
    mark_keys_in_loop(source_loop, guard_op.suboperations)
    send_loop_to_backend(metainterp, source_loop, False)
    return target_loop
