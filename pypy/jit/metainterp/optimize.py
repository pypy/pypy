# ____________________________________________________________

from pypy.jit.metainterp.optimizefindnode import PerfectSpecializationFinder
from pypy.jit.metainterp.optimizeopt import optimize_loop_1
from pypy.jit.metainterp.specnode import equals_specnodes

def optimize_loop(options, old_loop_tokens, loop, cpu):
    options.logger_noopt.log_loop(loop.inputargs, loop.operations)
    finder = PerfectSpecializationFinder(cpu)
    finder.find_nodes_loop(loop)
    for old_loop_token in old_loop_tokens:
        if equals_specnodes(old_loop_token.specnodes, loop.specnodes):
            return old_loop_token
    optimize_loop_1(cpu, loop)
    return None

# ____________________________________________________________

from pypy.jit.metainterp.optimizefindnode import BridgeSpecializationFinder
from pypy.jit.metainterp.optimizeopt import optimize_bridge_1

def optimize_bridge(options, old_loop_tokens, bridge, cpu):
    options.logger_noopt.log_loop(bridge.inputargs, bridge.operations)
    finder = BridgeSpecializationFinder(cpu)
    finder.find_nodes_bridge(bridge)
    for old_loop_token in old_loop_tokens:
        if finder.bridge_matches(old_loop_token.specnodes):
            bridge.operations[-1].jump_target = old_loop_token
            optimize_bridge_1(cpu, bridge)
            return old_loop_token
    return None

# ____________________________________________________________
