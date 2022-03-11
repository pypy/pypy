from rpython.jit.tl.threadedcode import tla

code = [
    tla.DUP,
    tla.CONST_INT, 1,
    tla.LT,
    tla.JUMP_IF, 10,
    tla.CONST_INT, 10,
    tla.SUB,
    tla.EXIT,
    tla.CONST_INT, 1,
    tla.SUB,
    tla.JUMP, 0,
]
