from pypy.jit.metainterp.optimizeopt.optimizer import Optimizer
from pypy.jit.metainterp.optimizeopt.rewrite import OptRewrite
from pypy.jit.metainterp.optimizeopt.intbounds import OptIntBounds
from pypy.jit.metainterp.optimizeopt.virtualize import OptVirtualize
from pypy.jit.metainterp.optimizeopt.heap import OptHeap
from pypy.jit.metainterp.optimizeopt.fficall import OptFfiCall
from pypy.jit.metainterp.optimizeopt.string import OptString
from pypy.jit.metainterp.optimizeopt.unroll import OptUnroll

def optimize_loop_1(metainterp_sd, loop, unroll=True):
    """Optimize loop.operations to remove internal overheadish operations. 
    """
    opt_str = OptString()
    optimizations = [OptIntBounds(),
                     OptRewrite(),
                     OptVirtualize(),
                     opt_str,
                     OptHeap(),
                     OptFfiCall(),
                    ]
    if unroll:
        optimizations.insert(0, OptUnroll())
        opt_str.enabled = False # FIXME: Workaround to disable string optimisation
                                # during preamble but to keep it during the loop
    optimizer = Optimizer(metainterp_sd, loop, optimizations)
    optimizer.propagate_all_forward()

def optimize_bridge_1(metainterp_sd, bridge):
    """The same, but for a bridge. """
    optimize_loop_1(metainterp_sd, bridge, False)
