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

def use_unrolling(cpu, enable_opts):
    return cpu.supports_guard_gc_type and 'unroll' in enable_opts

def build_opt_chain(enable_opts):
    optimizations = []
    for name, opt in unroll_all_opts:
        if name in enable_opts:
            if opt is not None:
                o = opt()
                optimizations.append(o)
    if ('rewrite' not in enable_opts or 'virtualize' not in enable_opts or
            'heap' not in enable_opts or 'pure' not in enable_opts):
        optimizations.append(OptSimplify())
    return optimizations

def _log_loop_from_trace(metainterp_sd, trace, memo=None, is_unrolled=False):
    # mark that a new trace has been started
    log = metainterp_sd.jitlog.log_trace(jl.MARK_TRACE, metainterp_sd, None)
    log.write_trace(trace)
    if not is_unrolled:
        metainterp_sd.logger_noopt.log_loop_from_trace(trace, memo=memo)

def optimize_trace(metainterp_sd, jitdriver_sd, compile_data,
                   memo=None, use_unrolling=True):
    """Optimize loop.operations to remove internal overheadish operations.
    """
    debug_start("jit-optimize")
    try:
        _log_loop_from_trace(metainterp_sd, compile_data.trace, memo,
                             is_unrolled=not compile_data.log_noopt)
        if memo is None:
            memo = {}
        compile_data.box_names_memo = memo
        optimizations = build_opt_chain(compile_data.enable_opts)
        return compile_data.optimize(metainterp_sd, jitdriver_sd,
                                     optimizations, unroll=use_unrolling)
    finally:
        compile_data.forget_optimization_info()
        debug_stop("jit-optimize")

if __name__ == '__main__':
    print ALL_OPTS_NAMES
