from rpython.rlib import rthread
from pypy.module.thread.error import wrap_thread_error
from pypy.interpreter.executioncontext import ExecutionContext


ExecutionContext._signals_enabled = 0     # default value


class OSThreadLocals:
    """Thread-local storage for OS-level threads.
    For memory management, this version depends on explicit notification when
    a thread finishes.  This works as long as the thread was started by
    os_thread.bootstrap()."""

    def __init__(self):
        self._valuedict = {}   # {thread_ident: ExecutionContext()}
        self._cleanup_()

    def _cleanup_(self):
        self._valuedict.clear()
        self._mainthreadident = 0
        self._mostrecentkey = 0        # fast minicaching for the common case
        self._mostrecentvalue = None   # fast minicaching for the common case

    def getvalue(self):
        ident = rthread.get_ident()
        if ident == self._mostrecentkey:
            result = self._mostrecentvalue
        else:
            value = self._valuedict.get(ident, None)
            # slow path: update the minicache
            self._mostrecentkey = ident
            self._mostrecentvalue = value
            result = value
        return result

    def setvalue(self, value):
        ident = rthread.get_ident()
        if value is not None:
            if self._mainthreadident == 0:
                value._signals_enabled = 1    # the main thread is enabled
                self._mainthreadident = ident
            self._valuedict[ident] = value
        else:
            try:
                del self._valuedict[ident]
            except KeyError:
                pass
        # update the minicache to prevent it from containing an outdated value
        self._mostrecentkey = ident
        self._mostrecentvalue = value

    def signals_enabled(self):
        ec = self.getvalue()
        return ec._signals_enabled

    def enable_signals(self, space):
        ec = self.getvalue()
        ec._signals_enabled += 1

    def disable_signals(self, space):
        ec = self.getvalue()
        new = ec._signals_enabled - 1
        if new < 0:
            raise wrap_thread_error(space,
                "cannot disable signals in thread not enabled for signals")
        ec._signals_enabled = new

    def getallvalues(self):
        return self._valuedict

    def leave_thread(self, space):
        "Notification that the current thread is about to stop."
        from pypy.module.thread.os_local import thread_is_stopping
        try:
            thread_is_stopping(self.getvalue())
        finally:
            self.setvalue(None)

    def reinit_threads(self, space):
        "Called in the child process after a fork()"
        ident = rthread.get_ident()
        ec = self.getvalue()
        if ident != self._mainthreadident:
            ec._signals_enabled += 1
        self._cleanup_()
        self._mainthreadident = ident
        self.setvalue(ec)
