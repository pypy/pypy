from pypy.interpreter.error import OperationError
from pypy.rlib.rstm import increment_atomic, decrement_atomic, is_atomic
from pypy.module.thread.error import wrap_thread_error

def atomic_enter(space):
    if not space.config.translation.stm:
        raise wrap_thread_error(space,
            "atomic.__enter__(): STM not available")
    increment_atomic()

def atomic_exit(space, w_ignored1=None, w_ignored2=None, w_ignored3=None):
    if not space.config.translation.stm:
        raise wrap_thread_error(space,
            "atomic.__exit__(): STM not available")
    if not is_atomic():
        raise wrap_thread_error(space,
            "atomic.__exit__(): more exits than enters")
    decrement_atomic()
