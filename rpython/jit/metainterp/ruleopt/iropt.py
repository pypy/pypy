"""Optimization passes over the generated matching-code IR."""
from rpython.jit.metainterp.ruleopt import ir


def remove_unused_bindings(block):
    """Remove unused bindings with effect-free right-hand sides, in place.

    Mutates block and returns None. Effectful RHSs and ExprStmts are retained.
    Repeat until stable: deleting a binding can make its inputs unused too.
    """
    while True:
        used = set()
        for ref in block.walk(ir.Ref):
            used.add(ref.value)
        changed = False
        for node in block.walk(ir.Block):
            i = 0
            while i < len(node.statements):
                stmt = node.statements[i]
                if (isinstance(stmt, ir.Bind) and stmt.value not in used
                        and not stmt.expr.has_side_effects()):
                    del node.statements[i]
                    changed = True
                else:
                    i += 1
        if not changed:
            return
