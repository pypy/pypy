import thread

# Force the declaration of thread.start_new_thread() & co. for RPython
import pypy.module.thread.rpython.exttable


class OSThreadLocals:
    """Thread-local storage for OS-level threads.
    For memory management, this version depends on explicit notification when
    a thread finishes.  This works as long as the thread was started by
    os_thread.bootstrap()."""

    def __init__(self):
        # XXX use string-keyed dicts only for now
        self._valuedict = {}   # {str(thread_ident): ExecutionContext()}

    def getvalue(self):
        ident = thread.get_ident()
        return self._valuedict.get(str(ident), None)

    def setvalue(self, value):
        ident = thread.get_ident()
        self._valuedict[str(ident)] = value

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
            ident = thread.get_ident()
            try:
                del self._valuedict[str(ident)]
            except KeyError:
                pass

    def yield_thread(self):
        """Notification that the current thread is between two bytecodes
        (so that it's a good time to yield some time to other threads)."""

    def atthreadexit(self, space, exit_func, w_obj):
        ec = space.getexecutioncontext()
        ec.thread_exit_funcs.append((exit_func, w_obj))
