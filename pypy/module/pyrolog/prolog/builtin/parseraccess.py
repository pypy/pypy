import py
from prolog.interpreter import helper, term, error
from prolog.builtin.register import expose_builtin

# ___________________________________________________________________
# operators

@expose_builtin("current_op", unwrap_spec=["obj", "obj", "obj"],
                handles_continuation=True)
def impl_current_op(engine, heap, precedence, typ, name, continuation):
    oldstate = heap.branch()
    for prec, allops in engine.getoperations():
        for form, ops in allops:
            for op in ops:
                try:
                    precedence.unify(term.Number(prec), heap)
                    typ.unify(term.Callable.build(form), heap)
                    name.unify(term.Callable.build(op), heap)
                    return continuation.call(engine, choice_point=True)
                except error.UnificationFailed:
                    heap.revert(oldstate)
    heap.discard(oldstate)
    raise error.UnificationFailed()

@expose_builtin("op", unwrap_spec=["int", "atom", "atom"])
def impl_op(engine, heap, precedence, typ, name):
    from prolog.interpreter import parsing
    if engine.operations is None:
        engine.operations = parsing.make_default_operations()
    operations = engine.operations
    precedence_to_ops = {}
    for prec, allops in operations:
        precedence_to_ops[prec] = allops
        for form, ops in allops:
            try:
                index = ops.index(name)
                del ops[index]
            except ValueError:
                pass
    if precedence != 0:
        if precedence in precedence_to_ops:
            allops = precedence_to_ops[precedence]
            for form, ops in allops:
                if form == typ:
                    ops.append(name)
                    break
            else:
                allops.append((typ, [name]))
        else:
            for i in range(len(operations)):
                (prec, allops) = operations[i]
                if precedence > prec:
                    operations.insert(i, (precedence, [(typ, [name])]))
                    break
            else:
                operations.append((precedence, [(typ, [name])]))
    engine.parser = parsing.make_parser_at_runtime(engine.operations)


