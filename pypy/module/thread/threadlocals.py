from rpython.rlib import rthread
from rpython.rlib.objectmodel import we_are_translated
from pypy.module.thread.error import wrap_thread_error
from pypy.interpreter.executioncontext import ExecutionContext


ExecutionContext._signals_enabled = 0     # default value


class OSThreadLocals:
    """Thread-local storage for OS-level threads.
    For memory management, this version depends on explicit notification when
    a thread finishes.  This works as long as the thread was started by
    os_thread.bootstrap()."""

    def __init__(self):
        "NOT_RPYTHON"
        self._valuedict = {}   # {thread_ident: ExecutionContext()}
        self._cleanup_()
        self.raw_thread_local = rthread.ThreadLocalReference(ExecutionContext,
                                                            loop_invariant=True)

    def _cleanup_(self):
        self._valuedict.clear()
        self._mainthreadident = 0

    def enter_thread(self, space):
        "Notification that the current thread is about to start running."
        self._set_ec(space.createexecutioncontext())

    def try_enter_thread(self, space):
        if rthread.get_ident() in self._valuedict:
            return False
        self.enter_thread(space)
        return True

    def _set_ec(self, ec):
        ident = rthread.get_ident()
        if self._mainthreadident == 0 or self._mainthreadident == ident:
            ec._signals_enabled = 1    # the main thread is enabled
            self._mainthreadident = ident
        self._valuedict[ident] = ec
        # This logic relies on hacks and _make_sure_does_not_move().
        # It only works because we keep the 'ec' alive in '_valuedict' too.
        self.raw_thread_local.set(ec)

    def leave_thread(self, space):
        "Notification that the current thread is about to stop."
        from pypy.module.thread.os_local import thread_is_stopping
        ec = self.get_ec()
        if ec is not None:
            try:
                thread_is_stopping(ec)
            finally:
                self.raw_thread_local.set(None)
                ident = rthread.get_ident()
                try:
                    del self._valuedict[ident]
                except KeyError:
                    pass

    def get_ec(self):
        ec = self.raw_thread_local.get()
        if not we_are_translated():
            assert ec is self._valuedict.get(rthread.get_ident(), None)
        return ec

    def signals_enabled(self):
        ec = self.get_ec()
        return ec is not None and ec._signals_enabled

    def enable_signals(self, space):
        ec = self.get_ec()
        assert ec is not None
        ec._signals_enabled += 1

    def disable_signals(self, space):
        ec = self.get_ec()
        assert ec is not None
        new = ec._signals_enabled - 1
        if new < 0:
            raise wrap_thread_error(space,
                "cannot disable signals in thread not enabled for signals")
        ec._signals_enabled = new

    def getallvalues(self):
        return self._valuedict

    def reinit_threads(self, space):
        "Called in the child process after a fork()"
        ident = rthread.get_ident()
        ec = self.get_ec()
        assert ec is not None
        old_sig = ec._signals_enabled
        if ident != self._mainthreadident:
            old_sig += 1
        self._cleanup_()
        self._mainthreadident = ident
        self._set_ec(ec)
        ec._signals_enabled = old_sig
