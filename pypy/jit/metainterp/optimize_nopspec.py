
from pypy.rlib.debug import debug_start, debug_stop
from pypy.jit.metainterp.optimizeopt import optimize_loop_1, optimize_bridge_1
from pypy.jit.metainterp.optimizefindnode import PerfectSpecializationFinder
from pypy.jit.metainterp.optimizefindnode import BridgeSpecializationFinder

def optimize_loop(metainterp_sd, old_loop_tokens, loop):
    debug_start("jit-optimize")
    try:
        return _optimize_loop(metainterp_sd, old_loop_tokens, loop)
    finally:
        debug_stop("jit-optimize")

def _optimize_loop(metainterp_sd, old_loop_tokens, loop):
    cpu = metainterp_sd.cpu
    metainterp_sd.logger_noopt.log_loop(loop.inputargs, loop.operations)
    finder = PerfectSpecializationFinder(cpu)
    finder.find_nodes_loop(loop, False)
    if old_loop_tokens:
        return old_loop_tokens[0]
    optimize_loop_1(metainterp_sd, loop)
    return None

def optimize_bridge(metainterp_sd, old_loop_tokens, bridge):
    debug_start("jit-optimize")
    try:
        return _optimize_bridge(metainterp_sd, old_loop_tokens, bridge)
    finally:
        debug_stop("jit-optimize")

def _optimize_bridge(metainterp_sd, old_loop_tokens, bridge):
    cpu = metainterp_sd.cpu    
    metainterp_sd.logger_noopt.log_loop(bridge.inputargs, bridge.operations)
    finder = BridgeSpecializationFinder(cpu)
    finder.find_nodes_bridge(bridge)
    if old_loop_tokens:
        old_loop_token = old_loop_tokens[0]
        bridge.operations[-1].setdescr(old_loop_token)   # patch jump target
        optimize_bridge_1(metainterp_sd, bridge)
        return old_loop_token
    return None
