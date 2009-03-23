
from pypy.rpython.ootypesystem import ootype
from pypy.objspace.flow.model import Constant, Variable
from pypy.rlib.objectmodel import we_are_translated
from pypy.conftest import option

from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.metainterp.history import Loop, log, Box
from pypy.jit.metainterp import optimize


def compile_new_loop(metainterp, old_loops, endliveboxes):
    """Try to compile a new loop by closing the current history back
    to the first operation.
    """
    loop = create_empty_loop(metainterp)
    if we_are_translated():
        try:
            loop = compile_fresh_loop(metainterp, loop, old_loops,
                                      endliveboxes)
            return loop
        except optimize.CancelInefficientLoop:
            return None
    else:
        return _compile_new_loop_1(metainterp, loop, old_loops, endliveboxes)

def compile_new_bridge(metainterp, old_loops, endliveboxes, resumekey):
    """Try to compile a new bridge leading from the beginning of the history
    to some existing place.
    """
    if we_are_translated():
        try:
            target_loop = compile_fresh_bridge(metainterp, old_loops,
                                               endliveboxes, resumekey)
            return target_loop
        except optimize.CancelInefficientLoop:
            return None
    else:
        return _compile_new_bridge_1(metainterp, old_loops,
                                     endliveboxes, resumekey)

class BridgeInProgress(Exception):
    pass


# the following is not translatable
def _compile_new_loop_1(metainterp, loop, old_loops, endliveboxes):
    orgloop = loop
    try:
        try:
            loop = compile_fresh_loop(metainterp, loop, old_loops,
                                      endliveboxes)
        except Exception, exc:
            show_loop(metainterp, loop, error=exc)
            raise
        else:
            if loop == orgloop:
                show_loop(metainterp, loop)
            else:
                log.info("reusing loop at %r" % (loop,))
    except optimize.CancelInefficientLoop:
        return None
    loop.check_consistency()
    return loop

def _compile_new_bridge_1(metainterp, old_loops, endliveboxes, resumekey):
    try:
        try:
            target_loop = compile_fresh_bridge(metainterp, old_loops,
                                               endliveboxes, resumekey)
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
    return Loop(name)

# ____________________________________________________________

def compile_fresh_loop(metainterp, loop, old_loops, endliveboxes):
    # ---<temporary>---
    if old_loops:
        return old_loops[0]
    # ---</temporary>---
    history = metainterp.history
    loop.inputargs = history.inputargs
    loop.operations = history.operations
    close_loop(loop, endliveboxes)
    #old_loop = optimize.optimize_loop(metainterp.options, old_loops, loop,
    #                                  metainterp.cpu)
    #if old_loop is not None:
    #    return old_loop
    mark_keys_in_loop(loop, loop.operations)
    send_loop_to_backend(metainterp, loop)
    metainterp.stats.loops.append(loop)
    old_loops.append(loop)
    return loop

def close_loop(loop, endliveboxes):
    op = ResOperation(rop.JUMP, endliveboxes, None)
    op.jump_target = loop
    loop.operations.append(op)

def mark_keys_in_loop(loop, operations):
    op = None
    for op in operations:
        if op.is_guard():
            mark_keys_in_loop(loop, op.suboperations)
    if op.opnum == rop.FAIL:
        op.key.loop = loop

def send_loop_to_backend(metainterp, loop):
    metainterp.cpu.compile_operations(loop)

# ____________________________________________________________

def matching_merge_point(metainterp, targetmp, endliveboxes):
    return True

def compile_fresh_bridge(metainterp, old_loops, endliveboxes, resumekey):
    history = metainterp.history
    #
    op = ResOperation(rop.JUMP, endliveboxes, None)
    history.operations.append(op)
    #
    #old_loop = optimize.optimize_bridge(metainterp.options, old_loops, bridge,
    #                                    metainterp.cpu)
    #if old_loop is None:
    #    return None
    # ---<temporary>---
    target_loop = old_loops[0]
    op.jump_target = target_loop
    # ---</temporary>---
    source_loop = resumekey.loop
    guard_op = resumekey.guard_op
    guard_op.suboperations = history.operations
    mark_keys_in_loop(source_loop, guard_op.suboperations)
    send_loop_to_backend(metainterp, source_loop)
    return target_loop
