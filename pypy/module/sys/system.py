"""Information about the current system."""
from pypy.interpreter import gateway
from rpython.rlib import rbigint, rfloat
from rpython.rtyper.lltypesystem import rffi


app = gateway.applevel("""
"NOT_RPYTHON"
from _structseq import structseqtype, structseqfield
class float_info:
    __metaclass__ = structseqtype

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

class long_info:
    __metaclass__ = structseqtype
    bits_per_digit = structseqfield(0)
    sizeof_digit = structseqfield(1)
""")


def get_float_info(space):
    info_w = [
        space.newfloat(rfloat.DBL_MAX),
        space.newint(rfloat.DBL_MAX_EXP),
        space.newint(rfloat.DBL_MAX_10_EXP),
        space.newfloat(rfloat.DBL_MIN),
        space.newint(rfloat.DBL_MIN_EXP),
        space.newint(rfloat.DBL_MIN_10_EXP),
        space.newint(rfloat.DBL_DIG),
        space.newint(rfloat.DBL_MANT_DIG),
        space.newfloat(rfloat.DBL_EPSILON),
        space.newint(rfloat.FLT_RADIX),
        space.newint(rfloat.FLT_ROUNDS),
    ]
    w_float_info = app.wget(space, "float_info")
    return space.call_function(w_float_info, space.newtuple(info_w))

def get_long_info(space):
    bits_per_digit = rbigint.SHIFT
    sizeof_digit = rffi.sizeof(rbigint.STORE_TYPE)
    info_w = [
        space.newint(bits_per_digit),
        space.newint(sizeof_digit),
    ]
    w_long_info = app.wget(space, "long_info")
    return space.call_function(w_long_info, space.newtuple(info_w))

def get_float_repr_style(space):
    return space.newtext("short")

def getdlopenflags(space):
    return space.newint(space.sys.dlopenflags)

def setdlopenflags(space, w_flags):
    space.sys.dlopenflags = space.int_w(w_flags)
