from rpython.jit.tl.threadedcode import tla

# code = [
#     tla.DUP,
#     tla.CONST_INT, 1,
#     tla.SUB,
#     tla.DUP,
#     tla.JUMP_IF, 1,
#     tla.POP,
#     tla.CONST_INT, 1,
#     tla.SUB,
#     tla.DUP,
#     tla.JUMP_IF, 0,
#     tla.EXIT
#     ]

code = [
    tla.DUP,
    tla.CONST_INT, 1,
    tla.SUB,
    tla.DUP,
    tla.CONST_INT, 1,
    tla.LT,
    tla.JUMP_IF, 12,
    tla.JUMP, 1,
    tla.POP,
    tla.CONST_INT, 1,
    tla.SUB,
    tla.DUP,
    tla.DUP,
    tla.CONST_INT, 1,
    tla.LT,
    tla.JUMP_IF, 25,
    tla.JUMP, 1,
    tla.EXIT
]
