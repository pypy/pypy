from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError, operationerrfmt, exception_from_errno
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef, generic_new_descr, GetSetProperty
from pypy.rlib._rsocket_rffi import socketclose
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rpython.tool import rffi_platform
from pypy.translator.tool.cbuild import ExternalCompilationInfo


eci = ExternalCompilationInfo(
    includes = ["sys/types.h",
                "sys/event.h",
                "sys/time.h"],
)


class CConfig:
    _compilation_info_ = eci


CConfig.kevent = rffi_platform.Struct("struct kevent", [
    ("ident", rffi.UINTPTR_T),
    ("filter", rffi.SHORT),
    ("flags", rffi.USHORT),
    ("fflags", rffi.UINT),
    ("data", rffi.INTPTR_T),
    ("udata", rffi.VOIDP),
])


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
#    "KQ_FILTER_NETDEV": None, # deprecated on FreeBSD .. no longer defined
    "KQ_FILTER_SIGNAL": "EVFILT_SIGNAL",
    "KQ_FILTER_TIMER": "EVFILT_TIMER",
    "KQ_EV_ADD": "EV_ADD",
    "KQ_EV_DELETE": "EV_DELETE",
    "KQ_EV_ENABLE": "EV_ENABLE",
    "KQ_EV_DISABLE": "EV_DISABLE",
    "KQ_EV_ONESHOT": "EV_ONESHOT",
    "KQ_EV_CLEAR": "EV_CLEAR",
#    "KQ_EV_SYSFLAGS": None, # Python docs says "internal event" .. not defined on FreeBSD
#    "KQ_EV_FLAG1": None, # Python docs says "internal event" .. not defined on FreeBSD
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


syscall_kqueue = rffi.llexternal(
    "kqueue",
    [],
    rffi.INT,
    compilation_info=eci
)

