"""
_stm.time(), _stm.clock()
"""

from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.translator.tool.cbuild import ExternalCompilationInfo


# Linux-only for now

eci = ExternalCompilationInfo(
    includes=["time.h"],
    libraries=["rt"],
    post_include_bits = ["""
double pypy_clock_get_time(void);
double pypy_clock_get_clock(void);
"""],
    separate_module_sources = ["""
double pypy_clock_get_time(void) {
    struct timespec t = {-1, 0};
    clock_gettime(CLOCK_REALTIME, &t);
    return t.tv_sec + 0.000000001 * t.tv_nsec;
}
double pypy_clock_get_clock(void) {
    struct timespec t = {-1, 0};
    clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &t);
    return t.tv_sec + 0.000000001 * t.tv_nsec;
}
"""])


pypy_clock_get_time = rffi.llexternal('pypy_clock_get_time',
                                      [], lltype.Float,
                                      compilation_info=eci,
                                      releasegil=False, transactionsafe=True)
pypy_clock_get_clock = rffi.llexternal('pypy_clock_get_clock',
                                       [], lltype.Float,
                                       compilation_info=eci,
                                       releasegil=False, transactionsafe=True)


def time(space):
    """Similar to time.time(), but works without conflict.
The drawback is that the returned times may appear out of order:
this thread's transaction may commit before or after another thread's,
while _stm.time() called by both may return results in the opposite
order (or even exactly equal results if you are unlucky)."""
    return space.wrap(pypy_clock_get_time())

def clock(space):
    """Similar to time.clock(), but works without conflict.
The drawback is that the returned times may appear out of order:
this thread's transaction may commit before or after another thread's,
while _stm.time() called by both may return results in the opposite
order (or even exactly equal results if you are unlucky)."""
    return space.wrap(pypy_clock_get_clock())
