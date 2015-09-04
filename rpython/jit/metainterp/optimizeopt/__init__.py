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
from rpython.jit.metainterp.optimizeopt.vectorize import optimize_vector
from rpython.rlib.jit import PARAMETERS, ENABLE_ALL_OPTS
from rpython.rlib.unroll import unrolling_iterable
from rpython.rlib.debug import debug_start, debug_stop, debug_print


ALL_OPTS = [('intbounds', OptIntBounds),
            ('rewrite', OptRewrite),
            ('virtualize', OptVirtualize),
            ('string', OptString),
            ('pure', OptPure),
            ('earlyforce', OptEarlyForce),
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

def optimize_trace(metainterp_sd, jitdriver_sd, compile_data):
    """Optimize loop.operations to remove internal overheadish operations.
    """

    debug_start("jit-optimize")

    enable_opts = warmstate.enable_opts
    if try_disabling_unroll:
        if 'unroll' not in enable_opts:
            return None
        enable_opts = enable_opts.copy()
        del enable_opts['unroll']

    try:
        #logops = metainterp_sd.logger_noopt.log_loop(inputargs, operations)
        optimizations, unroll = build_opt_chain(metainterp_sd,
                                                compile_data.enable_opts)
        return compile_data.optimize(metainterp_sd, jitdriver_sd,
                                     optimizations, unroll)
        # XXX if unroll:
        # XXX     if not export_state and \
        # XXX         ((warmstate.vec and jitdriver_sd.vec) \
        # XXX          or warmstate.vec_all):
        # XXX         optimize_vector(metainterp_sd, jitdriver_sd, loop,
        # XXX                         optimizations, inline_short_preamble,
        # XXX                         start_state, warmstate)
        # XXX     else:
        # XXX         return optimize_unroll(metainterp_sd, jitdriver_sd, loop,
        # XXX                                optimizations, inline_short_preamble,
        # XXX                                start_state, export_state)
        # XXX else:
        # XXX     optimizer = Optimizer(metainterp_sd, jitdriver_sd, loop,
        # XXX                           optimizations)
        # XXX     optimizer.propagate_all_forward()
    finally:
        compile_data.forget_optimization_info()
        debug_stop("jit-optimize")

if __name__ == '__main__':
    print ALL_OPTS_NAMES