syscall_kevent = rffi.llexternal(
    "kevent",
    [rffi.INT,
     lltype.Ptr(rffi.CArray(kevent)),
     rffi.INT,
     lltype.Ptr(rffi.CArray(kevent)),
     rffi.INT,
     lltype.Ptr(timespec)
    ],
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
            kqfd = self.kqfd
            self.kqfd = -1
            socketclose(kqfd)

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

        with lltype.scoped_alloc(rffi.CArray(kevent), changelist_len) as changelist:
            with lltype.scoped_alloc(rffi.CArray(kevent), max_events) as eventlist:
                with lltype.scoped_alloc(timespec) as timeout:

                    if not space.is_w(w_timeout, space.w_None):
                        _timeout = space.float_w(w_timeout)
                        if _timeout < 0:
                            raise operationerrfmt(space.w_ValueError,
                                "Timeout must be None or >= 0, got %s", str(_timeout)
                            )
                        sec = int(_timeout)
                        nsec = int(1e9 * (_timeout - sec))
                        rffi.setintfield(timeout, 'c_tv_sec', sec)
                        rffi.setintfield(timeout, 'c_tv_nsec', nsec)
                        ptimeout = timeout
                    else:
                        ptimeout = lltype.nullptr(timespec)

                    if not space.is_w(w_changelist, space.w_None):
                        i = 0
                        for w_ev in space.listview(w_changelist):
                            ev = space.interp_w(W_Kevent, w_ev)
                            changelist[i].c_ident = ev.event.c_ident
                            changelist[i].c_filter = ev.event.c_filter
                            changelist[i].c_flags = ev.event.c_flags
                            changelist[i].c_fflags = ev.event.c_fflags
                            changelist[i].c_data = ev.event.c_data
                            changelist[i].c_udata = ev.event.c_udata
                            i += 1
                        pchangelist = changelist
                    else:
                        pchangelist = lltype.nullptr(rffi.CArray(kevent))

                    nfds = syscall_kevent(self.kqfd,
                                          pchangelist,
                                          changelist_len,
                                          eventlist,
                                          max_events,
                                          ptimeout)
                    if nfds < 0:
                        raise exception_from_errno(space, space.w_IOError)
                    else:
                        elist_w = [None] * nfds
                        for i in xrange(nfds):

                            evt = eventlist[i]

                            w_event = W_Kevent(space)
                            w_event.event = lltype.malloc(kevent, flavor="raw")
                            w_event.event.c_ident = evt.c_ident
                            w_event.event.c_filter = evt.c_filter
                            w_event.event.c_flags = evt.c_flags
                            w_event.event.c_fflags = evt.c_fflags
                            w_event.event.c_data = evt.c_data
                            w_event.event.c_udata = evt.c_udata

                            elist_w[i] = w_event

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

    @unwrap_spec(filter=int, flags='c_uint', fflags='c_uint', data=int, udata='c_uint')
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
        l_ident = self.event.c_ident
        r_ident = other.event.c_ident
        l_filter = rffi.cast(lltype.Signed, self.event.c_filter)
        r_filter = rffi.cast(lltype.Signed, other.event.c_filter)
        l_flags = rffi.cast(lltype.Unsigned, self.event.c_flags)
        r_flags = rffi.cast(lltype.Unsigned, other.event.c_flags)
        l_fflags = rffi.cast(lltype.Unsigned, self.event.c_fflags)
        r_fflags = rffi.cast(lltype.Unsigned, other.event.c_fflags)
        l_data = self.event.c_data
        r_data = other.event.c_data
        l_udata = rffi.cast(lltype.Unsigned, self.event.c_udata)
        r_udata = rffi.cast(lltype.Unsigned, other.event.c_udata)

        if op == "eq":
            return l_ident == r_ident and \
                   l_filter == r_filter and \
                   l_flags == r_flags and \
                   l_fflags == r_fflags and \
                   l_data == r_data and \
                   l_udata == r_udata
        elif op == "lt":
            return (l_ident < r_ident) or \
                   (l_ident == r_ident and l_filter < r_filter) or \
                   (l_ident == r_ident and l_filter == r_filter and l_flags < r_flags) or \
                   (l_ident == r_ident and l_filter == r_filter and l_flags == r_flags and l_fflags < r_fflags) or \
                   (l_ident == r_ident and l_filter == r_filter and l_flags == r_flags and l_fflags == r_fflags and l_data < r_data) or \
                   (l_ident == r_ident and l_filter == r_filter and l_flags == r_flags and l_fflags == r_fflags and l_data == r_data and l_udata < r_udata)
        elif op == "gt":
            return (l_ident > r_ident) or \
                   (l_ident == r_ident and l_filter > r_filter) or \
                   (l_ident == r_ident and l_filter == r_filter and l_flags > r_flags) or \
                   (l_ident == r_ident and l_filter == r_filter and l_flags == r_flags and l_fflags > r_fflags) or \
                   (l_ident == r_ident and l_filter == r_filter and l_flags == r_flags and l_fflags == r_fflags and l_data > r_data) or \
                   (l_ident == r_ident and l_filter == r_filter and l_flags == r_flags and l_fflags == r_fflags and l_data == r_data and l_udata > r_udata)
        else:
            assert False

    def compare_all_fields(self, space, other, op):
        if not space.interp_w(W_Kevent, other):
            if op == "eq":
                return False
            elif op == "ne":
                return True
            else:
                raise OperationError(space.w_TypeError, space.wrap('cannot compare kevent to incompatible type'))
        return self._compare_all_fields(space.interp_w(W_Kevent, other), op)

    def descr__eq__(self, space, w_other):
        return space.wrap(self.compare_all_fields(space, w_other, "eq"))

    def descr__ne__(self, space, w_other):
        return space.wrap(not self.compare_all_fields(space, w_other, "eq"))

    def descr__le__(self, space, w_other):
        return space.wrap(not self.compare_all_fields(space, w_other, "gt"))

    def descr__lt__(self, space, w_other):
        return space.wrap(self.compare_all_fields(space, w_other, "lt"))

    def descr__ge__(self, space, w_other):
        return space.wrap(not self.compare_all_fields(space, w_other, "lt"))

    def descr__gt__(self, space, w_other):
        return space.wrap(self.compare_all_fields(space, w_other, "gt"))

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
        return space.wrap(rffi.cast(rffi.SIZE_T, self.event.c_udata))


W_Kevent.typedef = TypeDef("select.kevent",
    __new__ = generic_new_descr(W_Kevent),
    __init__ = interp2app(W_Kevent.descr__init__),
    __eq__ = interp2app(W_Kevent.descr__eq__),
    __ne__ = interp2app(W_Kevent.descr__ne__),
    __le__ = interp2app(W_Kevent.descr__le__),
    __lt__ = interp2app(W_Kevent.descr__lt__),
    __ge__ = interp2app(W_Kevent.descr__ge__),
    __gt__ = interp2app(W_Kevent.descr__gt__),

    ident = GetSetProperty(W_Kevent.descr_get_ident),
    filter = GetSetProperty(W_Kevent.descr_get_filter),
    flags = GetSetProperty(W_Kevent.descr_get_flags),
    fflags = GetSetProperty(W_Kevent.descr_get_fflags),
    data = GetSetProperty(W_Kevent.descr_get_data),
    udata = GetSetProperty(W_Kevent.descr_get_udata),
)
W_Kevent.typedef.acceptable_as_base_class = False
