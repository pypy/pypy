from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import W_Root, ObjSpace
from pypy.interpreter.miscutils import Action
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
    include_dirs = [str(py.path.local(autopath.pypydir).join('translator', 'c'))]
)

def external(name, args, result, **kwds):
    return rffi.llexternal(name, args, result, compilation_info=eci, **kwds)

pypysig_ignore = external('pypysig_ignore', [rffi.INT], lltype.Void)
pypysig_default = external('pypysig_default', [rffi.INT], lltype.Void)
pypysig_setflag = external('pypysig_setflag', [rffi.INT], lltype.Void)
pypysig_poll = external('pypysig_poll', [], rffi.INT)

class CheckSignalAction(Action):
    """A repeatitive action at the space level, checking if the
    signal_occurred flag is set and if so, scheduling ReportSignal actions.
    """
    repeat = True

    def __init__(self, space):
        self.space = space
        self.handlers_w = {}

    def perform(self):
        while True:
            n = pypysig_poll()
            if n < 0:
                break
            main_ec = self.space.threadlocals.getmainthreadvalue()
            main_ec.add_pending_action(ReportSignal(self, n))

    def get(space):
        for action in space.pending_actions:
            if isinstance(action, CheckSignalAction):
                return action
        raise OperationError(space.w_RuntimeError,
                             space.wrap("lost CheckSignalAction"))
    get = staticmethod(get)


class ReportSignal(Action):
    """A one-shot action for the main thread's execution context."""

    def __init__(self, action, signum):
        self.action = action
        self.signum = signum

    def perform(self):
        try:
            w_handler = self.action.handlers_w[self.signum]
        except KeyError:
            return    # no handler, ignore signal
        # re-install signal handler, for OSes that clear it
        pypysig_setflag(self.signum)
        # invoke the app-level handler
        space = self.action.space
        ec = space.getexecutioncontext()
        try:
            w_frame = ec.framestack.top()
        except IndexError:
            w_frame = space.w_None
        space.call_function(w_handler, space.wrap(self.signum), w_frame)


def getsignal(space, signum):
    """
    getsignal(sig) -> action

    Return the current action for the given signal.  The return value can be:
    SIG_IGN -- if the signal is being ignored
    SIG_DFL -- if the default action for the signal is in effect
    None -- if an unknown handler is in effect (XXX UNIMPLEMENTED)
    anything else -- the callable Python object used as a handler
    """
    action = CheckSignalAction.get(space)
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
    action = CheckSignalAction.get(space)
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
