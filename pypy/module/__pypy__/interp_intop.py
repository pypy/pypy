from pypy.interpreter.gateway import unwrap_spec
from rpython.rlib.rarithmetic import intmask


@unwrap_spec(n=int, m=int)
def int_add(space, n, m):
    return space.wrap(intmask(n + m))

@unwrap_spec(n=int, m=int)
def int_sub(space, n, m):
    return space.wrap(intmask(n - m))

@unwrap_spec(n=int, m=int)
def int_mul(space, n, m):
    return space.wrap(intmask(n * m))
