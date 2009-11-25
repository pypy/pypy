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
    if signature in engine.signature2function:
        del engine.signature2function[signature]
expose_builtin(impl_abolish, "abolish", unwrap_spec=["obj"])

def impl_assert(engine, rule):
    engine.add_rule(rule.getvalue(engine.heap))
expose_builtin(impl_assert, ["assert", "assertz"], unwrap_spec=["callable"])

def impl_asserta(engine, rule):
    engine.add_rule(rule.getvalue(engine.heap), end=False)
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
    function = engine.signature2function.get(head.signature, None)
    if function is None:
        raise error.UnificationFailed
    #import pdb; pdb.set_trace()
    rulechain = function.rulechain
    while rulechain:
        rule = rulechain.rule
        oldstate = engine.heap.branch()
        # standardizing apart
        try:
            deleted_body = rule.clone_and_unify_head(engine.heap, head)
            if body is not None:
                body.unify(deleted_body, engine.heap)
        except error.UnificationFailed:
            engine.heap.revert(oldstate)
        else:
            if function.rulechain is rulechain:
                if rulechain.next is None:
                    del engine.signature2function[head.signature]
                else:
                    function.rulechain = rulechain.next
            else:
                function.remove(rulechain)
            break
        rulechain = rulechain.next
    else:
        raise error.UnificationFailed()
expose_builtin(impl_retract, "retract", unwrap_spec=["callable"])


