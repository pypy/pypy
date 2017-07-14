from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.error import OperationError
from pypy.module._minimal_curses import fficurses
from rpython.rtyper.lltypesystem import lltype, rffi


class ModuleInfo:
    def __init__(self, space):
        self.setupterm_called = False

def check_setup_invoked(space):
    if not space.fromcache(ModuleInfo).setupterm_called:
        raise curses_error(space, "must call (at least) setupterm() first")


def curses_error(space, errmsg):
    w_module = space.getbuiltinmodule('_minimal_curses')
    w_exception_class = space.getattr(w_module, space.newtext('error'))
    w_exception = space.call_function(w_exception_class, space.newtext(errmsg))
    return OperationError(w_exception_class, w_exception)


@unwrap_spec(fd=int)
def setupterm(space, w_termname=None, fd=-1):
    if fd == -1:
        w_stdout = space.getattr(space.getbuiltinmodule('sys'),
                                 space.newtext('stdout'))
        fd = space.int_w(space.call_function(space.getattr(w_stdout,
                                             space.newtext('fileno'))))
    if space.is_none(w_termname):
        termname = None
    else:
        termname = space.text_w(w_termname)

    with rffi.scoped_str2charp(termname) as ll_term:
        fd = rffi.cast(rffi.INT, fd)
        ll_errmsg = fficurses.rpy_curses_setupterm(ll_term, fd)
    if ll_errmsg:
        raise curses_error(space, rffi.charp2str(ll_errmsg))

    space.fromcache(ModuleInfo).setupterm_called = True

@unwrap_spec(capname='text')
def tigetstr(space, capname):
    check_setup_invoked(space)
    with rffi.scoped_str2charp(capname) as ll_capname:
        ll_result = fficurses.rpy_curses_tigetstr(ll_capname)
        if ll_result:
            return space.newbytes(rffi.charp2str(ll_result))
        else:
            return space.w_None

@unwrap_spec(s='bufferstr')
def tparm(space, s, args_w):
    check_setup_invoked(space)
    args = [space.int_w(a) for a in args_w]
    # nasty trick stolen from CPython
    x0 = args[0] if len(args) > 0 else 0
    x1 = args[1] if len(args) > 1 else 0
    x2 = args[2] if len(args) > 2 else 0
    x3 = args[3] if len(args) > 3 else 0
    x4 = args[4] if len(args) > 4 else 0
    x5 = args[5] if len(args) > 5 else 0
    x6 = args[6] if len(args) > 6 else 0
    x7 = args[7] if len(args) > 7 else 0
    x8 = args[8] if len(args) > 8 else 0
    with rffi.scoped_str2charp(s) as ll_str:
        ll_result = fficurses.rpy_curses_tparm(ll_str, x0, x1, x2, x3,
                                               x4, x5, x6, x7, x8)
        if ll_result:
            return space.newbytes(rffi.charp2str(ll_result))
        else:
            raise curses_error(space, "tparm() returned NULL")
