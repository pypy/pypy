from rpython.jit.tl.threadedcode import tla

code = [
    tla.DUP,
    tla.CONST_INT, 1,
    tla.LT,
    tla.JUMP_IF, 11,
    tla.CONST_INT, 1,
    tla.SUB,
    tla.JUMP, 0,
    tla.CONST_INT, 10,
    tla.SUB,
    tla.EXIT,
]
