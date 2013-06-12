from prolog.builtin.register import expose_builtin
from prolog.interpreter import continuation
from prolog.interpreter.term import AttVar, Var, Callable, Atom
from prolog.interpreter.error import UnificationFailed,\
throw_representation_error, throw_instantiation_error
from prolog.interpreter.helper import wrap_list, is_term, unwrap_list
from prolog.interpreter.signature import Signature
from prolog.builtin.term_variables import term_variables

conssig = Signature.getsignature(".", 2)

@expose_builtin("attvar", unwrap_spec=["obj"])
def impl_attvar(engine, heap, obj):
    if not isinstance(obj, AttVar):
        raise UnificationFailed()
    if obj.is_empty():
        raise UnificationFailed()
        
@expose_builtin("put_attr", unwrap_spec=["obj", "atom", "obj"])
def impl_put_attr(engine, heap, var, attr, value):
    if isinstance(var, AttVar):
        old_value, _ = var.get_attribute(attr)
        var.add_attribute(attr, value)
        _, index = var.get_attribute(attr)
        heap.trail_new_attr(var, index, old_value)
    elif isinstance(var, Var):
        attvar = heap.new_attvar()
        attvar.add_attribute(attr, value)
        var.unify(attvar, heap)
    else:
        throw_representation_error("put_attr/3",
                "argument must be unbound (1-st argument)")

@expose_builtin("get_attr", unwrap_spec=["obj", "atom", "obj"])
def impl_get_attr(engine, heap, var, attr, value):
    if not isinstance(var, Var):
        throw_instantiation_error(var)
    if not isinstance(var, AttVar):
        raise UnificationFailed()
    attribute_value, _ = var.get_attribute(attr)
    if attribute_value is not None:
        value.unify(attribute_value, heap)
    else:
        raise UnificationFailed()
 
@expose_builtin("del_attr", unwrap_spec=["obj", "atom"])
def impl_del_attr(engine, heap, var, attr):
    if isinstance(var, AttVar):
        heap.add_trail_atts(var, attr)
        var.del_attribute(attr)

@expose_builtin("term_attvars", unwrap_spec=["obj", "obj"])
def impl_term_attvars(engine, heap, prolog_term, variables):
    term_variables(engine, heap, prolog_term, variables, True)

@expose_builtin("copy_term", unwrap_spec=["obj", "obj", "obj"])
def impl_copy_term_3(engine, heap, prolog_term, copy, goals):
    from prolog.interpreter.memo import CopyMemo
    gs = []
    memo = CopyMemo()
    X = heap.newvar()
    impl_term_attvars(engine, heap, prolog_term, X)
    attvars = unwrap_list(X.dereference(heap))
    for attvar in attvars:
        V = heap.newvar()
        memo.set(attvar, V)
        assert isinstance(attvar, AttVar)
        for module, index in attvar.attmap.indexes.iteritems():
            val = attvar.value_list[index]
            put_attr = Callable.build("put_attr", [V, Callable.build(module), val])
            gs.append(put_attr)
    prolog_term.copy(heap, memo).unify(copy, heap)
    goals.unify(wrap_list(gs), heap)

@expose_builtin("del_attrs", unwrap_spec=["obj"])
def impl_del_attrs(engine, heap, attvar):
    if isinstance(attvar, AttVar):
        if attvar.value_list is not None:
            for name, index in attvar.attmap.indexes.iteritems():
                heap.add_trail_atts(attvar, name)
            attvar.value_list = None
