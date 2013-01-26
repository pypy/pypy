from __future__ import with_statement
from pypy.interpreter.error import OperationError, exception_from_errno
from pypy.interpreter.gateway import unwrap_spec
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib import jit, rposix
from pypy.rlib.rarithmetic import intmask
from pypy.rlib.rsignal import *


@unwrap_spec(signum=int)
def getsignal(space, signum):
    """
    getsignal(sig) -> action

    Return the current action for the given signal.  The return value can be:
    SIG_IGN -- if the signal is being ignored
    SIG_DFL -- if the default action for the signal is in effect
    None -- if an unknown handler is in effect (XXX UNIMPLEMENTED)
    anything else -- the callable Python object used as a handler
    """
    check_signum_in_range(space, signum)
    action = space.check_signal_action
    if signum in action.handlers_w:
        return action.handlers_w[signum]
    return space.wrap(SIG_DFL)

def default_int_handler(space, w_signum, w_frame):
    """
    default_int_handler(...)

    The default handler for SIGINT installed by Python.
    It raises KeyboardInterrupt.
    """
    raise OperationError(space.w_KeyboardInterrupt,
                         space.w_None)

@jit.dont_look_inside
@unwrap_spec(timeout=int)
def alarm(space, timeout):
    return space.wrap(c_alarm(timeout))

@jit.dont_look_inside
def pause(space):
    c_pause()
    return space.w_None

def check_signum_exists(space, signum):
    if signum in signal_values:
        return
    raise OperationError(space.w_ValueError,
                         space.wrap("invalid signal value"))

def check_signum_in_range(space, signum):
    if 1 <= signum < NSIG:
        return
    raise OperationError(space.w_ValueError,
                         space.wrap("signal number out of range"))


@jit.dont_look_inside
@unwrap_spec(signum=int)
def signal(space, signum, w_handler):
    """
    signal(sig, action) -> action

    Set the action for the given signal.  The action can be SIG_DFL,
    SIG_IGN, or a callable Python object.  The previous action is
    returned.  See getsignal() for possible return values.

    *** IMPORTANT NOTICE ***
    A signal handler function is called with two arguments:
    the first is the signal number, the second is the interrupted stack frame.
    """
    ec      = space.getexecutioncontext()
    main_ec = space.threadlocals.getmainthreadvalue()

    old_handler = getsignal(space, signum)

    if ec is not main_ec:
        raise OperationError(space.w_ValueError,
                             space.wrap("signal() must be called from the "
                                        "main thread"))
    action = space.check_signal_action
    if space.eq_w(w_handler, space.wrap(SIG_DFL)):
        pypysig_default(signum)
    elif space.eq_w(w_handler, space.wrap(SIG_IGN)):
        pypysig_ignore(signum)
    else:
        if not space.is_true(space.callable(w_handler)):
            raise OperationError(space.w_TypeError,
                                 space.wrap("'handler' must be a callable "
                                            "or SIG_DFL or SIG_IGN"))
        pypysig_setflag(signum)
    action.handlers_w[signum] = w_handler
    return old_handler

@jit.dont_look_inside
@unwrap_spec(fd=int)
def set_wakeup_fd(space, fd):
    """Sets the fd to be written to (with '\0') when a signal
    comes in.  Returns the old fd.  A library can use this to
    wakeup select or poll.  The previous fd is returned.
    
    The fd must be non-blocking.
    """
    if space.config.objspace.usemodules.thread:
        main_ec = space.threadlocals.getmainthreadvalue()
        ec = space.getexecutioncontext()
        if ec is not main_ec:
            raise OperationError(
                space.w_ValueError,
                space.wrap("set_wakeup_fd only works in main thread"))
    old_fd = pypysig_set_wakeup_fd(fd)
    return space.wrap(intmask(old_fd))

@jit.dont_look_inside
@unwrap_spec(signum=int, flag=int)
def siginterrupt(space, signum, flag):
    check_signum_exists(space, signum)
    if rffi.cast(lltype.Signed, c_siginterrupt(signum, flag)) < 0:
        errno = rposix.get_errno()
        raise OperationError(space.w_RuntimeError, space.wrap(errno))


#__________________________________________________________

def timeval_from_double(d, timeval):
    rffi.setintfield(timeval, 'c_tv_sec', int(d))
    rffi.setintfield(timeval, 'c_tv_usec', int((d - int(d)) * 1000000))

def double_from_timeval(tv):
    return rffi.getintfield(tv, 'c_tv_sec') + (
        rffi.getintfield(tv, 'c_tv_usec') / 1000000.0)

def itimer_retval(space, val):
    w_value = space.wrap(double_from_timeval(val.c_it_value))
    w_interval = space.wrap(double_from_timeval(val.c_it_interval))
    return space.newtuple([w_value, w_interval])

class Cache:
    def __init__(self, space):
        self.w_itimererror = space.new_exception_class("signal.ItimerError",
                                                       space.w_IOError)

def get_itimer_error(space):
    return space.fromcache(Cache).w_itimererror

@jit.dont_look_inside
@unwrap_spec(which=int, first=float, interval=float)
def setitimer(space, which, first, interval=0):
    """setitimer(which, seconds[, interval])
    
    Sets given itimer (one of ITIMER_REAL, ITIMER_VIRTUAL
    or ITIMER_PROF) to fire after value seconds and after
    that every interval seconds.
    The itimer can be cleared by setting seconds to zero.
    
    Returns old values as a tuple: (delay, interval).
    """
    with lltype.scoped_alloc(itimervalP.TO, 1) as new:

        timeval_from_double(first, new[0].c_it_value)
        timeval_from_double(interval, new[0].c_it_interval)

        with lltype.scoped_alloc(itimervalP.TO, 1) as old:

            ret = c_setitimer(which, new, old)
            if ret != 0:
                raise exception_from_errno(space, get_itimer_error(space))


            return itimer_retval(space, old[0])

@jit.dont_look_inside
@unwrap_spec(which=int)
def getitimer(space, which):
    """getitimer(which)
    
    Returns current value of given itimer.
    """
    with lltype.scoped_alloc(itimervalP.TO, 1) as old:

        c_getitimer(which, old)

        return itimer_retval(space, old[0])
