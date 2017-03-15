"""
Access to the time module's high-resolution monotonic clock
"""

def monotonic(space):
    from pypy.module.time import interp_time
    if interp_time.HAS_MONOTONIC:
        w_res = interp_time.monotonic(space)
    else:
        w_res = interp_time.gettimeofday(space)
    return space.float_w(w_res)   # xxx back and forth
