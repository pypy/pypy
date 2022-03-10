from rpython.jit.tl.threadedcode import tla

code = [
        tla.DUP, tla.NOP,
        tla.DUP,
        tla.CALL, 10, 1,
        tla.PRINT,
        tla.POP1,
        tla.POP1,
        tla.EXIT,
        tla.DUPN, 1,
        tla.CONST_INT, 1,
        tla.LT,
        tla.JUMP_IF, 35,
        tla.DUPN, 1,
        tla.CONST_INT, 1,
        tla.SUB,
        tla.DUP,
        tla.CALL, 10, 1,
        tla.DUPN, 3,
        tla.DUPN, 1,
        tla.MUL,
        tla.POP1,
        tla.POP1,
        tla.JUMP, 37,
        tla.CONST_INT, 1,
        tla.RET, 1,
]

