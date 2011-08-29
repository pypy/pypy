from __future__ import with_statement
from pypy.interpreter.error import OperationError, exception_from_errno
from pypy.interpreter.executioncontext import AsyncAction, AbstractActionFlag
from pypy.interpreter.executioncontext import PeriodicAsyncAction
from pypy.interpreter.gateway import unwrap_spec
import signal as cpy_signal
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rpython.tool import rffi_platform
from pypy.translator.tool.cbuild import ExternalCompilationInfo
import py
import sys
from pypy.tool import autopath
from pypy.rlib import jit, rposix
from pypy.rlib.rarithmetic import intmask

def setup():
    for key, value in cpy_signal.__dict__.items():
        if key.startswith('SIG') and isinstance(value, int):
            globals()[key] = value
            yield key

NSIG    = cpy_signal.NSIG
SIG_DFL = cpy_signal.SIG_DFL
SIG_IGN = cpy_signal.SIG_IGN
signal_names = list(setup())

includes = ['stdlib.h', 'src/signals.h']
if sys.platform != 'win32':
    includes.append('sys/time.h')

eci = ExternalCompilationInfo(
    includes = includes,
    separate_module_sources = ['#include <src/signals.h>'],
    include_dirs = [str(py.path.local(autopath.pypydir).join('translator', 'c'))],
    export_symbols = ['pypysig_poll', 'pypysig_default',
                      'pypysig_ignore', 'pypysig_setflag',
                      'pypysig_reinstall',
                      'pypysig_set_wakeup_fd',
                      'pypysig_getaddr_occurred'],
)

class CConfig:
    _compilation_info_ = eci

if sys.platform != 'win32':
    for name in """ITIMER_REAL ITIMER_VIRTUAL ITIMER_PROF""".split():
        setattr(CConfig, name, rffi_platform.DefinedConstantInteger(name))

    CConfig.timeval = rffi_platform.Struct(
        'struct timeval',
        [('tv_sec', rffi.LONG),
         ('tv_usec', rffi.LONG)])

    CConfig.itimerval = rffi_platform.Struct(
        'struct itimerval',
        [('it_value', CConfig.timeval),
         ('it_interval', CConfig.timeval)])

for k, v in rffi_platform.configure(CConfig).items():
    globals()[k] = v

def external(name, args, result, **kwds):
    return rffi.llexternal(name, args, result, compilation_info=eci,
                           sandboxsafe=True, **kwds)

pypysig_ignore = external('pypysig_ignore', [rffi.INT], lltype.Void)
pypysig_default = external('pypysig_default', [rffi.INT], lltype.Void)
pypysig_setflag = external('pypysig_setflag', [rffi.INT], lltype.Void)
pypysig_reinstall = external('pypysig_reinstall', [rffi.INT], lltype.Void)
pypysig_set_wakeup_fd = external('pypysig_set_wakeup_fd', [rffi.INT], rffi.INT)
pypysig_poll = external('pypysig_poll', [], rffi.INT, threadsafe=False)
# don't bother releasing the GIL around a call to pypysig_poll: it's
# pointless and a performance issue

# don't use rffi.LONGP because the JIT doesn't support raw arrays so far
struct_name = 'pypysig_long_struct'
LONG_STRUCT = lltype.Struct(struct_name, ('c_value', lltype.Signed),
                            hints={'c_name' : struct_name, 'external' : 'C'})
del struct_name

pypysig_getaddr_occurred = external('pypysig_getaddr_occurred', [],
                                    lltype.Ptr(LONG_STRUCT), _nowrapper=True,
                                    elidable_function=True)
c_alarm = external('alarm', [rffi.INT], rffi.INT)
c_pause = external('pause', [], rffi.INT)
c_siginterrupt = external('siginterrupt', [rffi.INT, rffi.INT], rffi.INT)

if sys.platform != 'win32':
    itimervalP = rffi.CArrayPtr(itimerval)
    c_setitimer = external('setitimer',
                           [rffi.INT, itimervalP, itimervalP], rffi.INT)
    c_getitimer = external('getitimer', [rffi.INT, itimervalP], rffi.INT)


