from rpython.jit.tl.threadedcode import tla

code = [
    tla.CONST_INT, 0,
    tla.CONST_INT, 1,
    tla.CONST_N, 0, 7, 161, 32,
    tla.DUPN, 2,
    tla.DUPN, 2,
    tla.DUPN, 2,
    tla.CALL, 24, 3,
    tla.PRINT,
    tla.POP1,
    tla.POP1,
    tla.POP1,
    tla.POP1,
    tla.EXIT,
    tla.DUPN, 1,
    tla.CONST_INT, 1,
    tla.GT,
    tla.JUMP_IF, 35,
    tla.DUPN, 3,
    tla.JUMP, 70,
    tla.DUPN, 1,
    tla.CONST_INT, 2,
    tla.GT,
    tla.JUMP_IF, 46,
    tla.DUPN, 2,
    tla.JUMP, 70,
    tla.DUPN, 3,
    tla.DUPN, 3,
    tla.ADD,
    tla.DUPN, 2,
    tla.CONST_INT, 1,
    tla.SUB,
    tla.DUPN, 4,
    tla.DUPN, 2,
    tla.DUPN, 2,
    tla.FRAME_RESET, 3, 2, 3,
    tla.JUMP, 24,
    tla.POP1,
    tla.POP1,
    tla.RET, 3,
]

