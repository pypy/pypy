from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError, operationerrfmt, exception_from_errno
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef, generic_new_descr, GetSetProperty
from pypy.rlib._rsocket_rffi import socketclose
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rpython.tool import rffi_platform
from pypy.translator.tool.cbuild import ExternalCompilationInfo


# http://www.freebsd.org/cgi/man.cgi?query=kqueue&sektion=2
# /usr/include/sys/event.h
#
eci = ExternalCompilationInfo(
    includes = ["sys/types.h",
                "sys/event.h",
                "sys/time.h"],
)


class CConfig:
    _compilation_info_ = eci


# struct kevent {
# 	uintptr_t	ident;		/* identifier for this event */
# 	short		filter;		/* filter for event */
# 	u_short		flags;
# 	u_int		fflags;
# 	intptr_t	data;
# 	void		*udata;		/* opaque user data identifier */
# };
#
CConfig.kevent = rffi_platform.Struct("struct kevent", [
    ("ident", rffi.UINT),
    ("filter", rffi.SHORT),
    ("flags", rffi.USHORT),
    ("fflags", rffi.UINT),
    ("data", rffi.INT),
    ("udata", rffi.VOIDP),
])

# struct timespec {
#	time_t	tv_sec;		/* seconds */
#	long	tv_nsec;	/* and nanoseconds */
# };
CConfig.timespec = rffi_platform.Struct("struct timespec", [
    ("tv_sec", rffi.TIME_T),
    ("tv_nsec", rffi.LONG),
])


symbol_map = {
    "KQ_FILTER_READ": "EVFILT_READ",
    "KQ_FILTER_WRITE": "EVFILT_WRITE",
    "KQ_FILTER_AIO": "EVFILT_AIO",
    "KQ_FILTER_VNODE": "EVFILT_VNODE",
    "KQ_FILTER_PROC": "EVFILT_PROC",
#    "KQ_FILTER_NETDEV": None, # deprecated on FreeBSD .. no longer defined .. what to do?
    "KQ_FILTER_SIGNAL": "EVFILT_SIGNAL",
    "KQ_FILTER_TIMER": "EVFILT_TIMER",

    "KQ_EV_ADD": "EV_ADD",
    "KQ_EV_DELETE": "EV_DELETE",
    "KQ_EV_ENABLE": "EV_ENABLE",
    "KQ_EV_DISABLE": "EV_DISABLE",
    "KQ_EV_ONESHOT": "EV_ONESHOT",
    "KQ_EV_CLEAR": "EV_CLEAR",

    # for the next 2 Python docs: "internal event" .. not defined on FreeBSD .. what to do?
#    "KQ_EV_SYSFLAGS": None,
#    "KQ_EV_FLAG1": None,

    "KQ_EV_EOF": "EV_EOF",
    "KQ_EV_ERROR": "EV_ERROR"
}

for symbol in symbol_map.values():
    setattr(CConfig, symbol, rffi_platform.DefinedConstantInteger(symbol))

cconfig = rffi_platform.configure(CConfig)

kevent = cconfig["kevent"]
timespec = cconfig["timespec"]

for symbol in symbol_map:
    globals()[symbol] = cconfig[symbol_map[symbol]]


# int kqueue(void);
#
syscall_kqueue = rffi.llexternal(
    "kqueue",
    [],
    rffi.INT,
    compilation_info=eci
)

# int kevent(int kq,
#            const struct kevent *changelist, int nchanges,
# 	               struct kevent *eventlist, int nevents,
# 	         const struct timespec *timeout);
#
syscall_kevent = rffi.llexternal(
    "kevent",
    [rffi.INT,
     lltype.Ptr(rffi.CArray(kevent)), rffi.INT,
     lltype.Ptr(rffi.CArray(kevent)), rffi.INT,
     lltype.Ptr(timespec)],
    rffi.INT,
    compilation_info=eci
)


