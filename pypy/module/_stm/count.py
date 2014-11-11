"""
_stm.count()
"""

from rpython.rlib import rstm


def count(space):
    """Return a different positive integer every time it is called.
This works without generating conflicts.  The returned integers are
only roughly in increasing order; this should not be relied upon."""
    count = rstm.stm_count()
    return space.wrap(count)
