"""codegen helpers and AST constant folding."""
import sys
import itertools

from pypy.interpreter.astcompiler import ast, consts, misc
from pypy.tool import stdlib_opcode as ops
from pypy.interpreter.error import OperationError
from pypy.rlib.unroll import unrolling_iterable


def optimize_ast(space, tree, compile_info):
    return tree.mutate_over(OptimizingVisitor(space, compile_info))


CONST_NOT_CONST = -1
CONST_FALSE = 0
CONST_TRUE = 1


class __extend__(ast.AST):

    def as_constant_truth(self, space):
        """Return the truth of this node if known."""
        raise AssertionError("only for expressions")

    def as_constant(self):
        """Return the value of this node as a wrapped constant if possible."""
        raise AssertionError("only for expressions")

    def accept_jump_if(self, gen, condition, target):
        raise AssertionError("only for expressions")


class __extend__(ast.expr):

    def as_constant_truth(self, space):
        const = self.as_constant()
        if const is None:
            return CONST_NOT_CONST
        return int(space.is_true(const))

    def as_constant(self):
        return None

    def accept_jump_if(self, gen, condition, target):
        self.walkabout(gen)
        if condition:
            gen.emit_jump(ops.POP_JUMP_IF_TRUE, target, True)
        else:
            gen.emit_jump(ops.POP_JUMP_IF_FALSE, target, True)


class __extend__(ast.Num):

    def as_constant(self):
        return self.n


class __extend__(ast.Str):

    def as_constant(self):
        return self.s


class __extend__(ast.Const):

    def as_constant(self):
        return self.value

class __extend__(ast.Index):
    def as_constant(self):
        return self.value.as_constant()

class __extend__(ast.Slice):
    def as_constant(self):
        # XXX: this ought to return a slice object if all the indices are
        # constants, but we don't have a space here.
        return None

class __extend__(ast.UnaryOp):

    def accept_jump_if(self, gen, condition, target):
        if self.op == ast.Not:
            self.operand.accept_jump_if(gen, not condition, target)
        else:
            ast.expr.accept_jump_if(self, gen, condition, target)



class __extend__(ast.BoolOp):

    def _accept_jump_if_any_is(self, gen, condition, target):
        self.values[0].accept_jump_if(gen, condition, target)
        for i in range(1, len(self.values)):
            self.values[i].accept_jump_if(gen, condition, target)

    def accept_jump_if(self, gen, condition, target):
        if condition and self.op == ast.And or \
                (not condition and self.op == ast.Or):
            end = gen.new_block()
            self._accept_jump_if_any_is(gen, not condition, end)
            gen.emit_jump(ops.JUMP_FORWARD, target)
            gen.use_next_block(end)
        else:
            self._accept_jump_if_any_is(gen, condition, target)


def _binary_fold(name):
    def do_fold(space, left, right):
        return getattr(space, name)(left, right)
    return do_fold

def _unary_fold(name):
    def do_fold(space, operand):
        return getattr(space, name)(operand)
    return do_fold

def _fold_pow(space, left, right):
    return space.pow(left, right, space.w_None)

def _fold_not(space, operand):
    return space.wrap(not space.is_true(operand))


binary_folders = {
    ast.Add : _binary_fold("add"),
    ast.Sub : _binary_fold("sub"),
    ast.Mult : _binary_fold("mul"),
    ast.Div : _binary_fold("truediv"),
    ast.FloorDiv : _binary_fold("floordiv"),
    ast.Mod : _binary_fold("mod"),
    ast.Pow : _fold_pow,
    ast.LShift : _binary_fold("lshift"),
    ast.RShift : _binary_fold("rshift"),
    ast.BitOr : _binary_fold("or_"),
    ast.BitXor : _binary_fold("xor"),
    ast.BitAnd : _binary_fold("and_"),
}
unrolling_binary_folders = unrolling_iterable(binary_folders.items())

unary_folders = {
    ast.Not : _fold_not,
    ast.USub : _unary_fold("neg"),
    ast.UAdd : _unary_fold("pos"),
    ast.Invert : _unary_fold("invert")
}
unrolling_unary_folders = unrolling_iterable(unary_folders.items())

for folder in itertools.chain(binary_folders.itervalues(),
                              unary_folders.itervalues()):
    folder._always_inline_ = True
del folder

