import time
from pypy.interpreter.gateway import unwrap_spec


def clock(space):
    """Return the CPU time or real time since the start of the process or
since the first call to clock().  This returns a floating point measured
in seconds with as much precision as the system records."""
    return space.wrap(time.clock())

def time_(space):
    """Return the current time in seconds since the Epoch.  Fractions of a
second may be present if the system clock provides them."""
    return space.wrap(time.time())

@unwrap_spec(seconds=float)
def sleep(space, seconds):
    """Delay execution for a given number of seconds.  The argument may
be a floating point number for subsecond precision."""
    time.sleep(seconds)
