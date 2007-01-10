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


# lltyping - direct mapping to the C functions defined in
# translator/c/src/signals.h

class Entry(ExtRegistryEntry):
    _about_ = pypysig_poll
    def compute_result_annotation(self):
        from pypy.annotation import model as annmodel
        return annmodel.SomeInteger()
    def specialize_call(self, hop):
        from pypy.rpython.lltypesystem import lltype
        hop.exception_cannot_occur()
        return hop.llops.gencapicall("pypysig_poll", [], lltype.Signed,
                                     includes=('src/signals.h',))

for _fn in [pypysig_default, pypysig_ignore, pypysig_setflag]:
    class Entry(ExtRegistryEntry):
        _about_ = _fn
        funcname = _fn.func_name
        def compute_result_annotation(self, s_signum):
            return None
        def specialize_call(self, hop):
            from pypy.rpython.lltypesystem import lltype
            vlist = hop.inputargs(lltype.Signed)
            hop.exception_cannot_occur()
            hop.llops.gencapicall(self.funcname, vlist,
                                  includes=('src/signals.h',))
del _fn
