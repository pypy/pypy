from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import W_Root, ObjSpace
from pypy.interpreter.executioncontext import AsyncAction, AbstractActionFlag
from pypy.rlib.rarithmetic import LONG_BIT, intmask
import signal as cpy_signal
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.translator.tool.cbuild import ExternalCompilationInfo
import py
from pypy.tool import autopath

def setup():
    for key, value in cpy_signal.__dict__.items():
        if key.startswith('SIG') and isinstance(value, int):
            globals()[key] = value
            yield key

NSIG    = cpy_signal.NSIG
SIG_DFL = cpy_signal.SIG_DFL
SIG_IGN = cpy_signal.SIG_IGN
signal_names = list(setup())

eci = ExternalCompilationInfo(
    includes = ['stdlib.h', 'src/signals.h'],
    separate_module_sources = ['#include <src/signals.h>'],
    include_dirs = [str(py.path.local(autopath.pypydir).join('translator', 'c'))],
    export_symbols = ['pypysig_poll', 'pypysig_default',
                      'pypysig_ignore', 'pypysig_setflag',
                      'pypysig_get_occurred', 'pypysig_set_occurred'],
)

def external(name, args, result, **kwds):
    return rffi.llexternal(name, args, result, compilation_info=eci, **kwds)

pypysig_ignore = external('pypysig_ignore', [rffi.INT], lltype.Void)
pypysig_default = external('pypysig_default', [rffi.INT], lltype.Void)
pypysig_setflag = external('pypysig_setflag', [rffi.INT], lltype.Void)
pypysig_poll = external('pypysig_poll', [], rffi.INT, threadsafe=False)
# don't bother releasing the GIL around a call to pypysig_poll: it's
# pointless and a performance issue

pypysig_get_occurred = external('pypysig_get_occurred', [],
                                lltype.Signed, _nowrapper=True)
pypysig_set_occurred = external('pypysig_set_occurred', [lltype.Signed],
                                lltype.Void, _nowrapper=True)


class SignalActionFlag(AbstractActionFlag):
    get = staticmethod(pypysig_get_occurred)
    set = staticmethod(pypysig_set_occurred)


class CheckSignalAction(AsyncAction):
    """An action that is automatically invoked when a signal is received."""

    # The C-level signal handler sets the highest bit of pypysig_occurred:
    bitmask = intmask(1 << (LONG_BIT-1))

    def __init__(self, space):
        AsyncAction.__init__(self, space)
        self.handlers_w = {}
        if space.config.objspace.usemodules.thread:
            # need a helper action in case signals arrive in a non-main thread
            self.pending_signals = {}
            self.reissue_signal_action = ReissueSignalAction(space)
            space.actionflag.register_action(self.reissue_signal_action)
        else:
            self.reissue_signal_action = None

    def perform(self, executioncontext):
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

    def report_signal(self, n):
        try:
            w_handler = self.handlers_w[n]
        except KeyError:
            return    # no handler, ignore signal
        # re-install signal handler, for OSes that clear it
        pypysig_setflag(n)
        # invoke the app-level handler
        space = self.space
        ec = space.getexecutioncontext()
        try:
            w_frame = ec.framestack.top()
        except IndexError:
            w_frame = space.w_None
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

    def perform(self, executioncontext):
        main_ec = self.space.threadlocals.getmainthreadvalue()
        if executioncontext is main_ec:
            # now running in the main thread: we can really report the signals
            self.space.check_signal_action.report_pending_signals()
        else:
            # still running in some other thread: try again later
            self.fire_after_thread_switch()


def getsignal(space, signum):
    """
    getsignal(sig) -> action

    Return the current action for the given signal.  The return value can be:
    SIG_IGN -- if the signal is being ignored
    SIG_DFL -- if the default action for the signal is in effect
    None -- if an unknown handler is in effect (XXX UNIMPLEMENTED)
    anything else -- the callable Python object used as a handler
    """
    action = space.check_signal_action
    if signum in action.handlers_w:
        return action.handlers_w[signum]
    return space.wrap(SIG_DFL)
getsignal.unwrap_spec = [ObjSpace, int]


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
signal.unwrap_spec = [ObjSpace, int, W_Root]
