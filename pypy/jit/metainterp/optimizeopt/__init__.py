from optimizer import Optimizer
from rewrite import OptRewrite
from intbounds import OptIntBounds
from virtualize import OptVirtualize
from heap import OptHeap

def optimize_loop_1(metainterp_sd, loop, virtuals=True):
    """Optimize loop.operations to make it match the input of loop.specnodes
    and to remove internal overheadish operations.  Note that loop.specnodes
    must be applicable to the loop; you will probably get an AssertionError
    if not.
    """
    optimizations = [OptIntBounds(),
                     OptRewrite(),
                     OptVirtualize(),
                     OptHeap(),
                    ]
    optimizer = Optimizer(metainterp_sd, loop, optimizations, virtuals)
    optimizer.propagate_all_forward()

def optimize_bridge_1(metainterp_sd, bridge):
    """The same, but for a bridge.  The only difference is that we don't
    expect 'specnodes' on the bridge.
    """
    optimize_loop_1(metainterp_sd, bridge, False)
        
