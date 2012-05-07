from pypy.interpreter.error import OperationError
from pypy.rlib.rstm import increment_atomic, decrement_atomic, is_atomic

def get_w_error(space):
    from pypy.module.thread import error
    return space.fromcache(error.Cache).w_error

def atomic_enter(space):
    if not space.config.translation.stm:
        raise OperationError(get_w_error(space),
            space.wrap("atomic.__enter__(): STM not available"))
    increment_atomic()

def atomic_exit(space, w_ignored1=None, w_ignored2=None, w_ignored3=None):
    if not space.config.translation.stm:
        raise OperationError(get_w_error(space),
            space.wrap("atomic.__exit__(): STM not available"))
    if not is_atomic():
        raise OperationError(get_w_error(space),
            space.wrap("atomic.__exit__(): more exits than enters"))
    decrement_atomic()
