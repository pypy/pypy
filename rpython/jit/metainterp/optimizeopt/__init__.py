from rpython.jit.metainterp.optimizeopt.optimizer import Optimizer
from rpython.jit.metainterp.optimizeopt.rewrite import OptRewrite
from rpython.jit.metainterp.optimizeopt.intbounds import OptIntBounds
from rpython.jit.metainterp.optimizeopt.virtualize import OptVirtualize
from rpython.jit.metainterp.optimizeopt.heap import OptHeap
from rpython.jit.metainterp.optimizeopt.vstring import OptString
from rpython.jit.metainterp.optimizeopt.simplify import OptSimplify
from rpython.jit.metainterp.optimizeopt.pure import OptPure
from rpython.jit.metainterp.optimizeopt.earlyforce import OptEarlyForce
from rpython.rlib.rjitlog import rjitlog as jl
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
    if (metainterp_sd.cpu is not None and
        not metainterp_sd.cpu.supports_guard_gc_type):
        unroll = False
    for name, opt in unroll_all_opts:
        if name in enable_opts:
            if opt is not None:
                o = opt()
                optimizations.append(o)

    if ('rewrite' not in enable_opts or 'virtualize' not in enable_opts
        or 'heap' not in enable_opts or 'pure' not in enable_opts):
        optimizations.append(OptSimplify(unroll))

    return optimizations, unroll

def optimize_trace(metainterp_sd, jitdriver_sd, compile_data, memo=None):
    """Optimize loop.operations to remove internal overheadish operations.
    """
    debug_start("jit-optimize")
    try:
        # mark that a new trace has been started
        log = metainterp_sd.jitlog.log_trace(jl.MARK_TRACE, metainterp_sd, None)
        log.write_trace(compile_data.trace)
        if compile_data.log_noopt:
            metainterp_sd.logger_noopt.log_loop_from_trace(compile_data.trace, memo=memo)
        if memo is None:
            memo = {}
        compile_data.box_names_memo = memo
        optimizations, unroll = build_opt_chain(metainterp_sd,
                                                compile_data.enable_opts)
        return compile_data.optimize(metainterp_sd, jitdriver_sd,
                                     optimizations, unroll)
    finally:
        compile_data.forget_optimization_info()
        debug_stop("jit-optimize")

if __name__ == '__main__':
    print ALL_OPTS_NAMES

