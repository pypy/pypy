"""Optimization passes over the generated matching-code IR."""
from rpython.jit.metainterp.ruleopt import ir


def optimize(block):
    """Optimize a generated matcher body in place."""
    remove_unused_bindings(block)
    while True:
        down_changed = move_bindings_down(block)
        in_changed = move_bindings_in(block)
        if not (down_changed or in_changed):
            return


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

    Preserve the relative order of bindings. Do not move them across other
    kinds of statements or into branches; inward movement is a separate pass.
    Mutates block and returns whether anything moved.
    """
    changed = False
    for sub in block.walk(ir.Block):
        statements = sub.statements
        # Move later bindings first, exposing checks to earlier bindings.
        for i in range(len(statements) - 2, -1, -1):
            stmt = statements[i]
            if not isinstance(stmt, ir.Bind) or stmt.expr.has_side_effects():
                continue
            while i + 1 < len(statements):
                branch = statements[i + 1]
                if not isinstance(branch, ir.If):
                    break
                if stmt.value in used_values(branch):
                    break
                statements[i], statements[i + 1] = branch, stmt
                i += 1
                changed = True
    return changed


def move_bindings_in(block):
    """Move a binding into the single If branch that needs it, in place.

    Uses the same matcher invariants as move_bindings_down. Mutates block
    and returns whether anything moved. Never duplicates a binding or moves
    it outward.

    Consider adjacent Bind / If pairs. The RHS must be effect-free;
    the Value must be unused in the condition and all following statements,
    and used in exactly one branch. Remove the Bind from its original block
    and prepend it to that branch.

    Scan backward so moving a binding exposes earlier eligible pairs. Walking
    blocks in preorder then visits the branch containing the moved bindings.
    """
    changed = False
    for sub in block.walk(ir.Block):
        statements = sub.statements
        for i in range(len(statements) - 2, -1, -1):
            stmt = statements[i]
            if not isinstance(stmt, ir.Bind) or stmt.expr.has_side_effects():
                continue
            branch = statements[i + 1]
            if not isinstance(branch, ir.If):
                continue
            value = stmt.value
            if value in used_values(branch.condition):
                continue
            if value in used_values(ir.Block(statements[i + 2:])):
                continue
            used_then = value in used_values(branch.then_block)
            used_else = value in used_values(branch.else_block)
            if used_then == used_else:
                continue
            destination = branch.then_block if used_then else branch.else_block
            del statements[i]
            destination.statements.insert(0, stmt)
            changed = True
    return changed
