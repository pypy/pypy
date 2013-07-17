from pypy.interpreter.gateway import unwrap_spec
from rpython.rlib.rarithmetic import intmask
from rpython.rtyper.lltypesystem import lltype
from rpython.rtyper.lltypesystem.lloperation import llop


@unwrap_spec(n=int, m=int)
def int_add(space, n, m):
    return space.wrap(intmask(n + m))

@unwrap_spec(n=int, m=int)
def int_sub(space, n, m):
    return space.wrap(intmask(n - m))

@unwrap_spec(n=int, m=int)
def int_mul(space, n, m):
    return space.wrap(intmask(n * m))

@unwrap_spec(n=int, m=int)
def int_floordiv(space, n, m):
    return space.wrap(llop.int_floordiv(lltype.Signed, n, m))

@unwrap_spec(n=int, m=int)
def int_mod(space, n, m):
    return space.wrap(llop.int_mod(lltype.Signed, n, m))
