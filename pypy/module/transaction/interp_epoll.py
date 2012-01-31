
# Linux-only

from __future__ import with_statement
import os
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.error import OperationError
from pypy.module.select.interp_epoll import W_Epoll, FD_SETSIZE
from pypy.module.select.interp_epoll import epoll_event
from pypy.module.select.interp_epoll import epoll_wait
from pypy.module.transaction import interp_transaction
from pypy.rlib import rposix


class EPollPending(interp_transaction.AbstractPending):
    def __init__(self, space, epoller, w_callback):
        self.space = space
        self.epoller = epoller
        self.w_callback = w_callback

    def run(self):
        # this code is run non-transactionally
        state = interp_transaction.state
        if state.has_exception():
            return
        maxevents = FD_SETSIZE - 1    # for now
        timeout = 500                 # for now: half a second
        with lltype.scoped_alloc(rffi.CArray(epoll_event), maxevents) as evs:
            nfds = epoll_wait(self.epoller.epfd, evs, maxevents, int(timeout))
            if nfds < 0:
                state.got_exception_errno = rposix.get_errno()
                state.must_reraise_exception(_reraise_from_errno)
                return
            for i in range(nfds):
                event = evs[i]
                fd = rffi.cast(lltype.Signed, event.c_data.c_fd)
                PendingCallback(self.w_callback, fd, event.c_events).register()
        # re-register myself to epoll_wait() for more
        self.register()


class PendingCallback(interp_transaction.AbstractPending):
    def __init__(self, w_callback, fd, events):
        self.w_callback = w_callback
        self.fd = fd
        self.events = events

    def run_in_transaction(self, space):
        space.call_function(self.w_callback, space.wrap(self.fd),
                                             space.wrap(self.events))


def _reraise_from_errno():
    state = interp_transaction.state
    space = state.space
    errno = state.got_exception_errno
    msg = os.strerror(errno)
    w_type = space.w_IOError
    w_error = space.call_function(w_type, space.wrap(errno), space.wrap(msg))
    raise OperationError(w_type, w_error)


@unwrap_spec(epoller=W_Epoll)
def add_epoll(space, epoller, w_callback):
    EPollPending(space, epoller, w_callback).register()
