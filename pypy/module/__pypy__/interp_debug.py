from pypy.interpreter.gateway import unwrap_spec
from pypy.rlib import debug, jit


@jit.dont_look_inside
@unwrap_spec(category=str)
def debug_start(space, category):
    debug.debug_start(category)

@jit.dont_look_inside
def debug_print(space, args_w):
    parts = [space.str_w(space.str(w_item)) for w_item in args_w]
    debug.debug_print(' '.join(parts))

@jit.dont_look_inside
@unwrap_spec(category=str)
def debug_stop(space, category):
    debug.debug_stop(category)


@unwrap_spec(category=str)
def debug_print_once(space, category, args_w):
    debug_start(space, category)
    debug_print(space, args_w)
    debug_stop(space, category)
