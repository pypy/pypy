""" Helper functions for dealing with prolog terms"""

from pypy.lang.prolog.interpreter import term
from pypy.lang.prolog.interpreter import error

emptylist = term.Atom.newatom("[]")

def wrap_list(python_list):
    curr = emptylist
    for i in range(len(python_list) - 1, -1, -1):
        curr = term.Term(".", [python_list[i], curr])
    return curr

def unwrap_list(prolog_list):
    result = []
    curr = prolog_list
    while isinstance(curr, term.Term):
        if not curr.name == ".":
            error.throw_type_error("list", prolog_list)
        result.append(curr.args[0])
        curr = curr.args[1]
    if isinstance(curr, term.Atom) and curr.name == "[]":
        return result
    error.throw_type_error("list", prolog_list)

def is_callable(var, engine):
    return isinstance(var, term.Callable)
is_callable._look_inside_me_ = True

def ensure_callable(var):
    if isinstance(var, term.Var):
        error.throw_instantiation_error()
    elif isinstance(var, term.Callable):
        return var
    else:
        error.throw_type_error("callable", var)
ensure_callable._look_inside_me_ = True

def unwrap_int(obj):
    if isinstance(obj, term.Number):
        return obj.num
    elif isinstance(obj, term.Float):
        f = obj.floatval; i = int(f)
        if f == i:
            return i
    error.throw_type_error('integer', obj)

def unwrap_atom(obj):
    if isinstance(obj, term.Atom):
        return obj.name
    error.throw_type_error('atom', obj)
unwrap_atom._look_inside_me_ = True

def unwrap_predicate_indicator(predicate):
    if not isinstance(predicate, term.Term):
        error.throw_type_error("predicate_indicator", predicate)
        assert 0, "unreachable"
    if not predicate.name == "/" or len(predicate.args) != 2:
        error.throw_type_error("predicate_indicator", predicate)
    name = unwrap_atom(predicate.args[0])
    arity = unwrap_int(predicate.args[1])
    return name, arity

def ensure_atomic(obj):
    if not is_atomic(obj):
        error.throw_type_error('atomic', obj)
    return obj

def is_atomic(obj):
    return (isinstance(obj, term.Atom) or isinstance(obj, term.Float) or 
            isinstance(obj, term.Number))


def convert_to_str(obj):
    if isinstance(obj, term.Var):
        error.throw_instantiation_error()
    if isinstance(obj, term.Atom):
        return obj.name
    elif isinstance(obj, term.Number):
        return str(obj.num)
    elif isinstance(obj, term.Float):
        return str(obj.floatval)
    error.throw_type_error("atomic", obj)

