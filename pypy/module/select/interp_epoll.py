from __future__ import with_statement

import errno

from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.error import OperationError, operationerrfmt, exception_from_errno
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rpython.tool import rffi_platform
from pypy.rlib._rsocket_rffi import socketclose, FD_SETSIZE
from pypy.rlib.rposix import get_errno
from pypy.translator.tool.cbuild import ExternalCompilationInfo


eci = ExternalCompilationInfo(
    includes = ['sys/epoll.h']
)

class CConfig:
    _compilation_info_ = eci


CConfig.epoll_data = rffi_platform.Struct("union epoll_data", [
    ("fd", rffi.INT),
])
CConfig.epoll_event = rffi_platform.Struct("struct epoll_event", [
    ("events", rffi.UINT),
    ("data", CConfig.epoll_data)
])

for symbol in ["EPOLL_CTL_ADD", "EPOLL_CTL_MOD", "EPOLL_CTL_DEL"]:
    setattr(CConfig, symbol, rffi_platform.DefinedConstantInteger(symbol))

cconfig = rffi_platform.configure(CConfig)

epoll_event = cconfig["epoll_event"]
EPOLL_CTL_ADD = cconfig["EPOLL_CTL_ADD"]
EPOLL_CTL_MOD = cconfig["EPOLL_CTL_MOD"]
EPOLL_CTL_DEL = cconfig["EPOLL_CTL_DEL"]

epoll_create = rffi.llexternal(
    "epoll_create", [rffi.INT], rffi.INT, compilation_info=eci
)
epoll_ctl = rffi.llexternal(
    "epoll_ctl",
    [rffi.INT, rffi.INT, rffi.INT, lltype.Ptr(epoll_event)],
    rffi.INT,
    compilation_info=eci
)
epoll_wait = rffi.llexternal(
    "epoll_wait",
    [rffi.INT, lltype.Ptr(rffi.CArray(epoll_event)), rffi.INT, rffi.INT],
    rffi.INT,
    compilation_info=eci,
)


class W_Epoll(Wrappable):
    def __init__(self, space, epfd):
        self.epfd = epfd

    @unwrap_spec(sizehint=int)
    def descr__new__(space, w_subtype, sizehint=-1):
        if sizehint == -1:
            sizehint = FD_SETSIZE - 1
        elif sizehint < 0:
            raise operationerrfmt(space.w_ValueError,
                "sizehint must be greater than zero, got %d", sizehint
            )
        epfd = epoll_create(sizehint)
        if epfd < 0:
            raise exception_from_errno(space, space.w_IOError)

        return space.wrap(W_Epoll(space, epfd))

    @unwrap_spec(fd=int)
    def descr_fromfd(space, w_cls, fd):
        return space.wrap(W_Epoll(space, fd))

    def __del__(self):
        self.close()

    def check_closed(self, space):
        if self.get_closed():
            raise OperationError(space.w_ValueError,
                space.wrap("I/O operation on closed epoll fd")
            )

    def get_closed(self):
        return self.epfd < 0

    def close(self):
        if not self.get_closed():
            socketclose(self.epfd)
            self.epfd = -1

    def epoll_ctl(self, space, ctl, w_fd, eventmask, ignore_ebadf=False):
        fd = space.c_filedescriptor_w(w_fd)
        with lltype.scoped_alloc(epoll_event) as ev:
            ev.c_events = rffi.cast(rffi.UINT, eventmask)
            rffi.setintfield(ev.c_data, 'c_fd', fd)

            result = epoll_ctl(self.epfd, ctl, fd, ev)
            if ignore_ebadf and get_errno() == errno.EBADF:
                result = 0
            if result < 0:
                raise exception_from_errno(space, space.w_IOError)

    def descr_get_closed(self, space):
        return space.wrap(self.get_closed())

    def descr_fileno(self, space):
        self.check_closed(space)
        return space.wrap(self.epfd)

    def descr_close(self, space):
        self.check_closed(space)
        self.close()

    @unwrap_spec(eventmask=int)
    def descr_register(self, space, w_fd, eventmask=-1):
        self.check_closed(space)
        self.epoll_ctl(space, EPOLL_CTL_ADD, w_fd, eventmask)

    def descr_unregister(self, space, w_fd):
        self.check_closed(space)
        self.epoll_ctl(space, EPOLL_CTL_DEL, w_fd, 0, ignore_ebadf=True)

    @unwrap_spec(eventmask=int)
    def descr_modify(self, space, w_fd, eventmask=-1):
        self.check_closed(space)
        self.epoll_ctl(space, EPOLL_CTL_MOD, w_fd, eventmask)

    @unwrap_spec(timeout=float, maxevents=int)
    def descr_poll(self, space, timeout=-1.0, maxevents=-1):
        self.check_closed(space)
        if timeout < 0:
            timeout = -1.0
        else:
            timeout *= 1000.0

        if maxevents == -1:
            maxevents = FD_SETSIZE - 1
        elif maxevents < 1:
            raise operationerrfmt(space.w_ValueError,
                "maxevents must be greater than 0, not %d", maxevents
            )

        with lltype.scoped_alloc(rffi.CArray(epoll_event), maxevents) as evs:
            nfds = epoll_wait(self.epfd, evs, maxevents, int(timeout))
            if nfds < 0:
                raise exception_from_errno(space, space.w_IOError)

            elist_w = [None] * nfds
            for i in xrange(nfds):
                event = evs[i]
                elist_w[i] = space.newtuple(
                    [space.wrap(event.c_data.c_fd), space.wrap(event.c_events)]
                )
            return space.newlist(elist_w)


W_Epoll.typedef = TypeDef("select.epoll",
    __new__ = interp2app(W_Epoll.descr__new__.im_func),
    fromfd = interp2app(W_Epoll.descr_fromfd.im_func, as_classmethod=True),

    closed = GetSetProperty(W_Epoll.descr_get_closed),
    fileno = interp2app(W_Epoll.descr_fileno),
    close = interp2app(W_Epoll.descr_close),
    register = interp2app(W_Epoll.descr_register),
    unregister = interp2app(W_Epoll.descr_unregister),
    modify = interp2app(W_Epoll.descr_modify),
    poll = interp2app(W_Epoll.descr_poll),
)
W_Epoll.typedef.acceptable_as_base_class = False
