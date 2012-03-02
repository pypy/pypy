from pypy.rlib.debug import debug_start, debug_stop, debug_print
from pypy.jit.metainterp.jitexc import JitException

class InvalidLoop(JitException):
    """Raised when the optimize*.py detect that the loop that
    we are trying to build cannot possibly make sense as a
    long-running loop (e.g. it cannot run 2 complete iterations)."""
