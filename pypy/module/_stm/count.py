"""
_stm.count()
"""

from rpython.rlib import rstm


def count(space):
    """Return a new integer every time it is called,
without generating conflicts."""
    count = rstm.stm_count()
    return space.wrap(count)
