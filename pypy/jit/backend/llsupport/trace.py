from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.objectmodel import CDefinedIntSymbolic, we_are_translated


# Calling this function adds an entry in the buffer maintained by
# src/debug_lltrace.h.  Arguments: addr, newvalue, mark.
trace_set = rffi.llexternal("_RPyTraceSet",
                            [rffi.CCHARP, rffi.LONG, rffi.LONG],
                            lltype.Void,
                            _callable = lambda a, n, m: None,
                            _nowrapper = True)

_is_tracing = CDefinedIntSymbolic('RPY_IS_TRACING', default=0)
addr_of_trace_set = CDefinedIntSymbolic('((long)&_RPyTraceSet)', default=0)

def is_tracing():
    return we_are_translated() and _is_tracing != 0
