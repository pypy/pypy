from pypy.jit.metainterp.optimizeopt.optimizer import Optimizer
from pypy.jit.metainterp.optimizeopt.rewrite import OptRewrite
from pypy.jit.metainterp.optimizeopt.intbounds import OptIntBounds
from pypy.jit.metainterp.optimizeopt.virtualize import OptVirtualize
from pypy.jit.metainterp.optimizeopt.heap import OptHeap
from pypy.jit.metainterp.optimizeopt.string import OptString
from pypy.jit.metainterp.optimizeopt.unroll import OptUnroll

def optimize_loop_1(metainterp_sd, loop, virtuals=True):
    """Optimize loop.operations to make it match the input of loop.specnodes
    and to remove internal overheadish operations.  Note that loop.specnodes
    must be applicable to the loop; you will probably get an AssertionError
    if not.
    """
    optimizations = [OptUnroll(),
                     OptIntBounds(),
                     OptRewrite(),
                     OptVirtualize(),
                     OptString(),
                     OptHeap(),
                    ]
    optimizer = Optimizer(metainterp_sd, loop, optimizations, virtuals)
    optimizer.propagate_all_forward()

def optimize_bridge_1(metainterp_sd, bridge):
    """The same, but for a bridge.  The only difference is that we don't
    expect 'specnodes' on the bridge.
    """
    optimize_loop_1(metainterp_sd, bridge, False)
