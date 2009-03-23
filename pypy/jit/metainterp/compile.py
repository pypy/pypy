
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

def compile_new_bridge(metainterp, old_loops, endliveboxes):
    """Try to compile a new bridge leading from the beginning of the history
    to some existing place.
    """
    bridge = create_empty_bridge(metainterp)
    if we_are_translated():
        try:
            bridge = compile_fresh_bridge(metainterp, bridge, old_loops,
                                          endliveboxes)
            return bridge
        except optimize.CancelInefficientLoop:
            return None
    else:
        return _compile_new_bridge_1(metainterp, bridge, old_loops,
                                     endliveboxes)

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

def _compile_new_bridge_1(metainterp, bridge, old_loops, endliveboxes):
    orgbridge = bridge
    try:
        try:
            bridge = compile_fresh_bridge(metainterp, bridge, old_loops,
                                          endliveboxes)
        except Exception, exc:
            show_loop(metainterp, bridge, error=exc)
            raise
        else:
            if bridge == orgbridge:
                show_loop(metainterp, bridge)
            elif bridge is not None:
                log.info("reusing bridge at %r" % (bridge,))
            else:
                log.info("compile_fresh_bridge() returned None")
    except optimize.CancelInefficientLoop:
        return None
    if bridge is not None:
        bridge.check_consistency()
    return bridge

def show_loop(metainterp, loop, error=None):
    # debugging
    if option.view:
        if error:
            errmsg = error.__class__.__name__
            if str(error):
                errmsg += ': ' + str(error)
        else:
            errmsg = None
        loop.show(errmsg=errmsg)

def create_empty_loop(metainterp):
    if we_are_translated():
        name = 'Loop'
    else:
        name = 'Loop #%d' % len(metainterp.stats.loops)
    return Loop(name)

# ____________________________________________________________

def compile_fresh_loop(metainterp, loop, old_loops, endliveboxes):
    history = metainterp.history
    loop.inputargs = history.inputargs
    loop.operations = history.operations
    close_loop(loop, endliveboxes)
    old_loop = optimize.optimize_loop(metainterp.options, old_loops, loop,
                                      metainterp.cpu)
    if old_loop is not None:
        return old_loop
    send_loop_to_backend(metainterp, loop)
    old_loops.append(loop)
    return loop

def close_loop(loop, endliveboxes):
    op = ResOperation(rop.JUMP, endliveboxes, None)
    op.jump_target = loop
    loop.operations.append(op)

def send_loop_to_backend(metainterp, loop):
    metainterp.cpu.compile_operations(loop)
    metainterp.stats.loops.append(loop)

# ____________________________________________________________

def matching_merge_point(metainterp, targetmp, endliveboxes):
    return True

def compile_fresh_bridge(metainterp, bridge, old_loops, endliveboxes):
    history = metainterp.history
    catch_op = history.operations[0]
    assert catch_op.opnum == rop.CATCH
    guard_op = catch_op.coming_from
    assert guard_op.is_guard()
    #
    operations = bridge.operations = history.operations
    op = ResOperation(rop.JUMP, endliveboxes, None)
    operations.append(op)
    #
    old_loop = optimize.optimize_bridge(metainterp.options, old_loops, bridge,
                                        metainterp.cpu)
    if old_loop is None:
        return None
    bridge.jump_to = old_loop
    finish_loop_or_bridge(metainterp, bridge, old_loop.operations[0], guard_op)
    return bridge
