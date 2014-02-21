from rpython.jit.metainterp.optimizeopt.optimizer import Optimizer
from rpython.jit.metainterp.optimizeopt.rewrite import OptRewrite
from rpython.jit.metainterp.optimizeopt.intbounds import OptIntBounds
from rpython.jit.metainterp.optimizeopt.virtualize import OptVirtualize
from rpython.jit.metainterp.optimizeopt.heap import OptHeap
from rpython.jit.metainterp.optimizeopt.vstring import OptString
from rpython.jit.metainterp.optimizeopt.unroll import optimize_unroll
from rpython.jit.metainterp.optimizeopt.simplify import OptSimplify
from rpython.jit.metainterp.optimizeopt.pure import OptPure
from rpython.jit.metainterp.optimizeopt.earlyforce import OptEarlyForce
from rpython.rlib.jit import PARAMETERS, ENABLE_ALL_OPTS
from rpython.rlib.unroll import unrolling_iterable
from rpython.rlib.debug import debug_start, debug_stop, debug_print


ALL_OPTS = [('intbounds', OptIntBounds),
            ('rewrite', OptRewrite),
            ('virtualize', OptVirtualize),
            ('string', OptString),
            ('earlyforce', OptEarlyForce),
            ('pure', OptPure),
            ('heap', OptHeap),
            ('unroll', None)]
# no direct instantiation of unroll
unroll_all_opts = unrolling_iterable(ALL_OPTS)

ALL_OPTS_DICT = dict.fromkeys([name for name, _ in ALL_OPTS])
ALL_OPTS_LIST = [name for name, _ in ALL_OPTS]
ALL_OPTS_NAMES = ':'.join([name for name, _ in ALL_OPTS])

assert ENABLE_ALL_OPTS == ALL_OPTS_NAMES, (
    'please fix rlib/jit.py to say ENABLE_ALL_OPTS = %r' % (ALL_OPTS_NAMES,))

def build_opt_chain(metainterp_sd, enable_opts):
    optimizations = []
    unroll = 'unroll' in enable_opts    # 'enable_opts' is normally a dict
    for name, opt in unroll_all_opts:
        if name in enable_opts:
            if opt is not None:
                o = opt()
                optimizations.append(o)

    if ('rewrite' not in enable_opts or 'virtualize' not in enable_opts
        or 'heap' not in enable_opts or 'unroll' not in enable_opts
        or 'pure' not in enable_opts):
        optimizations.append(OptSimplify(unroll))

    return optimizations, unroll

def optimize_trace(metainterp_sd, loop, enable_opts, inline_short_preamble=True):
    """Optimize loop.operations to remove internal overheadish operations.
    """

    debug_start("jit-optimize")
    try:
        loop.logops = metainterp_sd.logger_noopt.log_loop(loop.inputargs,
                                                          loop.operations)
        optimizations, unroll = build_opt_chain(metainterp_sd, enable_opts)
        if unroll:
            optimize_unroll(metainterp_sd, loop, optimizations, inline_short_preamble)
        else:
            optimizer = Optimizer(metainterp_sd, loop, optimizations)
            optimizer.propagate_all_forward()
    finally:
        debug_stop("jit-optimize")

if __name__ == '__main__':
    print ALL_OPTS_NAMES

