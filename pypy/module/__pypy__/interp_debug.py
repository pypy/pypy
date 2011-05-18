from pypy.interpreter.gateway import interp2app, NoneNotWrapped, unwrap_spec
from pypy.interpreter.error import OperationError
from pypy.rlib import debug

@unwrap_spec(category=str)
def debug_start(space, category):
    debug.debug_start(category)

def debug_print(space, args_w):
    parts = [space.str_w(space.str(w_item)) for w_item in args_w]
    debug.debug_print(' '.join(parts))

@unwrap_spec(category=str)
def debug_stop(space, category):
    debug.debug_stop(category)


@unwrap_spec(category=str)
def debug_print_once(space, category, args_w):
    debug_start(space, category)
    debug_print(space, args_w)
    debug_stop(space, category)
