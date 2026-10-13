"""Optimization passes over the generated matching-code IR."""
from rpython.jit.metainterp.ruleopt import ir


def optimize(block):
    """Optimize a generated matcher body in place."""
    remove_unused_bindings(block)
    while True:
        guards_changed = remove_redundant_guards(block)
        if guards_changed:
            remove_unused_bindings(block)
        down_changed = move_bindings_down(block)
        in_changed = move_bindings_in(block)
        if not (guards_changed or down_changed or in_changed):
            return


def used_values(node):
    """Return the Value identities referenced anywhere in a subtree."""
    return {ref.value for ref in node.walk(ir.Ref)}


def same_expression(left, right):
    """Compare expression structure, using identity for referenced Values."""
    if type(left) is not type(right):
        return False
    if isinstance(left, ir.Ref):
        return left.value is right.value
    if isinstance(left, ir.Literal):
        return type(left.value) is type(right.value) and left.value == right.value
    if isinstance(left, ir.Symbol):
        return left.name == right.name
    if isinstance(left, ir.Attribute):
        if left.name != right.name:
            return False
    elif isinstance(left, (ir.Unary, ir.Binary)):
        if left.operator != right.operator:
            return False
    elif isinstance(left, ir.Call):
        if left.side_effects != right.side_effects:
            return False
        if [name for name, expr in left.keywords] != [
                name for name, expr in right.keywords]:
            return False
    elif not isinstance(left, ir.ListExpr):
        return False
    left_children = list(left.iter_children())
    right_children = list(right.iter_children())
    return (len(left_children) == len(right_children) and
            all(same_expression(a, b)
                for a, b in zip(left_children, right_children)))


def remove_redundant_guards(block):
    """Remove adjacent repeated guards after returning true arms, in place.

    If the first guard succeeds, it returns; if it fails, its empty else arm
    leaves matching state unchanged. An identical effect-free guard must then
    fail too. Require an empty second else arm so the entire If can be removed.

    Like the movement passes, this relies on matching reads being stable until
    a rewrite. Return whether anything was removed.
    """
    changed = False
    for sub in block.walk(ir.Block):
        statements = sub.statements
        i = 0
        while i + 1 < len(statements):
            first, second = statements[i:i + 2]
            if (isinstance(first, ir.If) and isinstance(second, ir.If)
                    and not first.else_block.statements
                    and not second.else_block.statements
                    and first.then_block.statements
                    and isinstance(first.then_block.statements[-1],
                                   (ir.Return, ir.FinishRule))
                    and not first.condition.has_side_effects()
                    and same_expression(first.condition, second.condition)):
                del statements[i + 1]
                changed = True
            else:
                i += 1
    return changed


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

    Look ahead from a Bind to an If, crossing only effect-free bindings that
    do not use its Value. Only reorder bindings when moving into a branch.
    The RHS must be effect-free;
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
            value = stmt.value
            j = i + 1
            while j < len(statements) and isinstance(statements[j], ir.Bind):
                intervening = statements[j]
                if (intervening.expr.has_side_effects()
                        or value in used_values(intervening)):
                    break
                j += 1
            if j == len(statements):
                continue
            branch = statements[j]
            if not isinstance(branch, ir.If):
                continue
            if value in used_values(branch.condition):
                continue
            if value in used_values(ir.Block(statements[j + 1:])):
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
