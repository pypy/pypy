import prolog.interpreter.term as pterm
import prolog.interpreter.helper as phelper

from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.gateway import interp2app

import pypy.module.unipycation.util as util
import pypy.module.unipycation.objects as objects

from pypy.interpreter.baseobjspace import W_Root

def _w_type_check(space, inst, typ):
    if not space.is_true(space.isinstance(inst, typ)):
        w_ConversionError = util.get_from_module(space, "unipycation", "ConversionError")
        raise OperationError(w_ConversionError, space.wrap("%s is not of type %s" % (inst, typ)))

def _p_type_check(space, inst, typ):
    if not isinstance(inst, typ):
        w_ConversionError = util.get_from_module(space, "unipycation", "ConversionError")
        raise OperationError(w_ConversionError, space.wrap("type check failed"))

# -----------------------------
# Convert from Python to Prolog
# -----------------------------

def p_number_of_w_int(space, w_int):
    val = space.int_w(w_int)
    return pterm.Number(val)

def p_float_of_w_float(space, w_float):
    val = space.float_w(w_float)
    return pterm.Float(val)

def p_bigint_of_w_long(space, w_long):
    val = space.bigint_w(w_long)
    return pterm.BigInt(val)

def p_atom_of_w_str(space, w_str):
    val = space.str0_w(w_str)
    return pterm.Atom(val)

def p_term_of_w_term(space, w_term):
    assert isinstance(w_term, objects.W_Term)
    return w_term.p_term

def p_var_of_w_var(space, w_var):
    assert isinstance(w_var, objects.W_Var)
    return w_var.p_var

def p_of_w(space, w_anything):
    w_Term = util.get_from_module(space, "unipycation", "Term")
    w_Var = util.get_from_module(space, "unipycation", "Var")

    assert(isinstance(w_anything, W_Root))

    if space.is_true(space.isinstance(w_anything, space.w_int)):
        return p_number_of_w_int(space, w_anything)
    elif space.is_true(space.isinstance(w_anything, space.w_float)):
        return p_float_of_w_float(space, w_anything)
    elif space.is_true(space.isinstance(w_anything, space.w_long)):
        return p_bigint_of_w_long(space, w_anything)
    elif space.is_true(space.isinstance(w_anything, space.w_str)):
        return p_atom_of_w_str(space, w_anything)
    elif space.is_true(space.isinstance(w_anything, w_Term)):
        return p_term_of_w_term(space, w_anything)
    elif space.is_true(space.isinstance(w_anything, w_Var)):
        return p_var_of_w_var(space, w_anything)
    else:
        w_ConversionError = util.get_from_module(space, "unipycation", "ConversionError")
        raise OperationError(w_ConversionError,
                space.wrap("Don't know how to convert wrapped %s to prolog type" % w_anything))

# -----------------------------
# Convert from Prolog to Python
# -----------------------------

def w_int_of_p_number(space, p_number):
    return space.newint(p_number.num)

def w_float_of_p_float(space, p_float):
    return space.newfloat(p_float.floatval)

def w_long_of_p_bigint(space, p_bigint):
    return space.newlong_from_rbigint(p_bigint.value)

def w_str_of_p_atom(space, p_atom):
    return space.wrap(phelper.unwrap_atom(p_atom))

def w_term_of_p_callable(space, p_callable):
    return objects.W_Term(space, p_callable)

def w_whatever_of_p_bindingvar(space, p_bindingvar):
    if p_bindingvar.binding is None:
        return objects.var_new__(space, W_Root, None) # unbound variable, it is what it is...
    return w_of_p(space, p_bindingvar.binding)

def w_of_p(space, p_anything):
    if isinstance(p_anything, pterm.Number):
        return w_int_of_p_number(space, p_anything)
    elif isinstance(p_anything, pterm.Float):
        return w_float_of_p_float(space, p_anything)
    elif isinstance(p_anything, pterm.BigInt):
        return w_long_of_p_bigint(space, p_anything)
    elif isinstance(p_anything, pterm.Atom):
        return w_str_of_p_atom(space, p_anything)
    elif isinstance(p_anything, pterm.Callable):
        return w_term_of_p_callable(space, p_anything)
    elif isinstance(p_anything, pterm.BindingVar):
        return w_whatever_of_p_bindingvar(space, p_anything)
    else:
        w_ConversionError = util.get_from_module(space, "unipycation", "ConversionError")
        raise OperationError(w_ConversionError,
                space.wrap("Don't know how to convert %s to wrapped" % p_anything))
