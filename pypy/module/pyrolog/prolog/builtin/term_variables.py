import py
from rpython.rlib.objectmodel import specialize
from prolog.builtin.register import expose_builtin
from prolog.interpreter import term
from prolog.interpreter.helper import wrap_list, is_term
from prolog.interpreter.memo import CopyMemo
from prolog.interpreter.term import Var, AttVar, Callable
from prolog.interpreter.error import UnificationFailed

@expose_builtin("term_variables", unwrap_spec=["obj", "obj"])
def impl_term_variables(engine, heap, prolog_term, variables):
    term_variables(engine, heap, prolog_term, variables)

@specialize.arg(4)
def term_variables(engine, heap, prolog_term, variables, consider_attributes=False):
    varlist = []
    varc = variables
    seen = {}
    todo = [prolog_term]
    cls = Var
    if consider_attributes:
        cls = AttVar
    while todo:
        t = todo.pop()
        value = t.dereference(heap)
        if isinstance(value, cls):
            if consider_attributes and value.is_empty():
                continue
            if value not in seen:
                varlist.append(value)
                seen[value] = None
                X = heap.newvar()
                prolog_list = Callable.build(".", [value, X])
                prolog_list.unify(varc, heap)
                varc = X
        elif isinstance(value, Callable):
            numargs = value.argument_count()
            for i in range(numargs - 1, -1, -1):
                todo.append(value.argument_at(i))
    varc.unify(Callable.build("[]"), heap)
