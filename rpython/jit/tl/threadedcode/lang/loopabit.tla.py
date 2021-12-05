from rpython.jit.tl.threadedcode.bytecode import bytecodes

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
    bytecodes.DUP,
    bytecodes.CONST_INT, 1,
    bytecodes.SUB,
    bytecodes.DUP,
    bytecodes.CONST_INT, 1,
    bytecodes.LT,
    bytecodes.JUMP_IF, 12,
    bytecodes.JUMP, 1,
    bytecodes.POP,
    bytecodes.CONST_INT, 1,
    bytecodes.SUB,
    bytecodes.DUP,
    bytecodes.DUP,
    bytecodes.CONST_INT, 1,
    bytecodes.LT,
    bytecodes.JUMP_IF, 25,
    bytecodes.JUMP, 1,
    bytecodes.EXIT
]
