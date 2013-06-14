import prolog.interpreter.term as pterm

from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.floatobject import W_FloatObject
from pypy.objspace.std.longobject import W_LongObject
from pypy.objspace.std.stringobject import W_StringObject

# XXX use space.isinstance instead of isinstance

def int_p_of_int_w(space, w_int):
    if not isinstance(w_int, W_IntObject):
        raise TypeError("int_p_of_int_w: expects a pypy int")

    val = space.int_w(w_int)
    p_int = pterm.Number(val)
    return p_int

def float_p_of_float_w(space, w_float):
    if not isinstance(w_float, W_FloatObject):
        raise TypeError("float_p_of_float_w: expects a pypy float")

    val = space.float_w(w_float)
    p_float = pterm.Float(val)
    return p_float

def bigint_p_of_long_w(space, w_long):
    if not isinstance(w_long, W_LongObject):
        raise TypeError("bigint_p_of_long_w: expects a pypy long")

    val = space.bigint_w(w_long)
    p_bigint = pterm.BigInt(val)
    return p_bigint

def atom_p_of_str_w(space, w_str):
    if not isinstance(w_str, W_StringObject):
        raise TypeError("atom_p_of_str_w: expects a pypy string")

    val = space.str_w(w_str)
    p_atom = pterm.Atom(val)
    return p_atom

