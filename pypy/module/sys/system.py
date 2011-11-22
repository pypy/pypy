"""Information about the current system."""
from pypy.interpreter import gateway
from pypy.rlib import rfloat, rbigint
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rlib.objectmodel import HASH_INF, HASH_NAN, HASH_IMAG

app = gateway.applevel("""
"NOT_RPYTHON"
from _structseq import structseqtype, structseqfield
class float_info(metaclass=structseqtype):

    max = structseqfield(0)
    max_exp = structseqfield(1)
    max_10_exp = structseqfield(2)
    min = structseqfield(3)
    min_exp = structseqfield(4)
    min_10_exp = structseqfield(5)
    dig = structseqfield(6)
    mant_dig = structseqfield(7)
    epsilon = structseqfield(8)
    radix = structseqfield(9)
    rounds = structseqfield(10)

class int_info(metaclass=structseqtype):
    bits_per_digit = structseqfield(0)
    sizeof_digit = structseqfield(1)
    
class hash_info(metaclass=structseqtype):
    width = structseqfield(0)
    modulus = structseqfield(1)
    inf = structseqfield(2)
    nan = structseqfield(3)
    imag = structseqfield(4)
""")


def get_float_info(space):
    info_w = [
        space.wrap(rfloat.DBL_MAX),
        space.wrap(rfloat.DBL_MAX_EXP),
        space.wrap(rfloat.DBL_MAX_10_EXP),
        space.wrap(rfloat.DBL_MIN),
        space.wrap(rfloat.DBL_MIN_EXP),
        space.wrap(rfloat.DBL_MIN_10_EXP),
        space.wrap(rfloat.DBL_DIG),
        space.wrap(rfloat.DBL_MANT_DIG),
        space.wrap(rfloat.DBL_EPSILON),
        space.wrap(rfloat.FLT_RADIX),
        space.wrap(rfloat.FLT_ROUNDS),
    ]
    w_float_info = app.wget(space, "float_info")
    return space.call_function(w_float_info, space.newtuple(info_w))

def get_int_info(space):
    assert rbigint.SHIFT == 31
    bits_per_digit = rbigint.SHIFT
    sizeof_digit = rffi.sizeof(rffi.ULONG)
    info_w = [
        space.wrap(bits_per_digit),
        space.wrap(sizeof_digit),
    ]
    w_int_info = app.wget(space, "int_info")
    return space.call_function(w_int_info, space.newtuple(info_w))

def get_hash_info(space):
    # XXX our _hash_float() always give values that fit in 32bit
    modulus = (1 << 31) - 1  # Must be a prime number
    info_w = [
        space.wrap(8 * rffi.sizeof(lltype.Signed)),
        space.wrap(modulus),
        space.wrap(HASH_INF),
        space.wrap(HASH_NAN),
        space.wrap(HASH_IMAG),
    ]
    w_hash_info = app.wget(space, "hash_info")
    return space.call_function(w_hash_info, space.newtuple(info_w))

def get_float_repr_style(space):
    if rfloat.USE_SHORT_FLOAT_REPR:
        return space.wrap("short")
    else:
        return space.wrap("legacy")
