from __future__ import print_function

import signal as cpy_signal
import sys
import os
import errno

from pypy.interpreter.error import (
    OperationError, exception_from_saved_errno, oefmt)
from pypy.interpreter.executioncontext import (AsyncAction, AbstractActionFlag,
    PeriodicAsyncAction)
from pypy.interpreter.gateway import unwrap_spec

from rpython.rlib import jit, rposix, rgc
from rpython.rlib.objectmodel import we_are_translated
from rpython.rlib.rarithmetic import intmask
from rpython.rlib.rsignal import *
from rpython.rtyper.lltypesystem import lltype, rffi


WIN32 = sys.platform == 'win32'


class SignalActionFlag(AbstractActionFlag):
    # This class uses the C-level pypysig_counter variable as the tick
    # counter.  The C-level signal handler will reset it to -1 whenever
    # a signal is received.  This causes CheckSignalAction.perform() to
    # be called.

    def get_ticker(self):
        p = pypysig_getaddr_occurred()
        return p.c_value

    def reset_ticker(self, value):
        p = pypysig_getaddr_occurred()
        p.c_value = value

    def rearm_ticker(self):
        p = pypysig_getaddr_occurred()
        p.c_value = -1

    def decrement_ticker(self, by):
        p = pypysig_getaddr_occurred()
        value = p.c_value
        if self.has_bytecode_counter:    # this 'if' is constant-folded
            if jit.isconstant(by) and by == 0:
                pass     # normally constant-folded too
            else:
                value -= by
                p.c_value = value
        return value


class CheckSignalAction(PeriodicAsyncAction):
    """An action that is automatically invoked when a signal is received."""

    # Note that this is a PeriodicAsyncAction: it means more precisely
    # that it is called whenever the C-level ticker becomes < 0.
    # Without threads, it is only ever set to -1 when we receive a
    # signal.  With threads, it also decrements steadily (but slowly).

    def __init__(self, space):
        "NOT_RPYTHON"
        AsyncAction.__init__(self, space)
        self.pending_signal = -1
        self.fire_in_another_thread = False

        @rgc.no_collect
        def _after_thread_switch():
            # if threadlocals is the fake ThreadLocals from miscutils, we
            # cannot ever end up here, it's only called after a thread switch
            ec = self.space.threadlocals.get_ec()
            if ec is not None and ec.w_async_exception_type:
                self.space.actionflag.rearm_ticker() # ensure perform is called
                return
            if self.fire_in_another_thread:
                if self.space.threadlocals.signals_enabled():
                    self.fire_in_another_thread = False
                    self.space.actionflag.rearm_ticker()
                    # this occurs when we just switched to the main thread
                    # and there is a signal pending: we force the ticker to
                    # -1, which should ensure perform() is called quickly.
        self._after_thread_switch = _after_thread_switch
        # ^^^ so that 'self._after_thread_switch' can be annotated as a
        # constant

    def startup(self, space):
        # this is translated
        if space.config.objspace.usemodules.thread:
            from rpython.rlib import rgil
            rgil.invoke_after_thread_switch(self._after_thread_switch)

    def perform(self, executioncontext, frame):
        w_exc = executioncontext.w_async_exception_type
        if w_exc is not None:
            executioncontext.w_async_exception_type = None
            raise oefmt(w_exc, "asynchronous exception triggered from another thread")
        self._poll_for_signals()

    @jit.dont_look_inside
    def _poll_for_signals(self):
        # Poll for the next signal, if any
        n = self.pending_signal
        p = pypysig_getaddr_occurred_fullstruct()
        if p.c_debugger_pending_call:
            path = rffi.charp2str(p.c_debugger_script_path)
            p.c_debugger_pending_call = 0
            run_debugger(self.space, path)
            return
        if n < 0:
            n = pypysig_poll()
        while n >= 0:
            if self.space.threadlocals.signals_enabled():
                # If we are in the main thread, report the signal now,
                # and poll more
                self.pending_signal = -1
                report_signal(self.space, n)
                n = self.pending_signal
                if n < 0:
                    n = pypysig_poll()
            else:
                # Otherwise, arrange for perform() to be called again
                # after we switch to the main thread.
                self.pending_signal = n
                self.fire_in_another_thread = True
                break

    def set_interrupt(self):
        "Simulates the effect of a SIGINT signal arriving"
        if not we_are_translated():
            self.pending_signal = cpy_signal.SIGINT
            # ^^^ may override another signal, but it's just for testing
            self.fire_in_another_thread = True
        else:
            pypysig_pushback(cpy_signal.SIGINT)

# ____________________________________________________________


class Handlers:
    def __init__(self, space):
        self.handlers_w = {}
        for signum in range(1, NSIG):
            if WIN32 and signum not in signal_values:
                self.handlers_w[signum] = space.w_None
            else:
                self.handlers_w[signum] = space.newint(SIG_DFL)

def _get_handlers(space):
    return space.fromcache(Handlers).handlers_w


def report_signal(space, n):
    handlers_w = _get_handlers(space)
    try:
        w_handler = handlers_w[n]
    except KeyError:
        return    # no handler, ignore signal
    if not space.is_true(space.callable(w_handler)):
        return    # w_handler is SIG_IGN or SIG_DFL?
    # re-install signal handler, for OSes that clear it
    pypysig_reinstall(n)
    # invoke the app-level handler
    ec = space.getexecutioncontext()
    w_frame = ec.gettopframe_nohidden()
    space.call_function(w_handler, space.newint(n), w_frame)

