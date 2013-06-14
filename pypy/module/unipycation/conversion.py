import prolog.interpreter.term as pterm

from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.floatobject import W_FloatObject
from pypy.objspace.std.longobject import W_LongObject
from pypy.objspace.std.stringobject import W_StringObject

def _type_check(space, inst, typ):
    if not space.is_true(space.isinstance(inst, typ)):
        raise TypeError("%s is not of type %s" % (inst, typ))

def int_p_of_int_w(space, w_int):
    _type_check(space, w_int, space.w_int)

    val = space.int_w(w_int)
    return pterm.Number(val)

def float_p_of_float_w(space, w_float):
    _type_check(space, w_float, space.w_float)

    val = space.float_w(w_float)
    return pterm.Float(val)

def bigint_p_of_long_w(space, w_long):
    _type_check(space, w_long, space.w_long)

    val = space.bigint_w(w_long)
    return pterm.BigInt(val)

def atom_p_of_str_w(space, w_str):
    _type_check(space, w_str, space.w_str)

    val = space.str_w(w_str)
    return pterm.Atom(val)

