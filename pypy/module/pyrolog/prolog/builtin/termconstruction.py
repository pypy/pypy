import py
from prolog.interpreter import helper, term, error, continuation
from prolog.builtin.register import expose_builtin
from rpython.rlib import jit
# ___________________________________________________________________
# analysing and construction terms

@expose_builtin("functor", unwrap_spec=["obj", "obj", "obj"])
@jit.unroll_safe
def impl_functor(engine, heap, t, functor, arity):
    if helper.is_atomic(t):
        functor.unify(t, heap)
        arity.unify(term.Number(0), heap)
    elif helper.is_term(t):
        assert isinstance(t, term.Callable)
        sig = t.signature()
        atom = term.Callable.build(t.name(), signature=sig.atom_signature)
        functor.unify(atom, heap)
        arity.unify(term.Number(t.argument_count()), heap)
    elif isinstance(t, term.Var):
        if isinstance(functor, term.Var):
            error.throw_instantiation_error()
        a = helper.unwrap_int(arity)
        jit.promote(a)
        if a < 0:
            error.throw_domain_error("not_less_than_zero", arity)
        else:
            functor = helper.ensure_atomic(functor)
            if a == 0:
                t.unify(functor, heap)
            else:
                jit.promote(functor)
                name = helper.unwrap_atom(functor)
                t.unify(
                    term.Callable.build(name, [heap.newvar() for i in range(a)]),
                    heap)

@continuation.make_failure_continuation
def continue_arg(Choice, engine, scont, fcont, heap, varnum, num, temarg, vararg):
    if num < temarg.argument_count() - 1:
        fcont = Choice(engine, scont, fcont, heap, varnum, num + 1, temarg, vararg)
        heap = heap.branch()
    scont = continuation.BodyContinuation(
            engine, engine.modulewrapper.user_module, scont, term.Callable.build("=", [vararg, temarg.argument_at(num)]))
    varnum.unify(term.Number(num + 1), heap)
    return scont, fcont, heap

@expose_builtin("arg", unwrap_spec=["obj", "obj", "obj"],
handles_continuation=True)
def impl_arg(engine, heap, first, second, third, scont, fcont):
    if isinstance(second, term.Var):
        error.throw_instantiation_error()
    if isinstance(second, term.Atom):
        raise error.UnificationFailed()
        error.throw_type_error('compound', second)
    if not helper.is_term(second):
        error.throw_type_error("compound", second)
    assert isinstance(second, term.Callable)
    if isinstance(first, term.Var):
        return continue_arg(engine, scont, fcont, heap, first, 0, second, third)
    elif isinstance(first, term.Number):
        num = first.num
        if num == 0:
            raise error.UnificationFailed
        if num < 0:
            error.throw_domain_error("not_less_than_zero", first)
        if num > second.argument_count():
            raise error.UnificationFailed()
        arg = second.argument_at(num - 1)
        third.unify(arg, heap)
    else:
        error.throw_type_error("integer", first)
    return scont, fcont, heap

@expose_builtin("=..", unwrap_spec=["obj", "obj"])
@jit.unroll_safe
def impl_univ(engine, heap, first, second):
    if not isinstance(first, term.Var):
        if helper.is_term(first):
            assert isinstance(first, term.Callable)
            sig = first.signature().atom_signature
            l = [term.Callable.build(first.name(), signature=sig)] + first.arguments()
        else:
            l = [first]
        u1 = helper.wrap_list(l)
        if not isinstance(second, term.Var):
            u1.unify(second, heap)
        else:
            u1.unify(second, heap)
    else:
        if isinstance(second, term.Var):
            error.throw_instantiation_error()
        else:
            l = helper.unwrap_list(second)
            head = l[0].dereference(heap)
            if not isinstance(head, term.Atom):
                error.throw_type_error("atom", head)
            l2 = [None] * (len(l) - 1)
            for i in range(len(l2)):
                l2[i] = l[i + 1]
            name = jit.hint(head.signature(), promote=True).name
            term.Callable.build(name, l2).unify(first, heap)

@expose_builtin("copy_term", unwrap_spec=["obj", "obj"])
def impl_copy_term(engine, heap, interm, outterm):
    from prolog.interpreter.memo import CopyMemo
    m = CopyMemo()
    copy = interm.copy(heap, m)
    outterm.unify(copy, heap)


