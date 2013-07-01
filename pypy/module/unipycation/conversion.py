import prolog.interpreter.term as pterm
import prolog.interpreter.helper as phelper

from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import W_Root

import pypy.module.unipycation.util as util

def _w_type_check(space, inst, typ):
    if not space.is_true(space.isinstance(inst, typ)):
        w_ConversionError = util.get_from_module(space, "unipycation", "ConversionError")
        raise OperationError(w_ConversionError, "%s is not of type %s" % (inst, typ))

def _p_type_check(inst, typ):
    if not isinstance(inst, typ):
        w_ConversionError = util.get_from_module(space, "unipycation", "ConversionError")
        raise OperationError(w_ConversionError, "%s is not of type %s" % (inst, typ))

# -----------------------------
# Convert from Python to Prolog
# -----------------------------

def p_number_of_w_int(space, w_int):
    _w_type_check(space, w_int, space.w_int)

    val = space.int_w(w_int)
    return pterm.Number(val)

def p_float_of_w_float(space, w_float):
    _w_type_check(space, w_float, space.w_float)

    val = space.float_w(w_float)
    return pterm.Float(val)

def p_bigint_of_w_long(space, w_long):
    _w_type_check(space, w_long, space.w_long)

    val = space.bigint_w(w_long)
    return pterm.BigInt(val)

def p_atom_of_w_str(space, w_str):
    _w_type_check(space, w_str, space.w_str)

    val = space.str0_w(w_str)
    return pterm.Atom(val)

def p_of_w(space, w_anything):
    w_ConversionError = util.get_from_module(space, "unipycation", "ConversionError")

    assert(isinstance(w_anything, W_Root))

    if space.is_true(space.isinstance(w_anything, space.w_int)):
        return p_number_of_w_int(space, w_anything)
    elif space.is_true(space.isinstance(w_anything, space.w_float)):
        return p_float_of_w_float(space, w_anything)
    elif space.is_true(space.isinstance(w_anything, space.w_long)):
        return p_bigint_of_w_long(space, w_anything)
    elif space.is_true(space.isinstance(w_anything, space.w_str)):
        return p_atom_of_w_str(space, w_anything)
    else:
        raise OperationError(w_ConversionError,
                "Don't know how to convert wrapped %s to prolog type" % p_anything)

# -----------------------------
# Convert from Prolog to Python
# -----------------------------

def w_int_of_p_number(space, p_number):
    _p_type_check(p_number, pterm.Number)
    return space.newint(p_number.num)

def w_float_of_p_float(space, p_float):
    _p_type_check(p_float, pterm.Float)
    return space.newfloat(p_float.floatval)

def w_long_of_p_bigint(space, p_bigint):
    _p_type_check(p_bigint, pterm.BigInt)
    return space.newlong_from_rbigint(p_bigint.value)

def w_str_of_p_atom(space, p_atom):
    _p_type_check(p_atom, pterm.Atom)
    return space.wrap(phelper.unwrap_atom(p_atom))

def w_of_p(space, p_anything):
    if isinstance(p_anything, pterm.Number):
        return w_int_of_p_number(space, p_anything)
    elif isinstance(p_anything, pterm.Float):
        return w_float_of_p_float(space, p_anything)
    elif isinstance(p_anything, pterm.Float):
        return w_long_of_p_bigint(space, p_anything)
    elif isinstance(p_anything, pterm.Atom):
        return w_str_of_p_atom(space, p_anything)
    else:
        w_ConversionError = util.get_from_module(space, "unipycation", "ConversionError")
        raise OperationError(w_ConversionError,
                "Don't know how to convert %s to wrapped" % p_anything)