class W_Kqueue(Wrappable):
    def __init__(self, space, kqfd):
        self.kqfd = kqfd

    def descr__new__(space, w_subtype):
        kqfd = syscall_kqueue()
        if kqfd < 0:
            raise exception_from_errno(space, space.w_IOError)
        return space.wrap(W_Kqueue(space, kqfd))

    @unwrap_spec(fd=int)
    def descr_fromfd(space, w_cls, fd):
        return space.wrap(W_Kqueue(space, fd))

    def __del__(self):
        self.close()

    def get_closed(self):
        return self.kqfd < 0

    def close(self):
        if not self.get_closed():
            socketclose(self.kqfd)
            self.kqfd = -1

    def check_closed(self, space):
        if self.get_closed():
            raise OperationError(space.w_ValueError, space.wrap("I/O operation on closed kqueue fd"))

    def descr_get_closed(self, space):
        return space.wrap(self.get_closed())

    def descr_fileno(self, space):
        self.check_closed(space)
        return space.wrap(self.kqfd)

    def descr_close(self, space):
        self.close()

    @unwrap_spec(max_events=int)
    def descr_control(self, space, w_changelist, max_events, w_timeout=None):

        self.check_closed(space)

        if max_events < 0:
            raise operationerrfmt(space.w_ValueError,
                "Length of eventlist must be 0 or positive, got %d", max_events
            )

        if space.is_w(w_changelist, space.w_None):
            changelist_len = 0
        else:
            changelist_len = space.len_w(w_changelist)

        with lltype.scoped_alloc(rffi.CArray(kevent), changelist_len) as changelist, \
             lltype.scoped_alloc(rffi.CArray(kevent), max_events) as eventlist, \
             lltype.scoped_alloc(timespec) as timeout:

            if space.is_w(w_timeout, space.w_None):
                timeout.c_tv_sec = 0
                timeout.c_tv_nsec = 0
            else:
                _timeout = space.float_w(w_timeout)
                if _timeout < 0:
                    raise operationerrfmt(space.w_ValueError,
                        "Timeout must be None or >= 0, got %f", _timeout
                    )
                sec = int(_timeout)
                nsec = int(1e9 * (_timeout - sec) + 0.5)
                rffi.setintfield(timeout, 'c_tv_sec', sec)
                rffi.setintfield(timeout, 'c_tv_nsec', nsec)

            for i in xrange(changelist_len):
                ev = space.getitem(w_changelist, space.wrap(i))
                changelist[i].c_ident = ev.event.c_ident
                changelist[i].c_filter = ev.event.c_filter
                changelist[i].c_flags = ev.event.c_flags
                changelist[i].c_fflags = ev.event.c_fflags
                changelist[i].c_data = ev.event.c_data

            nfds = syscall_kevent(self.kqfd,
                                  changelist,
                                  changelist_len,
                                  eventlist,
                                  max_events,
                                  timeout)
            if nfds < 0:
                raise exception_from_errno(space, space.w_IOError)
            else:
                elist_w = [None] * nfds
                for i in xrange(nfds):

                    evt = eventlist[i]

                    event_w = W_Kevent(space)
                    event_w.event = lltype.malloc(kevent, flavor="raw")
                    event_w.event.c_ident = evt.c_ident
                    event_w.event.c_filter = evt.c_filter
                    event_w.event.c_flags = evt.c_flags
                    event_w.event.c_fflags = evt.c_fflags
                    event_w.event.c_data = evt.c_data

                    elist_w[i] = event_w
                return space.newlist(elist_w)



W_Kqueue.typedef = TypeDef("select.kqueue",
    __new__ = interp2app(W_Kqueue.descr__new__.im_func),
    fromfd = interp2app(W_Kqueue.descr_fromfd.im_func, as_classmethod=True),

    closed = GetSetProperty(W_Kqueue.descr_get_closed),
    fileno = interp2app(W_Kqueue.descr_fileno),

    close = interp2app(W_Kqueue.descr_close),
    control = interp2app(W_Kqueue.descr_control),
)
W_Kqueue.typedef.acceptable_as_base_class = False