opposite_compare_operations = misc.dict_to_switch({
    ast.Is : ast.IsNot,
    ast.IsNot : ast.Is,
    ast.In : ast.NotIn,
    ast.NotIn : ast.In
})


class OptimizingVisitor(ast.ASTVisitor):
    """Constant folds AST."""

    def __init__(self, space, compile_info):
        self.space = space
        self.compile_info = compile_info

    def default_visitor(self, node):
        return node

    def visit_BinOp(self, binop):
        left = binop.left.as_constant()
        if left is not None:
            right = binop.right.as_constant()
            if right is not None:
                op = binop.op
                # Can't fold straight division without "from __future_ import
                # division" because it might be affected at runtime by the -Q
                # flag.
                if op == ast.Div and \
                        not self.compile_info.flags & consts.CO_FUTURE_DIVISION:
                    return binop
                try:
                    for op_kind, folder in unrolling_binary_folders:
                        if op_kind == op:
                            w_const = folder(self.space, left, right)
                            break
                    else:
                        raise AssertionError("unknown binary operation")
                # Let all errors be found at runtime.
                except OperationError:
                    pass
                else:
                    # To avoid blowing up the size of pyc files, we only fold
                    # reasonably sized sequences.
                    try:
                        w_len = self.space.len(w_const)
                    except OperationError:
                        pass
                    else:
                        if self.space.int_w(w_len) > 20:
                            return binop
                    return ast.Const(w_const, binop.lineno, binop.col_offset)
        return binop

    def visit_UnaryOp(self, unary):
        w_operand = unary.operand.as_constant()
        op = unary.op
        if w_operand is not None:
            try:
                for op_kind, folder in unrolling_unary_folders:
                    if op_kind == op:
                        w_const = folder(self.space, w_operand)
                        break
                else:
                    raise AssertionError("unknown unary operation")
                w_minint = self.space.wrap(-sys.maxint - 1)
                # This makes sure the result is an integer.
                if self.space.eq_w(w_minint, w_const):
                    w_const = w_minint
            except OperationError:
                pass
            else:
                return ast.Const(w_const, unary.lineno, unary.col_offset)
        elif op == ast.Not:
            compare = unary.operand
            if isinstance(compare, ast.Compare) and len(compare.ops) == 1:
                cmp_op = compare.ops[0]
                try:
                    opposite = opposite_compare_operations(cmp_op)
                except KeyError:
                    pass
                else:
                    compare.ops[0] = opposite
                    return compare
        return unary

    def visit_BoolOp(self, bop):
        values = bop.values
        we_are_and = bop.op == ast.And
        i = 0
        while i < len(values) - 1:
            truth = values[i].as_constant_truth(self.space)
            if truth != CONST_NOT_CONST:
                if (truth != CONST_TRUE) == we_are_and:
                    del values[i + 1:]
                    break
                else:
                    del values[i]
            else:
                i += 1
        if len(values) == 1:
            return values[0]
        return bop

    def visit_Repr(self, rep):
        w_const = rep.value.as_constant()
        if w_const is not None:
            w_repr = self.space.repr(w_const)
            return ast.Const(w_repr, rep.lineno, rep.col_offset)
        return rep

    def visit_Name(self, name):
        # Turn loading None into a constant lookup.  Eventaully, we can do this
        # for True and False, too.
        if name.id == "None":
            assert name.ctx == ast.Load
            return ast.Const(self.space.w_None, name.lineno, name.col_offset)
        return name

    def visit_Tuple(self, tup):
        """Try to turn tuple building into a constant."""
        if tup.elts:
            consts_w = [None]*len(tup.elts)
            for i in range(len(tup.elts)):
                node = tup.elts[i]
                w_const = node.as_constant()
                if w_const is None:
                    return tup
                consts_w[i] = w_const
        else:
            consts_w = []
        w_consts = self.space.newtuple(consts_w)
        return ast.Const(w_consts, tup.lineno, tup.col_offset)

    def visit_Subscript(self, subs):
        if subs.ctx == ast.Load:
            w_obj = subs.value.as_constant()
            if w_obj is not None:
                w_idx = subs.slice.as_constant()
                if w_idx is not None:
                    try:
                        return ast.Const(self.space.getitem(w_obj, w_idx), subs.lineno, subs.col_offset)
                    except OperationError:
                        # Let exceptions propgate at runtime.
                        pass
        return subs
