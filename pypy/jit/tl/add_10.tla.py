from pypy.jit.tl import tla

code = [
    tla.CONST_INT, 10,
    tla.ADD,
    tla.RETURN
    ]