def run_debugger(space, path):
    from pypy.interpreter.streamutil import wrap_streamerror
    from pypy.interpreter.eval import Code
    from rpython.rlib import streamio
    w_pypymod = space.getbuiltinmodule('__pypy__')
    if space.is_true(space.getattr(w_pypymod, space.newtext('_pypy_disable_remote_debugger'))):
        return
    try:
        w_file = space.call_method(space.newbytes(path), 'decode', space.newtext('utf-8'))
        msg = "Executing remote debugger script "
        w_msg = space.add(space.newtext(msg), w_file)
        w_msg = space.add(w_msg, space.newtext('\n'))
        space.call_method(space.getattr(space.sys, space.newtext('stdout')), 'write', w_msg)
        try:
            stream = streamio.open_file_as_stream(path, 'r')
            source = stream.readall()
        except streamio.StreamErrors as e:
            raise wrap_streamerror(space, e)
        ec = space.getexecutioncontext()
        pycode = ec.compiler.compile(source, path, 'exec', 0)
        w_globals = space.newdict()
        pycode.exec_code(space, w_globals, w_globals)
    except OperationError as e:
        e.write_unraisable(space, "in remote debugger invocation")


@unwrap_spec(signum=int)
def getsignal(space, signum):
    """
    getsignal(sig) -> action

    Return the current action for the given signal.  The return value can be:
    SIG_IGN -- if the signal is being ignored
    SIG_DFL -- if the default action for the signal is in effect
    None -- if an unknown handler is in effect
    anything else -- the callable Python object used as a handler
    """
    check_signum_in_range(space, signum)
    handlers_w = _get_handlers(space)
    return handlers_w[signum]


def default_int_handler(space, args_w):
    """
    default_int_handler(...)

    The default handler for SIGINT installed by Python.
    It raises KeyboardInterrupt.
    """
    # issue #2780: accept and ignore any non-keyword arguments
    raise OperationError(space.w_KeyboardInterrupt, space.w_None)


@jit.dont_look_inside
@unwrap_spec(timeout=int)
def alarm(space, timeout):
    """alarm(seconds)

    Arrange for SIGALRM to arrive after the given number of seconds.
    """
    return space.newint(c_alarm(timeout))


@jit.dont_look_inside
def pause(space):
    """pause()

    Wait until a signal arrives.
    """
    c_pause()
    return space.w_None


def check_signum_in_range(space, signum):
    if 1 <= signum < NSIG:
        return
    raise oefmt(space.w_ValueError, "signal number out of range")


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
    if WIN32 and signum not in signal_values:
        raise oefmt(space.w_ValueError, "invalid signal value")
    if not space.threadlocals.signals_enabled():
        raise oefmt(space.w_ValueError,
                    "signal only works in main thread or with "
                    "__pypy__.thread.enable_signals()")
    check_signum_in_range(space, signum)

    if space.eq_w(w_handler, space.newint(SIG_DFL)):
        pypysig_default(signum)
    elif space.eq_w(w_handler, space.newint(SIG_IGN)):
        pypysig_ignore(signum)
    else:
        if not space.is_true(space.callable(w_handler)):
            raise oefmt(space.w_TypeError,
                        "'handler' must be a callable or SIG_DFL or SIG_IGN")
        pypysig_setflag(signum)

    handlers_w = _get_handlers(space)
    old_handler = handlers_w[signum]
    handlers_w[signum] = w_handler
    return old_handler


@jit.dont_look_inside
@unwrap_spec(fd=int)
def set_wakeup_fd(space, fd):
    """Sets the fd to be written to (with '\0') when a signal
    comes in.  Returns the old fd.  A library can use this to
    wakeup select or poll.  The previous fd is returned.

    The fd must be non-blocking.
    """
    if not space.threadlocals.signals_enabled():
        raise oefmt(space.w_ValueError,
                    "set_wakeup_fd only works in main thread or with "
                    "__pypy__.thread.enable_signals()")
    if fd != -1:
        try:
            os.fstat(fd)
        except OSError as e:
            if e.errno == errno.EBADF:
                raise oefmt(space.w_ValueError, "invalid fd")
    old_fd = pypysig_set_wakeup_fd(fd, True)
    return space.newint(intmask(old_fd))


@jit.dont_look_inside
@unwrap_spec(signum=int, flag=int)
def siginterrupt(space, signum, flag):
    """siginterrupt(sig, flag) -> None

    change system call restart behaviour: if flag is False, system calls
    will be restarted when interrupted by signal sig, else system calls
    will be interrupted.
    """
    check_signum_in_range(space, signum)
    if rffi.cast(lltype.Signed, c_siginterrupt(signum, flag)) < 0:
        errno = rposix.get_saved_errno()
        raise OperationError(space.w_RuntimeError, space.newint(errno))


#__________________________________________________________

def timeval_from_double(d, timeval):
    c_tv_sec = int(d)
    c_tv_usec = int((d - int(d)) * 1000000)
    # Don't disable the timer if the computation above rounds down to zero.
    if d > 0.0 and c_tv_sec == 0 and c_tv_usec == 0:
        c_tv_usec = 1
    rffi.setintfield(timeval, 'c_tv_sec', c_tv_sec)
    rffi.setintfield(timeval, 'c_tv_usec', c_tv_usec)


def double_from_timeval(tv):
    return rffi.getintfield(tv, 'c_tv_sec') + (
        rffi.getintfield(tv, 'c_tv_usec') / 1000000.0)


def itimer_retval(space, val):
    w_value = space.newfloat(double_from_timeval(val.c_it_value))
    w_interval = space.newfloat(double_from_timeval(val.c_it_interval))
    return space.newtuple2(w_value, w_interval)


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
                raise exception_from_saved_errno(space, get_itimer_error(space))

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