class W_Kevent(Wrappable):
    def __init__(self, space):
        self.event = lltype.nullptr(kevent)

    def __del__(self):
        if self.event:
            lltype.free(self.event, flavor="raw")

    @unwrap_spec(filter=int, flags=int, fflags=int, data=int, udata=int)
    def descr__init__(self, space, w_ident, filter=KQ_FILTER_READ, flags=KQ_EV_ADD, fflags=0, data=0, udata=0):
        ident = space.c_filedescriptor_w(w_ident)

        self.event = lltype.malloc(kevent, flavor="raw")
        rffi.setintfield(self.event, "c_ident", ident)
        rffi.setintfield(self.event, "c_filter", filter)
        rffi.setintfield(self.event, "c_flags", flags)
        rffi.setintfield(self.event, "c_fflags", fflags)
        rffi.setintfield(self.event, "c_data", data)
        self.event.c_udata = rffi.cast(rffi.VOIDP, udata)

    def _compare_all_fields(self, other, op):
        ## FIXME: handle udata ()
        ## assert s_attr.is_constant(), "getattr on ptr %r with non-constant field-name" % p.ll_ptrtype
        #for field in ["ident", "filter", "flags", "fflags", "data", "udata"]:
        for field in ["ident", "filter", "flags", "fflags", "data"]:
            lhs = getattr(self.event, "c_%s" % field)
            rhs = getattr(other.event, "c_%s" % field)
            if op == "eq":
                if lhs != rhs:
                    return False
            elif op == "lt":
                if lhs < rhs:
                    return True
            elif op == "ge":
                if lhs >= rhs:
                    return True
            else:
                assert False

        if op == "eq":
            return True
        elif op == "lt":
            return False
        elif op == "ge":
            return False

    def compare_all_fields(self, space, other, op):
        if not space.interp_w(W_Kevent, other):
            return space.w_NotImplemented
        return space.wrap(self._compare_all_fields(other, op))

    def descr__eq__(self, space, w_other):
        return self.compare_all_fields(space, w_other, "eq")

    def descr__lt__(self, space, w_other):
        return self.compare_all_fields(space, w_other, "lt")

    def descr__ge__(self, space, w_other):
        return self.compare_all_fields(space, w_other, "ge")

    def descr_get_ident(self, space):
        return space.wrap(self.event.c_ident)

    def descr_get_filter(self, space):
        return space.wrap(self.event.c_filter)

    def descr_get_flags(self, space):
        return space.wrap(self.event.c_flags)

    def descr_get_fflags(self, space):
        return space.wrap(self.event.c_fflags)

    def descr_get_data(self, space):
        return space.wrap(self.event.c_data)

    def descr_get_udata(self, space):
        return space.wrap(rffi.cast(rffi.INT, self.event.c_udata))


W_Kevent.typedef = TypeDef("select.kevent",
    __new__ = generic_new_descr(W_Kevent),
    __init__ = interp2app(W_Kevent.descr__init__),
    __eq__ = interp2app(W_Kevent.descr__eq__),
    __lt__ = interp2app(W_Kevent.descr__lt__),
    __ge__ = interp2app(W_Kevent.descr__ge__),

    ident = GetSetProperty(W_Kevent.descr_get_ident),
    filter = GetSetProperty(W_Kevent.descr_get_filter),
    flags = GetSetProperty(W_Kevent.descr_get_flags),
    fflags = GetSetProperty(W_Kevent.descr_get_fflags),
    data = GetSetProperty(W_Kevent.descr_get_data),
    udata = GetSetProperty(W_Kevent.descr_get_udata),
)
W_Kevent.typedef.acceptable_as_base_class = False
