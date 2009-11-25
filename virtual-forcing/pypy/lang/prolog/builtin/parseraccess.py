import py
from pypy.lang.prolog.interpreter import engine, helper, term, error
from pypy.lang.prolog.builtin.register import expose_builtin

# ___________________________________________________________________
# operators

def impl_current_op(engine, precedence, typ, name, continuation):
    for prec, allops in engine.getoperations():
        for form, ops in allops:
            for op in ops:
                oldstate = engine.heap.branch()
                try:
                    precedence.unify(term.Number(prec), engine.heap)
                    typ.unify(term.Atom.newatom(form), engine.heap)
                    name.unify(term.Atom(op), engine.heap)
                    return continuation.call(engine, choice_point=True)
                except error.UnificationFailed:
                    engine.heap.revert(oldstate)
    raise error.UnificationFailed()
expose_builtin(impl_current_op, "current_op", unwrap_spec=["obj", "obj", "obj"],
               handles_continuation=True)

def impl_op(engine, precedence, typ, name):
    from pypy.lang.prolog.interpreter import parsing
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
expose_builtin(impl_op, "op", unwrap_spec=["int", "atom", "atom"])


