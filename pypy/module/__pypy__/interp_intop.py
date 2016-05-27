from pypy.interpreter.gateway import unwrap_spec
from rpython.rtyper.lltypesystem import lltype
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rlib.rarithmetic import r_uint, intmask
from rpython.rlib import jit


# XXX maybe temporary: hide llop.int_{floordiv,mod} from the JIT,
#     because now it expects only Python-style divisions, not the
#     C-style divisions of these two ll operations
@jit.dont_look_inside
def _int_floordiv(n, m):
    return llop.int_floordiv(lltype.Signed, n, m)

@jit.dont_look_inside
def _int_mod(n, m):
    return llop.int_mod(lltype.Signed, n, m)


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
    return space.wrap(_int_floordiv(n, m))

@unwrap_spec(n=int, m=int)
def int_mod(space, n, m):
    return space.wrap(_int_mod(n, m))

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
