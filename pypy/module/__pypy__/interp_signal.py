from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.error import oefmt
from rpython.rlib import rthread, rgil


def signals_enter(space):
    space.threadlocals.enable_signals(space)

def signals_exit(space, w_ignored1=None, w_ignored2=None, w_ignored3=None):
    space.threadlocals.disable_signals(space)

@unwrap_spec(tid=int)
def _raise_in_thread(space, tid, w_exc_type):
    """ Raise exception of type exc_type the next time the thread with id tid
    is resumed. Corresponds to the C-API PyThreadState_SetAsyncExc.
    This is an experimental API, use with care."""
    # w_exc_type can be None, but only when called from the actual
    # PyThreadState_SetAsyncExc. in that case, the already scheduled
    # w_async_exception_type is cancelled (of course it might or might not have
    # been already delivered)
    ecs = space.threadlocals.getallvalues()
    for thread_ident, ec in ecs.items():
        if thread_ident == tid:
            ec.w_async_exception_type = w_exc_type
            # make sure we switch away from the current thread soon, to give
            # the target thread a chance to run
            space.actionflag.rearm_ticker()
            return
    raise oefmt(space.w_ValueError, "couldn't find thread")

