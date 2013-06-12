import py
from prolog.interpreter import helper, term, error
from prolog.builtin.register import expose_builtin

# ___________________________________________________________________
# type verifications

@expose_builtin("nonvar", unwrap_spec=["obj"])
def impl_nonvar(engine, heap, var):
    if isinstance(var, term.Var):
        raise error.UnificationFailed()

@expose_builtin("var", unwrap_spec=["obj"])
def impl_var(engine, heap, var):
    if not isinstance(var, term.Var):
        raise error.UnificationFailed()

@expose_builtin("integer", unwrap_spec=["obj"])
def impl_integer(engine, heap, var):
    if (isinstance(var, term.Var) or not (isinstance(var, term.Number) or
            isinstance(var, term.BigInt))):
        raise error.UnificationFailed()

@expose_builtin("float", unwrap_spec=["obj"])
def impl_float(engine, heap, var):
    if isinstance(var, term.Var) or not isinstance(var, term.Float):
        raise error.UnificationFailed()

@expose_builtin("number", unwrap_spec=["obj"])
def impl_number(engine, heap, var):
    if (isinstance(var, term.Var) or
        (not (isinstance(var, term.Number) or isinstance(var, term.BigInt)) and not
         isinstance(var, term.Float))):
        raise error.UnificationFailed()

@expose_builtin("atom", unwrap_spec=["obj"])
def impl_atom(engine, heap, var):
    if isinstance(var, term.Var) or not isinstance(var, term.Atom):
        raise error.UnificationFailed()

@expose_builtin("atomic", unwrap_spec=["obj"])
def impl_atomic(engine, heap, var):
    if helper.is_atomic(var):
        return
    raise error.UnificationFailed()

@expose_builtin("compound", unwrap_spec=["obj"])
def impl_compound(engine, heap, var):
    if isinstance(var, term.Var):
        raise error.UnificationFailed()
    if helper.is_term(var):
        return
    raise error.UnificationFailed()

@expose_builtin("callable", unwrap_spec=["obj"])
def impl_callable(engine, heap, var):
    if not helper.is_callable(var, engine):
        raise error.UnificationFailed()

@expose_builtin("ground", unwrap_spec=["raw"])
def impl_ground(engine, heap, var):
    var = var.dereference(heap)
    if isinstance(var, term.Var):
        raise error.UnificationFailed()
    if isinstance(var, term.Callable):
        for arg in var.arguments():
            impl_ground(engine, heap, arg)


