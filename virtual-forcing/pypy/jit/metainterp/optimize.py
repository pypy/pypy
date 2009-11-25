from pypy.rlib.debug import debug_start, debug_stop

# ____________________________________________________________

from pypy.jit.metainterp.optimizefindnode import PerfectSpecializationFinder
from pypy.jit.metainterp.optimizeopt import optimize_loop_1
from pypy.jit.metainterp.specnode import equals_specnodes

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
    finder.find_nodes_loop(loop)
    for old_loop_token in old_loop_tokens:
        if equals_specnodes(old_loop_token.specnodes, loop.token.specnodes):
            return old_loop_token
    optimize_loop_1(metainterp_sd, loop)
    return None

# ____________________________________________________________

from pypy.jit.metainterp.optimizefindnode import BridgeSpecializationFinder
from pypy.jit.metainterp.optimizeopt import optimize_bridge_1

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
    for old_loop_token in old_loop_tokens:
        if finder.bridge_matches(old_loop_token.specnodes):
            bridge.operations[-1].descr = old_loop_token   # patch jump target
            optimize_bridge_1(metainterp_sd, bridge)
            return old_loop_token
    return None

# ____________________________________________________________
