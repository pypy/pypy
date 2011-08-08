from pypy.jit.metainterp.optimizeopt.optimizer import Optimizer
from pypy.jit.metainterp.optimizeopt.rewrite import OptRewrite
from pypy.jit.metainterp.optimizeopt.intbounds import OptIntBounds
from pypy.jit.metainterp.optimizeopt.virtualize import OptVirtualize
from pypy.jit.metainterp.optimizeopt.heap import OptHeap
from pypy.jit.metainterp.optimizeopt.vstring import OptString
from pypy.jit.metainterp.optimizeopt.unroll import optimize_unroll, OptInlineShortPreamble
from pypy.jit.metainterp.optimizeopt.fficall import OptFfiCall
from pypy.jit.metainterp.optimizeopt.simplify import OptSimplify
from pypy.rlib.jit import PARAMETERS
from pypy.rlib.unroll import unrolling_iterable

ALL_OPTS = [('intbounds', OptIntBounds),
            ('rewrite', OptRewrite),
            ('virtualize', OptVirtualize),
            ('string', OptString),
            ('heap', OptHeap),
            ('ffi', None),
            ('unroll', None)]
# no direct instantiation of unroll
unroll_all_opts = unrolling_iterable(ALL_OPTS)

ALL_OPTS_DICT = dict.fromkeys([name for name, _ in ALL_OPTS])
ALL_OPTS_LIST = [name for name, _ in ALL_OPTS]
ALL_OPTS_NAMES = ':'.join([name for name, _ in ALL_OPTS])

def build_opt_chain(metainterp_sd, enable_opts,
                    inline_short_preamble=True, retraced=False):
    config = metainterp_sd.config
    optimizations = []
    unroll = 'unroll' in enable_opts    # 'enable_opts' is normally a dict
    for name, opt in unroll_all_opts:
        if name in enable_opts:
            if opt is not None:
                o = opt()
                if unroll and name == 'string':
                    o.enabled = False
                # FIXME: Workaround to disable string optimisation
                # during preamble but to keep it during the loop
                optimizations.append(o)
            elif name == 'ffi' and config.translation.jit_ffi:
                # we cannot put the class directly in the unrolling_iterable,
                # because we do not want it to be seen at all (to avoid to
                # introduce a dependency on libffi in case we do not need it)
                optimizations.append(OptFfiCall())

    if ('rewrite' not in enable_opts or 'virtualize' not in enable_opts
        or 'heap' not in enable_opts):
        optimizations.append(OptSimplify())

    if inline_short_preamble:
        optimizations = [OptInlineShortPreamble(retraced)] + optimizations

    return optimizations, unroll


def optimize_loop_1(metainterp_sd, loop, enable_opts,
                    inline_short_preamble=True, retraced=False, bridge=False):
    """Optimize loop.operations to remove internal overheadish operations.
    """

    optimizations, unroll = build_opt_chain(metainterp_sd, enable_opts,
                                            inline_short_preamble, retraced)
    if unroll:
        optimize_unroll(metainterp_sd, loop, optimizations)
    else:
        optimizer = Optimizer(metainterp_sd, loop, optimizations, bridge)
        optimizer.propagate_all_forward()

def optimize_bridge_1(metainterp_sd, bridge, enable_opts,
                      inline_short_preamble=True, retraced=False):
    """The same, but for a bridge. """
    enable_opts = enable_opts.copy()
    try:
        del enable_opts['unroll']
    except KeyError:
        pass
    optimize_loop_1(metainterp_sd, bridge, enable_opts,
                    inline_short_preamble, retraced, bridge=True)

if __name__ == '__main__':
    print ALL_OPTS_NAMES
