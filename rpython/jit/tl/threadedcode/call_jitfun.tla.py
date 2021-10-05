from rpython.jit.tl.threadedcode import tla

code = [
    tla.CALL_JIT, 11,
    tla.DUP,
    tla.CONST_INT, 1,
    tla.LT,
    tla.JUMP_IF, 10,
    tla.JUMP, 0,
    tla.EXIT,
    # function sub_1(x)
    tla.CONST_INT, 1,
    tla.SUB,
    tla.RET, 1
]
