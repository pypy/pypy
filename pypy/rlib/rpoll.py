"""
An RPython implementation of select.poll() based on rffi.
Note that this is not a drop-in replacement: the interface is
simplified - instead of a polling object there is only a poll()
function that directly takes a dictionary as argument.
"""

import os
from pypy.rlib import _rsocket_rffi as _c
from pypy.rpython.lltypesystem import lltype, rffi

# ____________________________________________________________
# events
#
eventnames = '''POLLIN POLLPRI POLLOUT POLLERR POLLHUP POLLNVAL
                POLLRDNORM POLLRDBAND POLLWRNORM POLLWEBAND POLLMSG'''.split()

eventnames = [name for name in eventnames
                   if getattr(_c.cConfig, name) is not None]

for name in eventnames:
    globals()[name] = getattr(_c.cConfig, name)

# ____________________________________________________________
# poll()
#
class PollError(Exception):
    def __init__(self, errno):
        self.errno = errno
    def get_msg(self):
        return os.strerror(self.errno)

def poll(fddict, timeout=-1):
    """'fddict' maps file descriptors to interesting events.
    'timeout' is an integer in milliseconds, and NOT a float
    number of seconds, but it's the same in CPython.  Use -1 for infinite.
    Returns a list [(fd, events)].
    """
    numfd = len(fddict)
    pollfds = lltype.malloc(_c.pollfdarray, numfd, flavor='raw')
    try:
        i = 0
        for fd, events in fddict.iteritems():
            rffi.setintfield(pollfds[i], 'c_fd', fd)
            rffi.setintfield(pollfds[i], 'c_events', events)
            i += 1
        assert i == numfd

        ret = _c.poll(pollfds, numfd, timeout)

        if ret < 0:
            raise PollError(_c.geterrno())

        retval = []
        for i in range(numfd):
            pollfd = pollfds[i]
            if pollfd.c_revents:
                retval.append((pollfd.c_fd, pollfd.c_revents))
    finally:
        lltype.free(pollfds, flavor='raw')
    return retval
