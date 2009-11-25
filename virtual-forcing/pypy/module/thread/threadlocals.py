from pypy.module.thread import ll_thread as thread

class OSThreadLocals:
    """Thread-local storage for OS-level threads.
    For memory management, this version depends on explicit notification when
    a thread finishes.  This works as long as the thread was started by
    os_thread.bootstrap()."""

    def __init__(self):
        self._valuedict = {}   # {thread_ident: ExecutionContext()}
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

    def getmainthreadvalue(self):
        ident = self._mainthreadident
        return self._valuedict.get(ident, None)

    def enter_thread(self, space):
        "Notification that the current thread is just starting."
        ec = space.getexecutioncontext()
        ec.thread_exit_funcs = []

    def leave_thread(self, space):
        "Notification that the current thread is about to stop."
        try:
            ec = space.getexecutioncontext()
            while ec.thread_exit_funcs:
                exit_func, w_obj = ec.thread_exit_funcs.pop()
                exit_func(w_obj)
        finally:
            self.setvalue(None)

    def atthreadexit(self, space, exit_func, w_obj):
        ec = space.getexecutioncontext()
        ec.thread_exit_funcs.append((exit_func, w_obj))
