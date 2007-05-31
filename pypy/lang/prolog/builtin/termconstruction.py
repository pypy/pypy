import py
from pypy.lang.prolog.interpreter import engine, helper, term, error
from pypy.lang.prolog.builtin.register import expose_builtin

# ___________________________________________________________________
# analysing and construction terms

def impl_functor(engine, t, functor, arity):
    if helper.is_atomic(t):
        functor.unify(t, engine.heap)
        arity.unify(term.Number(0), engine.heap)
    elif isinstance(t, term.Term):
        functor.unify(term.Atom(t.name), engine.heap)
        arity.unify(term.Number(len(t.args)), engine.heap)
    elif isinstance(t, term.Var):
        if isinstance(functor, term.Var):
            error.throw_instantiation_error()
        a = helper.unwrap_int(arity)
        if a < 0:
            error.throw_domain_error("not_less_than_zero", arity)
        else:
            functor = helper.ensure_atomic(functor)
            if a == 0:
                t.unify(helper.ensure_atomic(functor), engine.heap)
            else:
                name = helper.unwrap_atom(functor)
                t.unify(
                    term.Term(name, [term.Var() for i in range(a)]),
                    engine.heap)
expose_builtin(impl_functor, "functor", unwrap_spec=["obj", "obj", "obj"])

def impl_arg(engine, first, second, third, continuation):
    if isinstance(second, term.Var):
        error.throw_instantiation_error()
    if isinstance(second, term.Atom):
        raise error.UnificationFailed()
    if not isinstance(second, term.Term):
        error.throw_type_error("compound", second)
    if isinstance(first, term.Var):
        for i in range(len(second.args)):
            arg = second.args[i]
            oldstate = engine.heap.branch()
            try:
                third.unify(arg, engine.heap)
                first.unify(term.Number(i + 1), engine.heap)
                return continuation.call(engine, choice_point=True)
            except error.UnificationFailed:
                engine.heap.revert(oldstate)
        raise error.UnificationFailed()
    elif isinstance(first, term.Number):
        num = first.num
        if num == 0:
            raise error.UnificationFailed
        if num < 0:
            error.throw_domain_error("not_less_than_zero", first)
        if num > len(second.args):
            raise error.UnificationFailed()
        arg = second.args[num - 1]
        third.unify(arg, engine.heap)
    else:
        error.throw_type_error("integer", first)
    return continuation.call(engine, choice_point=False)
expose_builtin(impl_arg, "arg", unwrap_spec=["obj", "obj", "obj"],
               handles_continuation=True)

def impl_univ(engine, first, second):
    if not isinstance(first, term.Var):
        if isinstance(first, term.Term):
            l = [term.Atom(first.name)] + first.args
        else:
            l = [first]
        u1 = helper.wrap_list(l)
        if not isinstance(second, term.Var):
            u1.unify(second, engine.heap)
        else:
            u1.unify(second, engine.heap)
    else:
        if isinstance(second, term.Var):
            error.throw_instantiation_error()
        else:
            l = helper.unwrap_list(second)
            head = l[0]
            if not isinstance(head, term.Atom):
                error.throw_type_error("atom", head)
            term.Term(head.name, l[1:]).unify(first, engine.heap)
expose_builtin(impl_univ, "=..", unwrap_spec=["obj", "obj"])

def impl_copy_term(engine, interm, outterm):
    d = {}
    copy = interm.copy(engine.heap, d)
    outterm.unify(copy, engine.heap)
expose_builtin(impl_copy_term, "copy_term", unwrap_spec=["obj", "obj"])


