from prolog.interpreter import term
from prolog.interpreter import helper

from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.gateway import interp2app

from pypy.module.unipycation import util
from pypy.module.unipycation import objects
from pypy.module.unipycation import prologobject

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
    return term.Number(val)

def p_float_of_w_float(space, w_float):
    val = space.float_w(w_float)
    return term.Float(val)

def p_bigint_of_w_long(space, w_long):
    val = space.bigint_w(w_long)
    return term.BigInt(val)

def p_atom_of_w_str(space, w_str):
    val = space.str0_w(w_str)
    return term.Atom(val)

def p_term_of_w_term(space, w_term):
    assert isinstance(w_term, objects.W_CoreTerm)
    return w_term.p_term

def p_var_of_w_var(space, w_var):
    assert isinstance(w_var, objects.W_Var)
    return w_var.p_var

def p_of_w(space, w_anything):
    w_CoreTerm = util.get_from_module(space, "unipycation", "CoreTerm")
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
    elif space.is_true(space.isinstance(w_anything, w_CoreTerm)):
        return p_term_of_w_term(space, w_anything)
    elif space.is_true(space.isinstance(w_anything, w_Var)):
        return p_var_of_w_var(space, w_anything)
    else:
        return prologobject.PythonBlackBox(space, w_anything)

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
    return space.wrap(helper.unwrap_atom(p_atom))

def w_term_of_p_callable(space, p_callable):
    return objects.W_CoreTerm(space, p_callable)

def w_whatever_of_p_bindingvar(space, p_bindingvar):
    if p_bindingvar.binding is None:
        p_var = term.BindingVar()
        return objects.W_Var(space, p_var)
    return w_of_p(space, p_bindingvar.binding)

def w_of_p(space, p_anything):
    if isinstance(p_anything, term.Number):
        return w_int_of_p_number(space, p_anything)
    elif isinstance(p_anything, term.Float):
        return w_float_of_p_float(space, p_anything)
    elif isinstance(p_anything, term.BigInt):
        return w_long_of_p_bigint(space, p_anything)
    elif isinstance(p_anything, term.Atom):
        return w_str_of_p_atom(space, p_anything)
    elif isinstance(p_anything, term.Callable):
        return w_term_of_p_callable(space, p_anything)
    elif isinstance(p_anything, term.BindingVar):
        return w_whatever_of_p_bindingvar(space, p_anything)
    elif isinstance(p_anything, prologobject.PythonBlackBox):
        return p_anything.obj
    else:
        w_ConversionError = util.get_from_module(space, "unipycation", "ConversionError")
        raise OperationError(w_ConversionError,
                space.wrap("Don't know how to convert %s to wrapped" % p_anything))
