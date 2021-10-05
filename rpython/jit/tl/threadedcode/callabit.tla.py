from rpython.jit.tl.threadedcode import tla

code = [
    tla.DUP,
    tla.CALL, 16,
    tla.POP,
    tla.CONST_INT, 1,
    tla.SUB,
    tla.DUP,
    tla.CONST_INT, 1,
    tla.LT,
    tla.JUMP_IF, 15,
    tla.JUMP, 0,
    tla.EXIT,
    tla.CONST_INT, 1,
    tla.SUB,
    tla.DUP,
    tla.CONST_INT, 1,
    tla.LT,
    tla.JUMP_IF, 27,
    tla.CALL, 16,
    tla.RET, 1
]
