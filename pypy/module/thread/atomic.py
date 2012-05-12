from pypy.interpreter.error import OperationError
from pypy.module.thread.error import wrap_thread_error

def atomic_enter(space):
    if space.config.translation.stm:
        from pypy.rlib.rstm import increment_atomic
        increment_atomic()
    else:
        giltl = space.threadlocals
        giltl.is_atomic += 1
        space.threadlocals.set_gil_releasing_calls()

def atomic_exit(space, w_ignored1=None, w_ignored2=None, w_ignored3=None):
    if space.config.translation.stm:
        from pypy.rlib.rstm import decrement_atomic, is_atomic
        if is_atomic():
            decrement_atomic()
            return
    else:
        giltl = space.threadlocals
        if giltl.is_atomic > 0:
            giltl.is_atomic -= 1
            space.threadlocals.set_gil_releasing_calls()
            return
    raise wrap_thread_error(space,
        "atomic.__exit__(): more exits than enters")
