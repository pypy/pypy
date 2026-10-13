"""Optimization passes over the generated matching-code IR."""
from rpython.jit.metainterp.ruleopt import ir


def optimize(block):
    """Optimize a generated matcher body in place."""
    remove_unused_bindings(block)
    move_bindings_down(block)


def used_values(node):
    """Return the Value identities referenced anywhere in a subtree."""
    return {ref.value for ref in node.walk(ir.Ref)}


def remove_unused_bindings(block):
    """Remove unused bindings with effect-free right-hand sides, in place.

    Mutates block and returns None. Effectful RHSs and ExprStmts are retained.
    Repeat until stable: deleting a binding can make its inputs unused too.
    """
    while True:
        used = used_values(block)
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


def move_bindings_down(block):
    """Move bindings past If statements that do not use them, in place.

    This relies on the generated matcher's invariant: matching inspects state;
    a successful rewrite mutates state and returns. Values have unique
    definitions. This is not a pass for arbitrary Python programs.

    Exercise: swap adjacent Bind / If pairs when the binding's RHS has no
    side effects and its Value is absent from used_values(the_if). Repeat
    until no more swaps apply, including inside nested blocks.

    Preserve the relative order of bindings. Do not move them across other
    kinds of statements or into branches; inward movement is a separate pass.
    Mutates block and returns None.
    """
    def move_down(block):
        changed = True
        while changed:
            changed = False
            for i, stmt in enumerate(block.statements):
                if not isinstance(stmt, ir.Bind):
                    continue
                if stmt.expr.has_side_effects():
                    continue
                if i + 1 >= len(block.statements):
                    continue
                next = block.statements[i + 1]
                if not isinstance(next, ir.If):
                    continue
                used = used_values(next)
                if stmt.value in used:
                    continue
                block.statements[i], block.statements[i + 1] = block.statements[i + 1], block.statements[i]
                changed = True
    for sub in block.walk(ir.Block):
        move_down(sub)
