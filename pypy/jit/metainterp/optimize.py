# ____________________________________________________________

from pypy.jit.metainterp.optimizefindnode import PerfectSpecializationFinder
from pypy.jit.metainterp.optimizeopt import optimize_loop_1
from pypy.jit.metainterp.specnode import equals_specnodes

def optimize_loop(options, old_loops, loop, cpu):
    if not options.specialize:         # for tests only
        if old_loops:
            return old_loops[0]
        else:
            return None
    #loop.dump()
    finder = PerfectSpecializationFinder()
    finder.find_nodes_loop(loop)
    for old_loop in old_loops:
        if equals_specnodes(old_loop.specnodes, loop.specnodes):
            return old_loop
    optimize_loop_1(cpu, loop)
    return None

# ____________________________________________________________

from pypy.jit.metainterp.optimizefindnode import BridgeSpecializationFinder
from pypy.jit.metainterp.optimizeopt import optimize_bridge_1

def optimize_bridge(options, old_loops, bridge, cpu):
    if not options.specialize:         # for tests only
        return old_loops[0]
    finder = BridgeSpecializationFinder()
    finder.find_nodes_bridge(bridge)
    for old_loop in old_loops:
        if finder.bridge_matches(old_loop.specnodes):
            bridge.operations[-1].jump_target = old_loop
            optimize_bridge_1(cpu, bridge)
            return old_loop
    return None

# ____________________________________________________________
