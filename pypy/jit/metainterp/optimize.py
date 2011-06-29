from pypy.rlib.debug import debug_start, debug_stop
from pypy.jit.metainterp.jitexc import JitException

class InvalidLoop(JitException):
    """Raised when the optimize*.py detect that the loop that
    we are trying to build cannot possibly make sense as a
    long-running loop (e.g. it cannot run 2 complete iterations)."""

class RetraceLoop(JitException):
    """ Raised when inlining a short preamble resulted in an
        InvalidLoop. This means the optimized loop is too specialized
        to be useful here, so we trace it again and produced a second
        copy specialized in some different way.
    """

# ____________________________________________________________

def optimize_loop(metainterp_sd, old_loop_tokens, loop, enable_opts):
    debug_start("jit-optimize")
    try:
        return _optimize_loop(metainterp_sd, old_loop_tokens, loop,
                              enable_opts)
    finally:
        debug_stop("jit-optimize")

def _optimize_loop(metainterp_sd, old_loop_tokens, loop, enable_opts):
    from pypy.jit.metainterp.optimizeopt import optimize_loop_1
    loop.logops = metainterp_sd.logger_noopt.log_loop(loop.inputargs,
                                                      loop.operations)
    # XXX do we really still need a list?
    if old_loop_tokens:
        return old_loop_tokens[0]
    optimize_loop_1(metainterp_sd, loop, enable_opts)
    return None

# ____________________________________________________________

def optimize_bridge(metainterp_sd, old_loop_tokens, bridge, enable_opts,
                    inline_short_preamble=True, retraced=False):
    debug_start("jit-optimize")
    try:
        return _optimize_bridge(metainterp_sd, old_loop_tokens, bridge,
                                enable_opts,
                                inline_short_preamble, retraced)
    finally:
        debug_stop("jit-optimize")

def _optimize_bridge(metainterp_sd, old_loop_tokens, bridge, enable_opts,
                     inline_short_preamble, retraced=False):
    from pypy.jit.metainterp.optimizeopt import optimize_bridge_1
    bridge.logops = metainterp_sd.logger_noopt.log_loop(bridge.inputargs,
                                                        bridge.operations)
    if old_loop_tokens:
        old_loop_token = old_loop_tokens[0]
        bridge.operations[-1].setdescr(old_loop_token)   # patch jump target
        optimize_bridge_1(metainterp_sd, bridge, enable_opts,
                          inline_short_preamble, retraced)
        return old_loop_tokens[0]
        #return bridge.operations[-1].getdescr()
    return None

# ____________________________________________________________