class SignalActionFlag(AbstractActionFlag):
    # This class uses the C-level pypysig_counter variable as the tick
    # counter.  The C-level signal handler will reset it to -1 whenever
    # a signal is received.

    def get_ticker(self):
        p = pypysig_getaddr_occurred()
        return p.c_value

    def reset_ticker(self, value):
        p = pypysig_getaddr_occurred()
        p.c_value = value

    def decrement_ticker(self, by):
        p = pypysig_getaddr_occurred()
        value = p.c_value
        if self.has_bytecode_counter:    # this 'if' is constant-folded
            value -= by
            p.c_value = value
        return value


class CheckSignalAction(PeriodicAsyncAction):
    """An action that is automatically invoked when a signal is received."""

    def __init__(self, space):
        AsyncAction.__init__(self, space)
        self.handlers_w = {}
        if space.config.objspace.usemodules.thread:
            # need a helper action in case signals arrive in a non-main thread
            self.pending_signals = {}
            self.reissue_signal_action = ReissueSignalAction(space)
        else:
            self.reissue_signal_action = None

    def perform(self, executioncontext, frame):
        while True:
            n = pypysig_poll()
            if n < 0:
                break
            if self.reissue_signal_action is None:
                # no threads: we can report the signal immediately
                self.report_signal(n)
            else:
                main_ec = self.space.threadlocals.getmainthreadvalue()
                if executioncontext is main_ec:
                    # running in the main thread: we can report the
                    # signal immediately
                    self.report_signal(n)
                else:
                    # running in another thread: we need to hack a bit
                    self.pending_signals[n] = None
                    self.reissue_signal_action.fire_after_thread_switch()

    def set_interrupt(self):
        "Simulates the effect of a SIGINT signal arriving"
        n = cpy_signal.SIGINT
        if self.reissue_signal_action is None:
            self.report_signal(n)
        else:
            self.pending_signals[n] = None
            self.reissue_signal_action.fire_after_thread_switch()

    def report_signal(self, n):
        try:
            w_handler = self.handlers_w[n]
        except KeyError:
            return    # no handler, ignore signal
        # re-install signal handler, for OSes that clear it
        pypysig_reinstall(n)
        # invoke the app-level handler
        space = self.space
        ec = space.getexecutioncontext()
        w_frame = space.wrap(ec.gettopframe_nohidden())
        space.call_function(w_handler, space.wrap(n), w_frame)

    def report_pending_signals(self):
        # XXX this logic isn't so complicated but I have no clue how
        # to test it :-(
        pending_signals = self.pending_signals.keys()
        self.pending_signals.clear()
        try:
            while pending_signals:
                self.report_signal(pending_signals.pop())
        finally:
            # in case of exception, put the undelivered signals back
            # into the dict instead of silently swallowing them
            if pending_signals:
                for n in pending_signals:
                    self.pending_signals[n] = None
                self.reissue_signal_action.fire()


class ReissueSignalAction(AsyncAction):
    """A special action to help deliver signals to the main thread.  If
    a non-main thread caught a signal, this action fires after every
    thread switch until we land in the main thread.
    """

    def perform(self, executioncontext, frame):
        main_ec = self.space.threadlocals.getmainthreadvalue()
        if executioncontext is main_ec:
            # now running in the main thread: we can really report the signals
            self.space.check_signal_action.report_pending_signals()
        else:
            # still running in some other thread: try again later
            self.fire_after_thread_switch()


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
    check_signum(space, signum)
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

def check_signum(space, signum):
    if signum < 1 or signum >= NSIG:
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
        action.handlers_w[signum] = w_handler
    elif space.eq_w(w_handler, space.wrap(SIG_IGN)):
        pypysig_ignore(signum)
        action.handlers_w[signum] = w_handler
    else:
        if not space.is_true(space.callable(w_handler)):
            raise OperationError(space.w_TypeError,
                                 space.wrap("'handler' must be a callable "
                                            "or SIG_DFL or SIG_IGN"))
        pypysig_setflag(signum)
        action.handlers_w[signum] = w_handler
    return old_handler

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

@unwrap_spec(signum=int, flag=int)
def siginterrupt(space, signum, flag):
    check_signum(space, signum)
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
    with lltype.scoped_alloc(itimervalP.TO, 1) as old:

        c_getitimer(which, old)

        return itimer_retval(space, old[0])
