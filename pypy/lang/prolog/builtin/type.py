import py
from pypy.lang.prolog.interpreter import engine, helper, term, error
from pypy.lang.prolog.builtin.register import expose_builtin

# ___________________________________________________________________
# type verifications

def impl_nonvar(engine, var):
    if isinstance(var, term.Var):
        raise error.UnificationFailed()
expose_builtin(impl_nonvar, "nonvar", unwrap_spec=["obj"])

def impl_var(engine, var):
    if not isinstance(var, term.Var):
        raise error.UnificationFailed()
expose_builtin(impl_var, "var", unwrap_spec=["obj"])

def impl_integer(engine, var):
    if isinstance(var, term.Var) or not isinstance(var, term.Number):
        raise error.UnificationFailed()
expose_builtin(impl_integer, "integer", unwrap_spec=["obj"])

def impl_float(engine, var):
    if isinstance(var, term.Var) or not isinstance(var, term.Float):
        raise error.UnificationFailed()
expose_builtin(impl_float, "float", unwrap_spec=["obj"])

def impl_number(engine, var):
    if (isinstance(var, term.Var) or
        (not isinstance(var, term.Number) and not
         isinstance(var, term.Float))):
        raise error.UnificationFailed()
expose_builtin(impl_number, "number", unwrap_spec=["obj"])

def impl_atom(engine, var):
    if isinstance(var, term.Var) or not isinstance(var, term.Atom):
        raise error.UnificationFailed()
expose_builtin(impl_atom, "atom", unwrap_spec=["obj"])

def impl_atomic(engine, var):
    if helper.is_atomic(var):
        return
    raise error.UnificationFailed()
expose_builtin(impl_atomic, "atomic", unwrap_spec=["obj"])

def impl_compound(engine, var):
    if isinstance(var, term.Var) or not isinstance(var, term.Term):
        raise error.UnificationFailed()
expose_builtin(impl_compound, "compound", unwrap_spec=["obj"])

def impl_callable(engine, var):
    if not helper.is_callable(var, engine):
        raise error.UnificationFailed()
expose_builtin(impl_callable, "callable", unwrap_spec=["obj"])

def impl_ground(engine, var):
    if isinstance(var, term.Var):
        raise error.UnificationFailed()
    if isinstance(var, term.Term):
        for arg in var.args:
            impl_ground(engine, arg)
expose_builtin(impl_ground, "ground", unwrap_spec=["concrete"])


