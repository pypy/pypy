from rpython.rlib import rthread as thread


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
        ident = thread.get_ident()
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
        ident = thread.get_ident()
        if value is not None:
            if len(self._valuedict) == 0:
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

    def ismainthread(self):
        return thread.get_ident() == self._mainthreadident

    def getallvalues(self):
        return self._valuedict

    def leave_thread(self, space):
        "Notification that the current thread is about to stop."
        from pypy.module.thread.os_local import thread_is_stopping
        try:
            thread_is_stopping(self.getvalue())
        finally:
            self.setvalue(None)
