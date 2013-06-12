import prolog.interpreter.term as pterm

from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.floatobject import W_FloatObject
from pypy.objspace.std.longobject import W_LongObject
from pypy.objspace.std.stringobject import W_StringObject

def int_p_of_int_w(space, int_w):
    if not isinstance(int_w, W_IntObject):
        raise TypeError("int_p_of_int_w: expects a pypy int")

    int_val = space.int_w(int_w)
    int_p = pterm.Number(int_val)
    return int_p

def float_p_of_float_w(space, float_w):
    if not isinstance(float_w, W_FloatObject):
        raise TypeError("float_p_of_float_w: expects a pypy float")

    float_val = space.float_w(float_w)
    float_p = pterm.Float(float_val)
    return float_p

def bigint_p_of_long_w(space, long_w):
    if not isinstance(long_w, W_LongObject):
        raise TypeError("bigint_p_of_long_w: expects a pypy long")

    bigint_val = space.bigint_w(long_w)
    bigint_p = pterm.BigInt(bigint_val)
    return bigint_p

def atom_p_of_str_w(space, str_w):
    if not isinstance(str_w, W_StringObject):
        raise TypeError("atom_p_of_str_w: expects a pypy string")

    str_val = space.str_w(str_w)
    atom_p = pterm.Atom(str_val)
    return atom_p

