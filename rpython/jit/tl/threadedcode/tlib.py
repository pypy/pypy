from rpython.rlib import jit

@jit.dont_look_inside
def emit_jump(pc, t, dummy=True):
    return pc

@jit.dont_look_inside
def emit_ret(pc, w_x, dummy=True):
    return pc
