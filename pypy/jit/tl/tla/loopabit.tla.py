from pypy.jit.tl.tla import tla

code = [
    tla.CONST_INT, 1,
    tla.SUB,
    tla.DUP,
    tla.JUMP_IF, 0,
    tla.RETURN
    ]
