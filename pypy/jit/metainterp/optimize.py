# ____________________________________________________________

from pypy.jit.metainterp.optimizefindnode import PerfectSpecializationFinder
from pypy.jit.metainterp.optimizeopt import optimize_loop_1
from pypy.jit.metainterp.specnode import equals_specnodes

def optimize_loop(options, old_loop_tokens, loop, cpu):
    if not options.specialize:         # for tests only
        if old_loop_tokens:
            return old_loop_tokens[0]
        else:
            return None
    if options.logger_noopt is not None:
        options.logger_noopt.log_loop(loop)
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
    if not options.specialize:         # for tests only
        return old_loop_tokens[0]
    if options.logger_noopt is not None:
        options.logger_noopt.log_loop(bridge)
    finder = BridgeSpecializationFinder(cpu)
    finder.find_nodes_bridge(bridge)
    for old_loop_token in old_loop_tokens:
        if finder.bridge_matches(old_loop_token.specnodes):
            bridge.operations[-1].jump_target = old_loop_token
            optimize_bridge_1(cpu, bridge)
            return old_loop_token
    return None

# ____________________________________________________________
