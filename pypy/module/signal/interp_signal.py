from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import W_Root, ObjSpace
from pypy.interpreter.miscutils import Action
import signal as cpy_signal


def setup():
    for key, value in cpy_signal.__dict__.items():
        if key.startswith('SIG') and isinstance(value, int):
            globals()[key] = value
            yield key

NSIG    = cpy_signal.NSIG
SIG_DFL = cpy_signal.SIG_DFL
SIG_IGN = cpy_signal.SIG_IGN
signal_names = list(setup())


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

def signal(space, signum, w_handler):
    ec      = space.getexecutioncontext()
    main_ec = space.threadlocals.getmainthreadvalue()
    if ec is not main_ec:
        raise OperationError(space.w_ValueError,
                             space.wrap("signal() must be called from the "
                                        "main thread"))
    action = CheckSignalAction.get(space)
    if space.eq_w(w_handler, space.wrap(SIG_DFL)):
        if signum in action.handlers_w:
            del action.handlers_w[signum]
        pypysig_default(signum)
    elif space.eq_w(w_handler, space.wrap(SIG_IGN)):
        if signum in action.handlers_w:
            del action.handlers_w[signum]
        pypysig_ignore(signum)
    else:
        if not space.is_true(space.callable(w_handler)):
            raise OperationError(space.w_TypeError,
                                 space.wrap("'handler' must be a callable "
                                            "or SIG_DFL or SIG_IGN"))
        action.handlers_w[signum] = w_handler
        pypysig_setflag(signum)
    # XXX return value missing
signal.unwrap_spec = [ObjSpace, int, W_Root]

# ____________________________________________________________
# CPython and LLTypeSystem implementations

from pypy.rpython.extregistry import ExtRegistryEntry

signal_queue = []    # only for py.py, not for translated pypy-c's

def pypysig_poll():
    "NOT_RPYTHON"
    if signal_queue:
        return signal_queue.pop(0)
    else:
        return -1

def pypysig_default(signum):
    "NOT_RPYTHON"
    cpy_signal.signal(signum, cpy_signal.SIG_DFL)  # XXX error handling

def pypysig_ignore(signum):
    "NOT_RPYTHON"
    cpy_signal.signal(signum, cpy_signal.SIG_IGN)  # XXX error handling

def _queue_handler(signum, frame):
    if signum not in signal_queue:
        signal_queue.append(signum)

def pypysig_setflag(signum):
    "NOT_RPYTHON"
    cpy_signal.signal(signum, _queue_handler)


class Entry(ExtRegistryEntry):
    pass   # in-progress
