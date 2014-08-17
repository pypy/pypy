from pypy.interpreter.gateway import unwrap_spec
from rpython.rtyper.lltypesystem import lltype
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rlib.rarithmetic import r_uint, intmask


@unwrap_spec(n=int, m=int)
def int_add(space, n, m):
    return space.wrap(llop.int_add(lltype.Signed, n, m))

@unwrap_spec(n=int, m=int)
def int_sub(space, n, m):
    return space.wrap(llop.int_sub(lltype.Signed, n, m))

@unwrap_spec(n=int, m=int)
def int_mul(space, n, m):
    return space.wrap(llop.int_mul(lltype.Signed, n, m))

@unwrap_spec(n=int, m=int)
def int_floordiv(space, n, m):
    return space.wrap(llop.int_floordiv(lltype.Signed, n, m))

@unwrap_spec(n=int, m=int)
def int_mod(space, n, m):
    return space.wrap(llop.int_mod(lltype.Signed, n, m))

@unwrap_spec(n=int, m=int)
def int_lshift(space, n, m):
    return space.wrap(llop.int_lshift(lltype.Signed, n, m))

@unwrap_spec(n=int, m=int)
def int_rshift(space, n, m):
    return space.wrap(llop.int_rshift(lltype.Signed, n, m))

@unwrap_spec(n=int, m=int)
def uint_rshift(space, n, m):
    n = r_uint(n)
    x = llop.uint_rshift(lltype.Unsigned, n, m)
    return space.wrap(intmask(x))
