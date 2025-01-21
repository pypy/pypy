"""
Access to the time module's high-resolution monotonic clock
"""
import math
from rpython.rlib.rarithmetic import (
    r_longlong, ovfcheck_float_to_longlong)
from rpython.rlib import rfloat
from pypy.interpreter.error import oefmt

SECS_TO_NS = 10 ** 9
MS_TO_NS = 10 ** 6
US_TO_NS = 10 ** 3

def monotonic(space):
    """Call time.monotonic and return a unwrapped float"""
    # used in module.select
    from pypy.module.time import interp_time
    return interp_time._monotonic(space)

def timestamp_w(space, w_secs):
    if space.isinstance_w(w_secs, space.w_float):
        secs = space.float_w(w_secs)
        if math.isnan(secs):
            raise oefmt(space.w_ValueError, "timestamp is nan")
        result_float = math.ceil(secs * SECS_TO_NS)
        try:
            return ovfcheck_float_to_longlong(result_float)
        except OverflowError:
            raise oefmt(space.w_OverflowError,
                "timestamp %R too large to convert to C _PyTime_t", w_secs)
    else:
        try:
            sec = space.bigint_w(w_secs).tolonglong()
            result = sec * r_longlong(SECS_TO_NS)
        except OverflowError:
            raise oefmt(space.w_OverflowError,
                "timestamp %R too large to convert to C _PyTime_t", w_secs)
        return result
