from pypy.interpreter.gateway import unwrap_spec
from rpython.rlib import debug, jit


@jit.dont_look_inside
@unwrap_spec(category='text')
def debug_start(space, category):
    debug.debug_start(category)

@jit.dont_look_inside
def debug_print(space, args_w):
    parts = [space.text_w(space.str(w_item)) for w_item in args_w]
    debug.debug_print(' '.join(parts))

@jit.dont_look_inside
@unwrap_spec(category='text')
def debug_stop(space, category):
    debug.debug_stop(category)


@unwrap_spec(category='text')
def debug_print_once(space, category, args_w):
    debug_start(space, category)
    debug_print(space, args_w)
    debug_stop(space, category)


@jit.dont_look_inside
def debug_flush(space):
    debug.debug_flush()
