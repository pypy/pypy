from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.error import oefmt

def signals_enter(space):
    space.threadlocals.enable_signals(space)

def signals_exit(space, w_ignored1=None, w_ignored2=None, w_ignored3=None):
    space.threadlocals.disable_signals(space)


@unwrap_spec(tid=int)
def _raise_in_thread(space, tid, w_exc_type):
    """ raise exception of type exc_type the next time the thread with id tid
    is resumed. corresponds to the C-API PyThreadState_SetAsyncExc. experimental API,
    use with care."""
    ecs = space.threadlocals.getallvalues()
    for thread_ident, ec in ecs.items():
        if thread_ident == tid:
            ec.w_async_exception_type = w_exc_type
            space.check_signal_action.notify_thread_interruption()
            return
    raise oefmt(space.w_ValueError, "couldn't find thread")
