from pypy.tool.pairtype import extendabletype
from pypy.interpreter.astcompiler import ast
from pypy.interpreter.error import OperationError

# Extra bytecode optimizations.  Two styles: a visitor (a mutator really)
# that modifies the AST tree in-place, and hooks for pycodegen to produce
# better bytecode.  The visitor pattern is a bit of a mess for the latter,
# so we simply stick new methods on the nodes.

OPTIMIZE = True

def is_constant_false(space, node):
    return isinstance(node, ast.Const) and not space.is_true(node.value)

def is_constant_true(space, node):
    return isinstance(node, ast.Const) and space.is_true(node.value)


class __extend__(ast.Node):
    __metaclass__ = extendabletype

    def opt_accept_jump_if(self, codegen, condition, target):
        """Generate code equivalent to:
               self.accept()
               JUMP_IF_condition target
        except that the value left on the stack afterwards (both if the
        branch is taken or not) can be garbage.
        """
        self.accept(codegen)
        if condition:
            codegen.emitop_block('JUMP_IF_TRUE', target)
        else:
            codegen.emitop_block('JUMP_IF_FALSE', target)


if not OPTIMIZE:
    def optimize_ast_tree(space, tree):
        return tree

else:

    class __extend__(ast.Not):
        __metaclass__ = extendabletype

        def opt_accept_jump_if(self, codegen, condition, target):
            self.expr.opt_accept_jump_if(codegen, not condition, target)


    class __extend__(ast.AbstractTest):
        __metaclass__ = extendabletype

        def _accept_jump_if_any_is(self, codegen, condition, target):
            # generate a "jump if any of the nodes' truth value is 'condition'"
            garbage_on_stack = False
            for node in self.nodes:
                if garbage_on_stack:
                    codegen.emit('POP_TOP')
                node.opt_accept_jump_if(codegen, condition, target)
                garbage_on_stack = True
            assert garbage_on_stack

        def opt_accept_jump_if(self, codegen, condition, target):
            if condition == self.is_and:
                # jump only if all the nodes' truth values are equal to
                # 'condition'
                end = codegen.newBlock()
                self._accept_jump_if_any_is(codegen, not condition, end)
                codegen.emitop_block('JUMP_FORWARD', target)
                codegen.nextBlock(end)
            else:
                self._accept_jump_if_any_is(codegen, condition, target)


    class __extend__(ast.And):
        __metaclass__ = extendabletype
        is_and = True

    class __extend__(ast.AbstractTest):
        __metaclass__ = extendabletype
        is_and = False


    class OptimizerMutator(ast.ASTVisitor):
        def __init__(self, space):
            self.space = space

        def default(self, node):
            return node

        def _visitUnaryOp(self, node, constant_fold):
            expr = node.expr
            if isinstance(expr, ast.Const):
                try:
                    w_newvalue = constant_fold(self.space, expr.value)
                except OperationError:
                    pass
                else:
                    return ast.Const(w_newvalue)
            return node

        def visitBackquote(self, node):
            return self._visitUnaryOp(node, _spacewrapper1('repr'))
        def visitInvert(self, node):
            return self._visitUnaryOp(node, _spacewrapper1('invert'))
        def visitUnaryAdd(self, node):
            return self._visitUnaryOp(node, _spacewrapper1('pos'))
        def visitUnarySub(self, node):
            return self._visitUnaryOp(node, _spacewrapper1('neg'))
        def visitNot(self, node):
            expr = node.expr
            if isinstance(expr, ast.Compare) and len(expr.ops) == 1:
                op, subnode = expr.ops[0]
                if op in opposite_cmp_op:
                    # not (x in y) ===> x not in y   (resp: not in, is, etc.)
                    expr.ops[0] = opposite_cmp_op[op], subnode
                    return expr
            return self._visitUnaryOp(node, _spacewrapper1('not_'))

        def _visitBinaryOp(self, node, constant_fold):
            left = node.left
            right = node.right
            if isinstance(left, ast.Const) and isinstance(right, ast.Const):
                try:
                    w_newvalue = constant_fold(self.space, left.value,
                                               right.value)
                except OperationError:
                    pass
                else:
                    # to avoid creating too large .pyc files, we don't
                    # constant-fold operations that create long sequences,
                    # like '(5,) * 500'.  This is the same as CPython.
                    try:
                        size = self.space.int_w(self.space.len(w_newvalue))
                    except OperationError:
                        size = -1
                    if size <= 20:
                        return ast.Const(w_newvalue)
            return node

        def visitAdd(self, node):
            return self._visitBinaryOp(node, _spacewrapper2('add'))
        #def visitDiv(self, node):
        #    cannot constant-fold because the result depends on
        #    whether future division is enabled or not
        def visitFloorDiv(self, node):
            return self._visitBinaryOp(node, _spacewrapper2('floordiv'))
        def visitLeftShift(self, node):
            return self._visitBinaryOp(node, _spacewrapper2('lshift'))
        def visitMod(self, node):
            return self._visitBinaryOp(node, _spacewrapper2('mod'))
        def visitMul(self, node):
            return self._visitBinaryOp(node, _spacewrapper2('mul'))
        def visitPower(self, node):
            return self._visitBinaryOp(node, constant_fold_pow)
        def visitRightShift(self, node):
            return self._visitBinaryOp(node, _spacewrapper2('rshift'))
        def visitSub(self, node):
            return self._visitBinaryOp(node, _spacewrapper2('sub'))

        #def visitSubscript(self, node): XXX

        def _visitBitOp(self, node, constant_fold):
            while len(node.nodes) >= 2:
                left = node.nodes[0]
                if not isinstance(left, ast.Const):
                    return node     # done
                right = node.nodes[1]
                if not isinstance(right, ast.Const):
                    return node     # done
                try:
                    w_newvalue = constant_fold(self.space, left.value,
                                               right.value)
                except OperationError:
                    return node     # done
                del node.nodes[1]
                node.nodes[0] = ast.Const(w_newvalue)
            else:
                # if reduced to a single node, just returns it
                return node.nodes[0]

        def visitBitand(self, node):
            return self._visitBitOp(node, _spacewrapper2('and_'))
        def visitBitor(self, node):
            return self._visitBitOp(node, _spacewrapper2('or_'))
        def visitBitxor(self, node):
            return self._visitBitOp(node, _spacewrapper2('xor'))

        def _List2Tuple(self, node):
            if isinstance(node, ast.List):
                newnode = ast.Tuple(node.nodes)
                copy_node_fields(node, newnode)
                # if the resulting tuple contains only constants, we can
                # completely constant-fold the tuple creation itself
                return self.visitTuple(newnode)
            else:
                return node

        def visitCompare(self, node):
            # xxx could do some constant-folding too, even if it sounds
            # a bit unlikely to be useful in practice
            last_op_name, last_subnode = node.ops[-1]
            if last_op_name == 'in' or last_op_name == 'not in':
                node.ops[-1] = last_op_name, self._List2Tuple(last_subnode)
            return node

        def _visitAbstractTest(self, node, is_and):
            # Logic for And nodes:
            # 1. if any of the nodes is True, it can be removed
            # 2. if any of the nodes is False, all nodes after it can be killed
            # For Or nodes, the conditions are reversed.
            i = 0
            nodes = node.nodes
            while i < len(nodes) - 1:
                subnode = nodes[i]
                if isinstance(subnode, ast.Const):
                    if (not self.space.is_true(subnode.value)) == is_and:
                        del nodes[i+1:]    # case 2.
                        break
                    else:
                        del nodes[i]
                        continue           # case 1.
                i += 1
            if len(nodes) > 1:
                return node
            else:
                return nodes[0]       # a single item left

        def visitAnd(self, node):
            return self._visitAbstractTest(node, True)
        def visitOr(self, node):
            return self._visitAbstractTest(node, False)

        def visitTuple(self, node):
            nodes = node.nodes
            consts_w = [None] * len(nodes)
            for i in range(len(nodes)):
                subnode = nodes[i]
                if not isinstance(subnode, ast.Const):
                    return node     # not all constants
                consts_w[i] = subnode.value
            return ast.Const(self.space.newtuple(consts_w))

        def visitFor(self, node):
            node.list = self._List2Tuple(node.list)
            return node

        def visitListCompFor(self, node):
            node.list = self._List2Tuple(node.list)
            return node

        def visitGenExprFor(self, node):
            node.iter = self._List2Tuple(node.iter)
            return node


    def _spacewrapper1(name):
        """Make a wrapper around the method: space.<name>(w_x)
        to avoid taking bound method objects, which creates issues
        depending on the details of the real space method, e.g. default args.
        """
        def constant_fold(space, w_x):
            return getattr(space, name)(w_x)
        return constant_fold
    _spacewrapper1._annspecialcase_ = 'specialize:memo'

    def _spacewrapper2(name):
        """Make a wrapper around the method: space.<name>(w_x, w_y)
        to avoid taking bound method objects, which creates issues
        depending on the details of the real space method, e.g. default args.
        """
        def constant_fold(space, w_x, w_y):
            return getattr(space, name)(w_x, w_y)
        return constant_fold
    _spacewrapper2._annspecialcase_ = 'specialize:memo'

    def constant_fold_pow(space, w_x, w_y):
        return space.pow(w_x, w_y, space.w_None)

    def copy_node_fields(src, dst):
        dst.lineno = src.lineno
        dst.filename = src.filename
        dst.parent = src.parent

    opposite_cmp_op = {
        'in'     : 'not in',
        'not in' : 'in',
        'is'     : 'is not',
        'is not' : 'is',
        }


    def optimize_ast_tree(space, tree):
        return tree.mutate(OptimizerMutator(space))
