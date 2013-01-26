from pypy.interpreter.executioncontext import AsyncAction, AbstractActionFlag
from pypy.interpreter.executioncontext import PeriodicAsyncAction
from pypy.rlib import jit
from pypy.rlib.rsignal import pypysig_getaddr_occurred
from pypy.rlib.rsignal import pypysig_poll, pypysig_reinstall


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
            if jit.isconstant(by) and by == 0:
                pass     # normally constant-folded too
            else:
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

    @jit.dont_look_inside
    def perform(self, executioncontext, frame):
        while True:
            n = pypysig_poll()
            if n < 0:
                break
            self.perform_signal(executioncontext, n)

    @jit.dont_look_inside
    def perform_signal(self, executioncontext, n):
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

    @jit.dont_look_inside
    def set_interrupt(self):
        "Simulates the effect of a SIGINT signal arriving"
        ec = self.space.getexecutioncontext()
        self.perform_signal(ec, cpy_signal.SIGINT)

    @jit.dont_look_inside
    def report_signal(self, n):
        try:
            w_handler = self.handlers_w[n]
        except KeyError:
            return    # no handler, ignore signal
        space = self.space
        if not space.is_true(space.callable(w_handler)):
            return    # w_handler is SIG_IGN or SIG_DFL?
        # re-install signal handler, for OSes that clear it
        pypysig_reinstall(n)
        # invoke the app-level handler
        ec = space.getexecutioncontext()
        w_frame = space.wrap(ec.gettopframe_nohidden())
        space.call_function(w_handler, space.wrap(n), w_frame)

    @jit.dont_look_inside
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
