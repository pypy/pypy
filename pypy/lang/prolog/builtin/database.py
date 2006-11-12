import py
from pypy.lang.prolog.interpreter import engine, helper, term, error
from pypy.lang.prolog.builtin.register import expose_builtin

# ___________________________________________________________________
# database

def impl_abolish(engine, predicate):
    from pypy.lang.prolog.builtin import builtins
    name, arity = helper.unwrap_predicate_indicator(predicate)
    if arity < 0:
        error.throw_domain_error("not_less_than_zero", term.Number(arity))
    signature = name + "/" + str(arity)
    if signature in builtins:
        error.throw_permission_error("modify", "static_procedure",
                                     predicate)
    if signature in engine.signature2rules:
        del engine.signature2rules[signature]
expose_builtin(impl_abolish, "abolish", unwrap_spec=["obj"])

def impl_assert(engine, rule):
    engine.add_rule(rule.getvalue(engine.frame))
expose_builtin(impl_assert, ["assert", "assertz"], unwrap_spec=["callable"])

def impl_asserta(engine, rule):
    engine.add_rule(rule.getvalue(engine.frame), end=False)
expose_builtin(impl_asserta, "asserta", unwrap_spec=["callable"])


def impl_retract(engine, pattern):
    from pypy.lang.prolog.builtin import builtins
    if isinstance(pattern, term.Term) and pattern.name == ":-":
        head = helper.ensure_callable(pattern.args[0])
        body = helper.ensure_callable(pattern.args[1])
    else:
        head = pattern
        body = None
    if head.signature in builtins:
        assert isinstance(head, term.Callable)
        error.throw_permission_error("modify", "static_procedure", 
                                     head.get_prolog_signature())
    rules = engine.signature2rules.get(head.signature, [])
    for i in range(len(rules)):
        rule = rules[i]
        oldstate = engine.frame.branch()
        # standardizing apart
        try:
            deleted_body = rule.clone_and_unify_head(engine.frame, head)
            if body is not None:
                body.unify(deleted_body, engine.frame)
        except error.UnificationFailed:
            engine.frame.revert(oldstate)
        else:
            del rules[i]
            break
    else:
        raise error.UnificationFailed()
expose_builtin(impl_retract, "retract", unwrap_spec=["callable"])


