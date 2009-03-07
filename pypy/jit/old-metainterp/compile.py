
from pypy.rpython.ootypesystem import ootype
from pypy.objspace.flow.model import Constant, Variable
from pypy.rlib.objectmodel import we_are_translated
from pypy.conftest import option

from pypy.jit.metainterp.history import Graph, Jump, log, Box
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
    try:
        try:
            loop = compile_fresh_loop(metainterp, loop, old_loops,
                                      endliveboxes)
        except Exception, exc:
            show_loop(metainterp, loop, loop.operations[0], exc)
            raise
        else:
            show_loop(metainterp, loop, loop.operations[0], None)
    except optimize.CancelInefficientLoop:
        return None
    loop.check_consistency()
    return loop

def _compile_new_bridge_1(metainterp, bridge, old_loops, endliveboxes):
    try:
        try:
            bridge = compile_fresh_bridge(metainterp, bridge, old_loops,
                                          endliveboxes)
        except Exception, exc:
            show_loop(metainterp, bridge, None, exc)
            raise
        else:
            show_loop(metainterp, bridge, None, None)
    except optimize.CancelInefficientLoop:
        return None
    if bridge is not None:
        bridge.check_consistency()
    return bridge

def show_loop(metainterp, loop, mp=None, error=None):
    # debugging
    if option.view:
        if error:
            errmsg = error.__class__.__name__
            if str(error):
                errmsg += ': ' + str(error)
        else:
            errmsg = None
        loop.show(in_stats=metainterp.stats, errmsg=errmsg,
                  highlightops=find_highlight_ops(metainterp.history, mp))

def find_highlight_ops(history, mp=None):
    result = {}
    for op in history.operations[::-1]:
        result[op] = True
        if op is mp:
            break
    return result

def create_empty_loop(metainterp):
    if we_are_translated():
        name = 'Loop'
    else:
        name = 'Loop #%d' % len(metainterp.stats.loops)
    graph = Graph(name, '#f084c2')
    return graph

def create_empty_bridge(metainterp):
    if we_are_translated():
        name = 'Bridge'
    else:
        name = 'Bridge #%d' % len(metainterp.stats.loops)
    graph = Graph(name, '#84f0c2')
    return graph

# ____________________________________________________________

def compile_fresh_loop(metainterp, loop, old_loops, endliveboxes):
    history = metainterp.history
    loop.operations = history.operations
    close_loop(loop, loop.operations[0], endliveboxes)
    old_loop = optimize.optimize_loop(metainterp.options, old_loops, loop)
    if old_loop is not None:
        return old_loop
    finish_loop_or_bridge(metainterp, loop, loop.operations[0])
    old_loops.append(loop)
    return loop

def close_loop(loop, targetmp, endliveboxes):
    assert targetmp.opname == 'merge_point'
    op = Jump('jump', endliveboxes, [])
    op.jump_target = targetmp
    loop.operations.append(op)

def finish_loop_or_bridge(metainterp, loop, targetmp, guard_op=None):
    assert targetmp.opname == 'merge_point'
    assert loop.operations[-1].opname == 'jump'
    loop.operations[-1].jump_target = targetmp
    metainterp.cpu.compile_operations(loop.operations, guard_op)
    metainterp.stats.loops.append(loop)

# ____________________________________________________________

def matching_merge_point(metainterp, targetmp, endliveboxes):
    return True

def compile_fresh_bridge(metainterp, bridge, old_loops, endliveboxes):
    history = metainterp.history
    catch_op = history.operations[0]
    assert catch_op.opname == 'catch'
    guard_op = catch_op.coming_from
    assert guard_op.opname.startswith('guard_')
    #
    operations = bridge.operations = history.operations
    op = Jump('jump', endliveboxes, [])
    operations.append(op)
    #
    old_loop = optimize.optimize_bridge(metainterp.options, old_loops, bridge)
    if old_loop is None:
        return None
    bridge.jump_to = old_loop
    finish_loop_or_bridge(metainterp, bridge, old_loop.operations[0], guard_op)
    return bridge
