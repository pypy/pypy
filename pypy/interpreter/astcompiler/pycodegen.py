import imp
import os
import marshal
import struct
import sys

from pypy.interpreter.astcompiler import ast
from pypy.interpreter.astcompiler import pyassem, misc, future, symbols, opt
from pypy.interpreter.astcompiler.consts import SC_LOCAL, SC_GLOBAL, \
    SC_FREE, SC_CELL, SC_DEFAULT, OP_APPLY, OP_ASSIGN, OP_DELETE, OP_NONE
from pypy.interpreter.astcompiler.consts import CO_VARARGS, CO_VARKEYWORDS, \
    CO_NEWLOCALS, CO_NESTED, CO_GENERATOR, CO_GENERATOR_ALLOWED, \
    CO_FUTURE_DIVISION, CO_FUTURE_WITH_STATEMENT, CO_FUTURE_ABSOLUTE_IMPORT, \
    CO_NOFREE
from pypy.interpreter.pyparser.error import SyntaxError
from pypy.interpreter.astcompiler.opt import is_constant_false
from pypy.interpreter.astcompiler.opt import is_constant_true
from pypy.interpreter.error import OperationError

# drop VERSION dependency since it the ast transformer for 2.4 doesn't work with 2.3 anyway
VERSION = 2

callfunc_opcode_info = [
    # (Have *args, Have **args) : opcode
    "CALL_FUNCTION",
    "CALL_FUNCTION_KW",
    "CALL_FUNCTION_VAR",
    "CALL_FUNCTION_VAR_KW",
]

LOOP = 1
EXCEPT = 2
TRY_FINALLY = 3
END_FINALLY = 4

from pypy.module.__builtin__.__init__ import BUILTIN_TO_INDEX

def compile(source, filename, mode, flags=None, dont_inherit=None):
    """Replacement for builtin compile() function"""
    if flags is not None or dont_inherit is not None:
        raise RuntimeError, "not implemented yet"

    if mode == "single":
        gen = Interactive(source, filename)
    elif mode == "exec":
        gen = Module(source, filename)
    elif mode == "eval":
        gen = Expression(source, filename)
    else:
        raise ValueError("compile() 3rd arg must be 'exec' or "
                         "'eval' or 'single'")
    gen.compile()
    return gen.code

class AbstractCompileMode:
    def __init__(self, source, filename):
        self.source = source
        self.filename = filename
        self.code = None

    def _get_tree(self):
        tree = parse(self.source, self.mode)
        misc.set_filename(self.filename, tree)
        #syntax.check(tree)
        return tree

    def compile(self):
        pass # implemented by subclass

    def getCode(self):
        return self.code

class Expression(AbstractCompileMode):
    mode = "eval"

    def compile(self):
        tree = self._get_tree()
        gen = ExpressionCodeGenerator(tree)
        self.code = gen.getCode()

class Interactive(AbstractCompileMode):
    mode = "single"

    def compile(self):
        tree = self._get_tree()
        gen = InteractiveCodeGenerator(tree)
        self.code = gen.getCode()

class Module(AbstractCompileMode):
    mode = "exec"

    def compile(self, display=0):
        tree = self._get_tree()
        gen = ModuleCodeGenerator(tree)
        if display:
            import pprint
            print pprint.pprint(tree)
        self.code = gen.getCode()

class CodeGenerator(ast.ASTVisitor):
    """Defines basic code generator for Python bytecode
    """

    localsfullyknown = False

    def __init__(self, space, graph):
        self.space = space
        self.setups = [] 
        self.last_lineno = -1
        self._div_op = "BINARY_DIVIDE"
        self.genexpr_cont_stack = []
        self.graph = graph
        self.optimized = 0 # is namespace access optimized?

        # XXX set flags based on future features
        futures = self.get_module().futures
        for feature in futures:
            if feature == "division":
                self.graph.setFlag(CO_FUTURE_DIVISION)
                self._div_op = "BINARY_TRUE_DIVIDE"
            elif feature == "generators":
                self.graph.setFlag(CO_GENERATOR_ALLOWED)
            elif feature == "with_statement":
                self.graph.setFlag(CO_FUTURE_WITH_STATEMENT)
            elif feature == "absolute_import":
                self.graph.setFlag(CO_FUTURE_ABSOLUTE_IMPORT)

    def emit(self, inst ):
        return self.graph.emit( inst )

    def emitop(self, inst, op):
        return self.graph.emitop_name( inst, op )

    def emitop_obj(self, inst, obj):
        return self.graph.emitop_obj( inst, obj )

    def emitop_code(self, inst, gen):
        code = gen.getCode()
        w_code = self.space.wrap(code)
        return self.graph.emitop_obj( inst, w_code )

    def emitop_int(self, inst, op):
        assert isinstance(op, int)
        return self.graph.emitop_int( inst, op )

    def emitop_block(self, inst, block):
        return self.graph.emitop_block( inst, block )

    def nextBlock(self, block ):
        """graph delegation"""
        return self.graph.nextBlock( block )

    def newBlock(self):
        """graph delegation"""
        return self.graph.newBlock()

    def setDocstring(self, doc):
        """graph delegation"""
        return self.graph.setDocstring( doc )
    
    def getCode(self):
        """Return a code object"""
        return self.graph.getCode()

    def mangle(self, name):
        return self.scope.mangle(name)

    def parseSymbols(self, tree):
        s = symbols.SymbolVisitor(self.space)
        tree.accept(s)

    def get_module(self):
        raise NotImplementedError("should be implemented by subclasses")

    # Next five methods handle name access
    def storeName(self, name, lineno):
        if name in ('None', '__debug__'):
            raise SyntaxError('assignment to %s is not allowed' % name, lineno)
        self._nameOp('STORE', name)

    def loadName(self, name, lineno):
        self._nameOp('LOAD', name)

    def delName(self, name, lineno):
        if name in ('None', '__debug__'):
            raise SyntaxError('deleting %s is not allowed' % name, lineno)
        scope = self.scope.check_name(self.mangle(name))
        if scope == SC_CELL:
            raise SyntaxError("cannot delete variable '%s' "
                              "referenced in nested scope" % name, lineno)
        self._nameOp('DELETE', name)

    def _nameOp(self, prefix, name):
        if name == 'None':     # always use LOAD_CONST to load None
            self.emitop_obj('LOAD_CONST', self.space.w_None)
            return
        name = self.mangle(name)
        scope = self.scope.check_name(name)
        if scope == SC_LOCAL:
            if not self.optimized:
                self.emitop(prefix + '_NAME', name)
            else:
                self.emitop(prefix + '_FAST', name)
        elif scope == SC_GLOBAL:
            self.emitop(prefix + '_GLOBAL', name)
        elif scope == SC_FREE or scope == SC_CELL:
            self.emitop(prefix + '_DEREF', name)
        elif scope == SC_DEFAULT:
            if self.optimized and self.localsfullyknown:
                self.emitop(prefix + '_GLOBAL', name)
            else:
                self.emitop(prefix + '_NAME', name)
        else:
            raise pyassem.InternalCompilerError(
                  "unsupported scope for var %s in %s: %d" %
                  (name, self.scope.name, scope))

    def _implicitNameOp(self, prefix, name):
        """Emit name ops for names generated implicitly by for loops

        The interpreter generates names that start with a period or
        dollar sign.  The symbol table ignores these names because
        they aren't present in the program text.
        """
        if self.optimized:
            self.emitop(prefix + '_FAST', name)
        else:
            self.emitop(prefix + '_NAME', name)

    # The set_lineno() function and the explicit emit() calls for
    # SET_LINENO below are only used to generate the line number table.
    # As of Python 2.3, the interpreter does not have a SET_LINENO
    # instruction.  pyassem treats SET_LINENO opcodes as a special case.

    def set_lineno(self, node, force=False):
        """Emit SET_LINENO if necessary.

        The instruction is considered necessary if the node has a
        lineno attribute and it is different than the last lineno
        emitted.

        Returns true if SET_LINENO was emitted.

        There are no rules for when an AST node should have a lineno
        attribute.  The transformer and AST code need to be reviewed
        and a consistent policy implemented and documented.  Until
        then, this method works around missing line numbers.
        """
        if node is None:
            return False
        lineno = node.lineno
        if lineno != -1 and (lineno != self.last_lineno
                             or force):
            self.emitop_int('SET_LINENO', lineno)
            self.last_lineno = lineno
            return True
        return False

    # The first few visitor methods handle nodes that generator new
    # code objects.  They use class attributes to determine what
    # specialized code generators to use.


    def visitModule(self, node):
        space = self.space
        self.parseSymbols(node)
        assert node.scope is not None
        self.scope = node.scope
        if not space.is_w(node.w_doc, space.w_None):
            self.setDocstring(node.w_doc)
            self.set_lineno(node)
            self.emitop_obj('LOAD_CONST', node.w_doc)
            self.storeName('__doc__', node.lineno)
        node.node.accept( self )
        self.emitop_obj('LOAD_CONST', space.w_None )
        self.emit('RETURN_VALUE')

    def visitExpression(self, node):
        self.set_lineno(node)
        self.parseSymbols(node)
        assert node.scope is not None
        self.scope = node.scope
        node.node.accept( self )
        self.emit('RETURN_VALUE')

    def visitFunction(self, node):
        self._visitFuncOrLambda(node, isLambda=0)
        space = self.space
        self.storeName(node.name, node.lineno)

    def visitLambda(self, node):
        self._visitFuncOrLambda(node, isLambda=1)

    def _visitFuncOrLambda(self, node, isLambda=0):
        if not isLambda and node.decorators:
            for decorator in node.decorators.nodes:
                decorator.accept( self )
            ndecorators = len(node.decorators.nodes)
        else:
            ndecorators = 0
        if ndecorators > 0:
            initialnode = node.decorators.nodes[0]
        else:
            initialnode = None

        gen = FunctionCodeGenerator(self.space, node, isLambda,
                                    self.get_module(), initialnode)
        node.code.accept( gen )
        gen.finish(node)
        self.set_lineno(node)
        for default in node.defaults:
            default.accept( self )
        self._makeClosure(gen, len(node.defaults))
        for i in range(ndecorators):
            self.emitop_int('CALL_FUNCTION', 1)

    def _makeClosure(self, gen, args):
        frees = gen.scope.get_free_vars_in_parent()
        if frees:
            for name in frees:
                self.emitop('LOAD_CLOSURE', name)
            self.emitop_int('BUILD_TUPLE', len(frees))
            self.emitop_code('LOAD_CONST', gen)
            self.emitop_int('MAKE_CLOSURE', args)
        else:
            self.emitop_code('LOAD_CONST', gen)
            self.emitop_int('MAKE_FUNCTION', args)

    def visitClass(self, node):
        gen = ClassCodeGenerator(self.space, node,
                                 self.get_module())
        node.code.accept( gen )
        gen.finish(node)
        self.set_lineno(node)
        self.emitop_obj('LOAD_CONST', self.space.wrap(node.name) )
        for base in node.bases:
            base.accept( self )
        self.emitop_int('BUILD_TUPLE', len(node.bases))
        self._makeClosure(gen, 0)
        self.emitop_int('CALL_FUNCTION', 0)
        self.emit('BUILD_CLASS')
        self.storeName(node.name, node.lineno)

    # The rest are standard visitor methods

    # The next few implement control-flow statements

    def visitIf(self, node):
        end = self.newBlock()
        for test, suite in node.tests:
            if is_constant_true(self.space, test):
                # "if 1:"
                suite.accept( self )
                self.nextBlock(end)
                return
            if is_constant_false(self.space, test):
                # "if 0:" XXX will need to check generator stuff here
                continue
            # normal case
            self.set_lineno(test)
            nextTest = self.newBlock()
            test.opt_accept_jump_if(self, False, nextTest)
            self.emit('POP_TOP')
            suite.accept( self )
            self.emitop_block('JUMP_FORWARD', end)
            self.nextBlock(nextTest)
            self.emit('POP_TOP')
        if node.else_:
            node.else_.accept( self )
        self.nextBlock(end)

    def visitWhile(self, node):
        self.set_lineno(node)
        if is_constant_false(self.space, node.test):
            # "while 0:"
            if node.else_:
                node.else_.accept( self )
            return

        loop = self.newBlock()
        else_ = self.newBlock()

        after = self.newBlock()
        self.emitop_block('SETUP_LOOP', after)

        self.nextBlock(loop)
        self.setups.append((LOOP, loop))

        self.set_lineno(node, force=True)
        if is_constant_true(self.space, node.test):
            # "while 1:"
            pass
        else:
            node.test.opt_accept_jump_if(self, False, else_)
            self.emit('POP_TOP')
        node.body.accept( self )
        self.emitop_block('JUMP_ABSOLUTE', loop)

        self.nextBlock(else_) # or just the POPs if not else clause
        self.emit('POP_TOP')
        self.emit('POP_BLOCK')
        self.setups.pop()
        if node.else_:
            node.else_.accept( self )
        self.nextBlock(after)

    def visitFor(self, node):
        start = self.newBlock()
        anchor = self.newBlock()
        after = self.newBlock()
        self.setups.append((LOOP, start))

        self.set_lineno(node)
        self.emitop_block('SETUP_LOOP', after)
        node.list.accept( self )
        self.emit('GET_ITER')

        self.nextBlock(start)
        self.set_lineno(node, force=1)
        self.emitop_block('FOR_ITER', anchor)
        node.assign.accept( self )
        node.body.accept( self )
        self.emitop_block('JUMP_ABSOLUTE', start)
        self.nextBlock(anchor)
        self.emit('POP_BLOCK')
        self.setups.pop()
        if node.else_:
            node.else_.accept( self )
        self.nextBlock(after)

    def visitBreak(self, node):
        # compute setups
        setups = [s for s in self.setups if
                  (s[0] != EXCEPT and s[0] != TRY_FINALLY)]
        if len(setups) == 0:
            raise SyntaxError( "'break' outside loop", node.lineno)
        self.set_lineno(node)
        self.emit('BREAK_LOOP')

    def visitContinue(self, node):
        if len(self.setups) == 0:
            raise SyntaxError( "'continue' not properly in loop", node.lineno)
        kind, block = self.setups[-1]
        if kind == LOOP:
            self.set_lineno(node)
            self.emitop_block('JUMP_ABSOLUTE', block)
        elif kind == EXCEPT or kind == TRY_FINALLY:
            self.set_lineno(node)
            # find the block that starts the loop
            top = len(self.setups)
            loop_block = None
            while top > 0:
                top = top - 1
                kind, loop_block = self.setups[top]
                if kind == LOOP:
                    break
                elif kind == END_FINALLY:
                    msg = "'continue' not supported inside 'finally' clause"
                    raise SyntaxError( msg, node.lineno )
            if kind != LOOP:
                raise SyntaxError( "'continue' not properly in loop", node.lineno)
            self.emitop_block('CONTINUE_LOOP', loop_block)
        elif kind == END_FINALLY:
            msg = "'continue' not supported inside 'finally' clause"
            raise SyntaxError( msg, node.lineno )

    def _visitTest(self, node, jump):
        end = self.newBlock()
        for child in node.nodes[:-1]:
            child.accept( self )
            self.emitop_block(jump, end)
            self.emit('POP_TOP')
        node.nodes[-1].accept( self )
        self.nextBlock(end)

    def visitAnd(self, node):
        self._visitTest(node, 'JUMP_IF_FALSE')

    def visitOr(self, node):
        self._visitTest(node, 'JUMP_IF_TRUE')

    def visitCondExpr(self, node):
        end = self.newBlock()
        falseblock = self.newBlock()

        node.test.opt_accept_jump_if(self, False, falseblock)
        self.emit('POP_TOP')
        node.true_expr.accept(self)
        self.emitop_block('JUMP_FORWARD', end)

        self.nextBlock(falseblock)
        self.emit('POP_TOP')
        node.false_expr.accept(self)

        self.nextBlock(end)

    __with_count = 0

    def visitWith(self, node):
        node.expr.accept(self)
        self.emit('DUP_TOP')

        ## exit = ctx.__exit__
        self.emitop('LOAD_ATTR', '__exit__')
        exit = "$exit%d" % self.__with_count
        var = "$var%d" % self.__with_count
        self.__with_count = self.__with_count + 1
        self._implicitNameOp('STORE', exit)

        self.emitop('LOAD_ATTR', '__enter__')
        self.emitop_int('CALL_FUNCTION', 0)
        finally_block = self.newBlock()
        body = self.newBlock()

        self.setups.append((TRY_FINALLY, body))

        if node.var is not None:        # VAR is present
            self._implicitNameOp('STORE', var)
            self.emitop_block('SETUP_FINALLY', finally_block)
            self.nextBlock(body)
            self._implicitNameOp('LOAD', var)
            self._implicitNameOp('DELETE', var)
            node.var.accept(self) 
        else:
            self.emit('POP_TOP')
            self.emitop_block('SETUP_FINALLY', finally_block)
            self.nextBlock(body)

        node.body.accept(self)
        
        self.emit('POP_BLOCK')
        self.setups.pop()
        self.emitop_obj('LOAD_CONST', self.space.w_None) # WITH_CLEANUP checks for normal exit
        self.nextBlock(finally_block)
        self.setups.append((END_FINALLY, finally_block))

        # find local variable with is context.__exit__
        self._implicitNameOp('LOAD', exit)
        self._implicitNameOp('DELETE', exit)

        self.emit('WITH_CLEANUP')
        self.emit('END_FINALLY')
        self.setups.pop()

    def visitCompare(self, node):
        node.expr.accept( self )
        cleanup = self.newBlock()
        for op, code in node.ops[:-1]:
            code.accept( self )
            self.emit('DUP_TOP')
            self.emit('ROT_THREE')
            self.emitop('COMPARE_OP', op)
            self.emitop_block('JUMP_IF_FALSE', cleanup)
            self.emit('POP_TOP')
        # now do the last comparison
        if node.ops:
            op, code = node.ops[-1]
            code.accept( self )
            self.emitop('COMPARE_OP', op)
        if len(node.ops) > 1:
            end = self.newBlock()
            self.emitop_block('JUMP_FORWARD', end)
            self.nextBlock(cleanup)
            self.emit('ROT_TWO')
            self.emit('POP_TOP')
            self.nextBlock(end)

    # list comprehensions
    __list_count = 0

    def visitListComp(self, node):
        self.set_lineno(node)
        # setup list
        self.__list_count = self.__list_count + 1
        tmpname = "_[%d]" % self.__list_count
        self.emitop_int('BUILD_LIST', 0)
        self.emit('DUP_TOP')
        self._implicitNameOp('STORE', tmpname)

        stack = []
        i = 0
        for for_ in node.quals:
            assert isinstance(for_, ast.ListCompFor)
            start, anchor = self._visitListCompFor(for_)
            self.genexpr_cont_stack.append( None )
            for if_ in for_.ifs:
                if self.genexpr_cont_stack[-1] is None:
                    self.genexpr_cont_stack[-1] = self.newBlock()
                if_.accept( self )
            stack.insert(0, (start, self.genexpr_cont_stack[-1], anchor))
            self.genexpr_cont_stack.pop()
            i += 1

        self._implicitNameOp('LOAD', tmpname)
        node.expr.accept( self )
        self.emit('LIST_APPEND')

        for start, cont, anchor in stack:
            if cont:
                skip_one = self.newBlock()
                self.emitop_block('JUMP_FORWARD', skip_one)
                self.nextBlock(cont)
                self.emit('POP_TOP')
                self.nextBlock(skip_one)
            self.emitop_block('JUMP_ABSOLUTE', start)
            self.nextBlock(anchor)
        self._implicitNameOp('DELETE', tmpname)

        self.__list_count = self.__list_count - 1

    def _visitListCompFor(self, node):
        start = self.newBlock()
        anchor = self.newBlock()

        node.list.accept( self )
        self.emit('GET_ITER')
        self.nextBlock(start)
        self.set_lineno(node, force=True)
        self.emitop_block('FOR_ITER', anchor)
        node.assign.accept( self )
        return start, anchor

    def visitListCompIf(self, node):
        branch = self.genexpr_cont_stack[-1]
        self.set_lineno(node, force=True)
        node.test.opt_accept_jump_if(self, False, branch)
        self.emit('POP_TOP')

    def visitGenExpr(self, node):
        gen = GenExprCodeGenerator(self.space, node, self.get_module())
        inner = node.code
        assert isinstance(inner, ast.GenExprInner)
        inner.accept( gen )
        gen.finish(node)
        self.set_lineno(node)
        self._makeClosure(gen, 0)
        # precomputation of outmost iterable
        qual0 = inner.quals[0]
        assert isinstance(qual0, ast.GenExprFor)
        qual0.iter.accept( self )
        self.emit('GET_ITER')
        self.emitop_int('CALL_FUNCTION', 1)

    def visitGenExprInner(self, node):
        self.set_lineno(node)
        # setup list

        stack = []
        i = 0
        for for_ in node.quals:
            assert isinstance(for_, ast.GenExprFor)
            start, anchor = self._visitGenExprFor(for_)
            self.genexpr_cont_stack.append( None )
            for if_ in for_.ifs:
                if self.genexpr_cont_stack[-1] is None:
                    self.genexpr_cont_stack[-1] = self.newBlock()
                if_.accept( self )
            stack.insert(0, (start, self.genexpr_cont_stack[-1], anchor))
            self.genexpr_cont_stack.pop()
            i += 1

        node.expr.accept( self )
        self.emit('YIELD_VALUE')
        self.emit('POP_TOP')

        for start, cont, anchor in stack:
            if cont:
                skip_one = self.newBlock()
                self.emitop_block('JUMP_FORWARD', skip_one)
                self.nextBlock(cont)
                self.emit('POP_TOP')
                self.nextBlock(skip_one)
            self.emitop_block('JUMP_ABSOLUTE', start)
            self.nextBlock(anchor)
        self.emitop_obj('LOAD_CONST', self.space.w_None)

    def _visitGenExprFor(self, node):
        start = self.newBlock()
        anchor = self.newBlock()

        if node.is_outmost:
            self.loadName('[outmost-iterable]', node.lineno)
        else:
            node.iter.accept( self )
            self.emit('GET_ITER')

        self.nextBlock(start)
        self.set_lineno(node, force=True)
        self.emitop_block('FOR_ITER', anchor)
        node.assign.accept( self )
        return start, anchor

    def visitGenExprIf(self, node ):
        branch = self.genexpr_cont_stack[-1]
        self.set_lineno(node, force=True)
        node.test.opt_accept_jump_if(self, False, branch)
        self.emit('POP_TOP')

    # exception related

    def visitAssert(self, node):
        # XXX would be interesting to implement this via a
        # transformation of the AST before this stage
        if __debug__:
            end = self.newBlock()
            self.set_lineno(node)
            # XXX AssertionError appears to be special case -- it is always
            # loaded as a global even if there is a local name.  I guess this
            # is a sort of renaming op.
            node.test.opt_accept_jump_if(self, True, end)
            self.emit('POP_TOP')
            self.emitop('LOAD_GLOBAL', 'AssertionError')
            if node.fail:
                node.fail.accept( self )
                self.emitop_int('RAISE_VARARGS', 2)
            else:
                self.emitop_int('RAISE_VARARGS', 1)
            self.nextBlock(end)
            self.emit('POP_TOP')

    def visitRaise(self, node):
        self.set_lineno(node)
        n = 0
        if node.expr1:
            node.expr1.accept( self )
            n = n + 1
        if node.expr2:
            node.expr2.accept( self )
            n = n + 1
        if node.expr3:
            node.expr3.accept( self )
            n = n + 1
        self.emitop_int('RAISE_VARARGS', n)

    def visitTryExcept(self, node):
        body = self.newBlock()
        handlers = self.newBlock()
        end = self.newBlock()
        if node.else_:
            lElse = self.newBlock()
        else:
            lElse = end
        self.set_lineno(node)
        self.emitop_block('SETUP_EXCEPT', handlers)
        self.nextBlock(body)
        self.setups.append((EXCEPT, body))
        node.body.accept( self )
        self.emit('POP_BLOCK')
        self.setups.pop()
        self.emitop_block('JUMP_FORWARD', lElse)
        self.nextBlock(handlers)

        last = len(node.handlers) - 1
        for expr, target, body in node.handlers:
            if expr:
                self.set_lineno(expr)
                self.emit('DUP_TOP')
                expr.accept( self )
                self.emitop('COMPARE_OP', 'exception match')
                next = self.newBlock()
                self.emitop_block('JUMP_IF_FALSE', next)
                self.emit('POP_TOP')
            else:
                self.set_lineno(body)
                next = None
            self.emit('POP_TOP')
            if target:
                target.accept( self )
            else:
                self.emit('POP_TOP')
            self.emit('POP_TOP')
            body.accept( self )
            self.emitop_block('JUMP_FORWARD', end)
            if expr: # XXX
                self.nextBlock(next)
                self.emit('POP_TOP')
        self.emit('END_FINALLY')
        if node.else_:
            self.nextBlock(lElse)
            node.else_.accept( self )
        self.nextBlock(end)

    def visitTryFinally(self, node):
        body = self.newBlock()
        final = self.newBlock()
        self.set_lineno(node)
        self.emitop_block('SETUP_FINALLY', final)
        self.nextBlock(body)
        self.setups.append((TRY_FINALLY, body))
        node.body.accept( self )
        self.emit('POP_BLOCK')
        self.setups.pop()
        self.emitop_obj('LOAD_CONST', self.space.w_None)
        self.nextBlock(final)
        self.setups.append((END_FINALLY, final))
        node.final.accept( self )
        self.emit('END_FINALLY')
        self.setups.pop()

    # misc

    def visitDiscard(self, node):
        # Important: this function is overridden in InteractiveCodeGenerator,
        # which also has the effect that the following test only occurs in
        # non-'single' modes.
        if isinstance(node.expr, ast.Const):
            return    # skip LOAD_CONST/POP_TOP pairs (for e.g. docstrings)
        self.set_lineno(node)
        node.expr.accept( self )
        self.emit('POP_TOP')

    def visitConst(self, node):
        space = self.space
        if space.is_true(space.isinstance(node.value, space.w_tuple)):
            self.set_lineno(node)
        self.emitop_obj('LOAD_CONST', node.value)

    def visitKeyword(self, node):
        self.emitop_obj('LOAD_CONST', self.space.wrap(node.name) )
        node.expr.accept( self )

    def visitGlobal(self, node):
        # no code to generate
        pass

    def visitName(self, node):
        self.set_lineno(node)
        self.loadName(node.varname, node.lineno)

    def visitPass(self, node):
        pass  # no self.set_lineno(node) unnecessarily! see test_return_lineno

    def visitImport(self, node):
        self.set_lineno(node)
        if self.graph.checkFlag(CO_FUTURE_ABSOLUTE_IMPORT):
            level = 0
        else:
            level = -1
        for name, alias in node.names:
            self.emitop_obj('LOAD_CONST', self.space.wrap(level)) # 2.5 flag
            self.emitop_obj('LOAD_CONST', self.space.w_None)
            self.emitop('IMPORT_NAME', name)
            mod = name.split(".")[0]
            if alias:
                self._resolveDots(name)
                self.storeName(alias, node.lineno)
            else:
                self.storeName(mod, node.lineno)

    def visitFrom(self, node):
        self.set_lineno(node)
        level = node.level
        if level == 0 and not self.graph.checkFlag(CO_FUTURE_ABSOLUTE_IMPORT):
            level = -1
        fromlist = [ self.space.wrap(name) for name,alias in node.names ]
        self.emitop_obj('LOAD_CONST', self.space.wrap(level)) # 2.5 flag
        self.emitop_obj('LOAD_CONST', self.space.newtuple(fromlist))
        self.emitop('IMPORT_NAME', node.modname)
        for name, alias in node.names:
            if name == '*':
                self.namespace = 0
                self.emit('IMPORT_STAR')
                # There can only be one name w/ from ... import *
                assert len(node.names) == 1
                return
            else:
                self.emitop('IMPORT_FROM', name)
                self._resolveDots(name)
                self.storeName(alias or name, node.lineno)
        self.emit('POP_TOP')

    def _resolveDots(self, name):
        elts = name.split(".")
        if len(elts) == 1:
            return
        for elt in elts[1:]:
            self.emitop('LOAD_ATTR', elt)

    def visitGetattr(self, node):
        node.expr.accept( self )
        self.emitop('LOAD_ATTR', self.mangle(node.attrname))

    # next five implement assignments

    def visitAssign(self, node):
        self.set_lineno(node)
        if opt.OPTIMIZE and self._visitTupleAssignment(node):
            return
        node.expr.accept( self )
        dups = len(node.nodes) - 1
        for i in range(len(node.nodes)):
            elt = node.nodes[i]
            if i < dups:
                self.emit('DUP_TOP')
            assert isinstance(elt, ast.Node)
            elt.accept( self )

    def _visitTupleAssignment(self, parentnode):
        # look for the assignment pattern (...) = (...)
        space = self.space
        expr = parentnode.expr
        if isinstance(expr, ast.Tuple):
            srcnodes = expr.nodes
        elif isinstance(expr, ast.List):
            srcnodes = expr.nodes
        elif isinstance(expr, ast.Const):
            try:
                values_w = space.unpackiterable(expr.value)
            except OperationError:
                return False
            srcnodes = [ast.Const(w) for w in values_w]
        else:
            return False
        if len(parentnode.nodes) != 1:
            return False
        target = parentnode.nodes[0]
        if not isinstance(target, ast.AssSeq):
            return False
        targetnodes = target.nodes
        if len(targetnodes) != len(srcnodes):
            return False
        # we can only optimize two (common) particular cases, because
        # the order of evaluation of the expression *and* the order
        # of assignment should both be kept, in principle.
        # 1. if all targetnodes are simple names, the assignment order
        #    *should* not really matter.
        # 2. otherwise, if the tuple is of length <= 3, we can emit simple
        #    bytecodes to reverse the items in the value stack.
        for node in targetnodes:
            if not isinstance(node, ast.AssName):
                break    # not a simple name
        else:
            # all simple names, case 1.
            for node in srcnodes:
                node.accept(self)
            # let's be careful about the same name appearing several times
            seen = {}
            for i in range(len(targetnodes)-1, -1, -1):
                node = targetnodes[i]
                assert isinstance(node, ast.AssName)
                if node.name not in seen:
                    seen[node.name] = True
                    self.storeName(node.name, node.lineno)
                else:
                    self.emit('POP_TOP')
            return True  # done

        n = len(srcnodes)
        if n > 3:
            return False    # can't do it
        else:
            # case 2.
            for node in srcnodes:
                node.accept(self)
            if n == 2:
                self.emit('ROT_TWO')
            elif n == 3:
                self.emit('ROT_THREE')
                self.emit('ROT_TWO')
            for node in targetnodes:
                node.accept(self)
            return True     # done

    def visitAssName(self, node):
        if node.flags == OP_ASSIGN:
            self.storeName(node.name, node.lineno)
        elif node.flags == OP_DELETE:
            self.set_lineno(node)
            self.delName(node.name, node.lineno)
        else:
            assert False, "visitAssName unexpected flags: %d" % node.flags

    def visitAssAttr(self, node):
        node.expr.accept( self )
        if node.flags == OP_ASSIGN:
            if node.attrname  == 'None':
                raise SyntaxError('assignment to None is not allowed', node.lineno)
            self.emitop('STORE_ATTR', self.mangle(node.attrname))
        elif node.flags == OP_DELETE:
            if node.attrname == 'None':
                raise SyntaxError('deleting None is not allowed', node.lineno)
            self.emitop('DELETE_ATTR', self.mangle(node.attrname))
        else:
            assert False, "visitAssAttr unexpected flags: %d" % node.flags

    def _visitAssSequence(self, node, op='UNPACK_SEQUENCE'):
        if not node.nodes:
            raise SyntaxError('Cannot assign to empty sequence',
                              node.lineno)
        if findOp(node) != OP_DELETE:
            self.emitop_int(op, len(node.nodes))
        for child in node.nodes:
            child.accept( self )

    visitAssTuple = _visitAssSequence
    visitAssList = _visitAssSequence

    # augmented assignment

    def visitAugAssign(self, node):
        self.set_lineno(node)
        node.node.accept( AugLoadVisitor(self) )
        node.expr.accept( self )
        self.emit(self._augmented_opcode[node.op])
        node.node.accept( AugStoreVisitor(self) )

    _augmented_opcode = {
        '+=' : 'INPLACE_ADD',
        '-=' : 'INPLACE_SUBTRACT',
        '*=' : 'INPLACE_MULTIPLY',
        '/=' : 'INPLACE_DIVIDE',
        '//=': 'INPLACE_FLOOR_DIVIDE',
        '%=' : 'INPLACE_MODULO',
        '**=': 'INPLACE_POWER',
        '>>=': 'INPLACE_RSHIFT',
        '<<=': 'INPLACE_LSHIFT',
        '&=' : 'INPLACE_AND',
        '^=' : 'INPLACE_XOR',
        '|=' : 'INPLACE_OR',
        }

    def visitExec(self, node):
        node.expr.accept( self )
        if node.locals is None:
            self.emitop_obj('LOAD_CONST', self.space.w_None)
        else:
            node.locals.accept( self )
        if node.globals is None:
            self.emit('DUP_TOP')
        else:
            node.globals.accept( self )
        self.emit('EXEC_STMT')

    def visitCallFunc(self, node):
        self.set_lineno(node)
        if self.emit_builtin_call(node):
            return
        if self.emit_method_call(node):
            return
        pos = 0
        kw = 0
        node.node.accept( self )
        for arg in node.args:
            arg.accept( self )
            if isinstance(arg, ast.Keyword):
                kw = kw + 1
            else:
                pos = pos + 1
        if node.star_args is not None:
            node.star_args.accept( self )
        if node.dstar_args is not None:
            node.dstar_args.accept( self )
        have_star = node.star_args is not None
        have_dstar = node.dstar_args is not None
        opcode = callfunc_opcode_info[ have_star*2 + have_dstar]
        self.emitop_int(opcode, kw << 8 | pos)

    def check_simple_call_args(self, node):
        if node.star_args is not None or node.dstar_args is not None:
            return False
        # check for kw args
        for arg in node.args:
            if isinstance(arg, ast.Keyword):
                return False
        return True

    def emit_builtin_call(self, node):
        if not self.space.config.objspace.opcodes.CALL_LIKELY_BUILTIN:
            return False
        if not self.check_simple_call_args(node):
            return False
        func = node.node
        if not isinstance(func, ast.Name):
            return False
        
        name = func.varname
        scope = self.scope.check_name(name)
        # YYY
        index = BUILTIN_TO_INDEX.get(name, -1)
        if ((scope == SC_GLOBAL or
            (scope == SC_DEFAULT and self.optimized and self.localsfullyknown)) 
            and index != -1):
            for arg in node.args:
                arg.accept(self)
            self.emitop_int("CALL_LIKELY_BUILTIN", index << 8 | len(node.args))
            return True
        return False

    def emit_method_call(self, node):
        if not self.space.config.objspace.opcodes.CALL_METHOD:
            return False
        meth = node.node
        if not isinstance(meth, ast.Getattr):
            return False
        if not self.check_simple_call_args(node):
            return False
        meth.expr.accept(self)
        self.emitop('LOOKUP_METHOD', self.mangle(meth.attrname))
        for arg in node.args:
            arg.accept(self)
        self.emitop_int('CALL_METHOD', len(node.args))
        return True

    def visitPrint(self, node):
        self.set_lineno(node)
        if node.dest:
            node.dest.accept( self )
        for child in node.nodes:
            if node.dest:
                self.emit('DUP_TOP')
            child.accept( self )
            if node.dest:
                self.emit('ROT_TWO')
                self.emit('PRINT_ITEM_TO')
            else:
                self.emit('PRINT_ITEM')
        if node.dest:
            self.emit('POP_TOP')

    def visitPrintnl(self, node):
        self.set_lineno(node)
        if node.dest:
            node.dest.accept( self )
        for child in node.nodes:
            if node.dest:
                self.emit('DUP_TOP')
            child.accept( self )
            if node.dest:
                self.emit('ROT_TWO')
                self.emit('PRINT_ITEM_TO')
            else:
                self.emit('PRINT_ITEM')
        if node.dest:
            self.emit('PRINT_NEWLINE_TO')
        else:
            self.emit('PRINT_NEWLINE')

    def visitReturn(self, node):
        self.set_lineno(node)
        if node.value is None:
            self.emitop_obj('LOAD_CONST', self.space.w_None)
        else:
            node.value.accept( self )
        self.emit('RETURN_VALUE')

    def visitYield(self, node):
        self.set_lineno(node)
        node.value.accept( self )
        self.emit('YIELD_VALUE')

    # slice and subscript stuff
    def visitSlice(self, node):
        return self._visitSlice(node, False)

    def _visitSlice(self, node, aug_flag):
        # aug_flag is used by visitAugSlice
        node.expr.accept( self )
        slice = 0
        if node.lower:
            node.lower.accept( self )
            slice = slice | 1
        if node.upper:
            node.upper.accept( self )
            slice = slice | 2
        if aug_flag:
            if slice == 0:
                self.emit('DUP_TOP')
            elif slice == 3:
                self.emitop_int('DUP_TOPX', 3)
            else:
                self.emitop_int('DUP_TOPX', 2)
        if node.flags == OP_APPLY:
            self.emit('SLICE+%d' % slice)
        elif node.flags == OP_ASSIGN:
            self.emit('STORE_SLICE+%d' % slice)
        elif node.flags == OP_DELETE:
            self.emit('DELETE_SLICE+%d' % slice)
        else:
            assert False, "weird slice %d" % node.flags

    def visitSubscript(self, node):
        return self._visitSubscript(node, False)

    def _visitSubscript(self, node, aug_flag):
        node.expr.accept( self )
        node.sub.accept( self )
        if aug_flag:
            self.emitop_int('DUP_TOPX', 2)
        if node.flags == OP_APPLY:
            self.emit('BINARY_SUBSCR')
        elif node.flags == OP_ASSIGN:
            self.emit('STORE_SUBSCR')
        elif node.flags == OP_DELETE:
            self.emit('DELETE_SUBSCR')

    # binary ops

    def binaryOp(self, node, op):
        node.left.accept( self )
        node.right.accept( self )
        self.emit(op)

    def visitAdd(self, node):
        return self.binaryOp(node, 'BINARY_ADD')

    def visitSub(self, node):
        return self.binaryOp(node, 'BINARY_SUBTRACT')

    def visitMul(self, node):
        return self.binaryOp(node, 'BINARY_MULTIPLY')

    def visitDiv(self, node):
        return self.binaryOp(node, self._div_op)

    def visitFloorDiv(self, node):
        return self.binaryOp(node, 'BINARY_FLOOR_DIVIDE')

    def visitMod(self, node):
        return self.binaryOp(node, 'BINARY_MODULO')

    def visitPower(self, node):
        return self.binaryOp(node, 'BINARY_POWER')

    def visitLeftShift(self, node):
        return self.binaryOp(node, 'BINARY_LSHIFT')

    def visitRightShift(self, node):
        return self.binaryOp(node, 'BINARY_RSHIFT')

    # unary ops

    def unaryOp(self, node, op):
        node.expr.accept( self )
        self.emit(op)

    def visitInvert(self, node):
        return self.unaryOp(node, 'UNARY_INVERT')

    def visitUnarySub(self, node):
        return self.unaryOp(node, 'UNARY_NEGATIVE')

    def visitUnaryAdd(self, node):
        return self.unaryOp(node, 'UNARY_POSITIVE')

    def visitUnaryInvert(self, node):
        return self.unaryOp(node, 'UNARY_INVERT')

    def visitNot(self, node):
        return self.unaryOp(node, 'UNARY_NOT')

    def visitBackquote(self, node):
        return self.unaryOp(node, 'UNARY_CONVERT')

    # bit ops

    def bitOp(self, nodes, op):
        nodes[0].accept( self )
        for node in nodes[1:]:
            node.accept( self )
            self.emit(op)

    def visitBitand(self, node):
        return self.bitOp(node.nodes, 'BINARY_AND')

    def visitBitor(self, node):
        return self.bitOp(node.nodes, 'BINARY_OR')

    def visitBitxor(self, node):
        return self.bitOp(node.nodes, 'BINARY_XOR')

    # object constructors

    def visitEllipsis(self, node):
        return self.emitop_obj('LOAD_CONST', self.space.w_Ellipsis)

    def visitTuple(self, node):
        self.set_lineno(node)
        for elt in node.nodes:
            elt.accept( self )
        self.emitop_int('BUILD_TUPLE', len(node.nodes))

    def visitList(self, node):
        self.set_lineno(node)
        for elt in node.nodes:
            elt.accept( self )
        self.emitop_int('BUILD_LIST', len(node.nodes))

    def visitSliceobj(self, node):
        for child in node.nodes:
            child.accept( self )
        self.emitop_int('BUILD_SLICE', len(node.nodes))

    def visitDict(self, node):
        self.set_lineno(node)
        self.emitop_int('BUILD_MAP', 0)
        for k, v in node.items:
            self.emit('DUP_TOP')
            k.accept( self )
            v.accept( self )
            self.emit('ROT_THREE')
            self.emit('STORE_SUBSCR')


class ModuleCodeGenerator(CodeGenerator):

    def __init__(self, space, tree, futures = []):
        graph = pyassem.PyFlowGraph(space, "<module>", tree.filename)
        self.futures = future.find_futures(tree)
        for f in futures:
            if f not in self.futures:
                self.futures.append(f)
        CodeGenerator.__init__(self, space, graph)
        tree.accept(self) # yuck

    def get_module(self):
        return self

class ExpressionCodeGenerator(CodeGenerator):

    def __init__(self, space, tree, futures=[]):
        graph = pyassem.PyFlowGraph(space, "<expression>", tree.filename)
        self.futures = futures[:]
        CodeGenerator.__init__(self, space, graph)
        tree.accept(self) # yuck

    def get_module(self):
        return self

class InteractiveCodeGenerator(CodeGenerator):

    def __init__(self, space, tree, futures=[]):
        graph = pyassem.PyFlowGraph(space, "<interactive>", tree.filename)
        self.futures = future.find_futures(tree)
        for f in futures:
            if f not in self.futures:
                self.futures.append(f)
        CodeGenerator.__init__(self, space, graph)
        self.set_lineno(tree)
        tree.accept(self) # yuck
        self.emit('RETURN_VALUE')

    def get_module(self):
        return self

    def visitDiscard(self, node):
        # XXX Discard means it's an expression.  Perhaps this is a bad
        # name.
        node.expr.accept( self )
        self.emit('PRINT_EXPR')
        
class AbstractFunctionCode(CodeGenerator):
    def __init__(self, space, scope, func, isLambda, mod, initialnode=None):
        assert scope is not None
        self.scope = scope
        self.localsfullyknown = self.scope.locals_fully_known() and \
            not self.scope.has_exec
        self.module = mod
        if isLambda:
            name = "<lambda>"
        else:
            assert isinstance(func, ast.Function)
            name = func.name
        # Find duplicated arguments.
        argnames = {}
        for arg in func.argnames:
            if isinstance(arg, ast.AssName):
                argname = self.mangle(arg.name)
                if argname in argnames:
                    raise SyntaxError("duplicate argument '%s' in function definition" % argname, func.lineno)
                argnames[argname] = 1
            elif isinstance(arg, ast.AssTuple):
                for argname in arg.getArgNames():
                    argname = self.mangle(argname)
                    if argname in argnames:
                        raise SyntaxError("duplicate argument '%s' in function definition" % argname, func.lineno)
                    argnames[argname] = 1
        if 'None' in argnames:
            raise SyntaxError('assignment to None is not allowed', func.lineno)

        argnames = []
        for i in range(len(func.argnames)):
            var = func.argnames[i]
            if isinstance(var, ast.AssName):
                argnames.append(self.mangle(var.name))
            elif isinstance(var, ast.AssTuple):
                argnames.append('.%d' % (2 * i))
                # (2 * i) just because CPython does that too
        graph = pyassem.PyFlowGraph(space, name, func.filename, argnames,
                                    optimized=self.localsfullyknown,
                                    newlocals=1)
        self.isLambda = isLambda
        CodeGenerator.__init__(self, space, graph)
        self.optimized = 1

        self.graph.setFreeVars(self.scope.get_free_vars_in_scope())
        self.graph.setCellVars(self.scope.get_cell_vars())

        if not isLambda:
            self.setDocstring(func.w_doc)

        if func.varargs:
            self.graph.setFlag(CO_VARARGS)
        if func.kwargs:
            self.graph.setFlag(CO_VARKEYWORDS)
        if not graph.freevars and not graph.cellvars:
            self.graph.setFlag(CO_NOFREE)
        self.set_lineno(initialnode or func)
        self.generateArgUnpack(func.argnames)

    def get_module(self):
        return self.module

    def finish(self, node=None):
        if node:
            self.set_lineno(node.flatten()[-1])
        if not self.isLambda:
            self.emitop_obj('LOAD_CONST', self.space.w_None)
        self.emit('RETURN_VALUE')

    def generateArgUnpack(self, args):
        for i in range(len(args)):
            arg = args[i]
            if isinstance(arg, ast.AssTuple):
                self.emitop('LOAD_FAST', '.%d' % (i * 2))
                self.unpackSequence(arg)

    def unpackSequence(self, tup):
        if VERSION > 1:
            self.emitop_int('UNPACK_SEQUENCE', len(tup.nodes))
        else:
            self.emitop_int('UNPACK_TUPLE', len(tup.nodes))
        
        for elt in tup.nodes:
            if isinstance(elt, ast.AssName):
                self.storeName(elt.name, elt.lineno)
            elif isinstance(elt, ast.AssTuple):
                self.unpackSequence( elt )
            else:
                #raise TypeError( "Got argument %s of type %s" % (elt,type(elt)))
                raise TypeError( "Got unexpected argument" )

    unpackTuple = unpackSequence

class FunctionCodeGenerator(AbstractFunctionCode):

    def __init__(self, space, func, isLambda, mod, initialnode=None):
        AbstractFunctionCode.__init__(self, space, func.scope,
                                      func, isLambda, mod, initialnode)
        if self.scope.generator:
            self.graph.setFlag(CO_GENERATOR)
            if self.scope.return_with_arg is not None:
                node = self.scope.return_with_arg
                raise SyntaxError("'return' with argument inside generator",
                                  node.lineno)
        if (self.scope.parent and
            isinstance(self.scope.parent, symbols.FunctionScope)):
            self.graph.setFlag(CO_NESTED)

class GenExprCodeGenerator(AbstractFunctionCode):

    def __init__(self, space, gexp, mod):
        AbstractFunctionCode.__init__(self, space, gexp.scope, gexp, 1, mod)
        self.graph.setFlag(CO_GENERATOR)

class AbstractClassCode(CodeGenerator):

    def __init__(self, space, klass, module):
        self.module = module
        graph = pyassem.PyFlowGraph( space, klass.name, klass.filename,
                                           optimized=0, klass=1)

        CodeGenerator.__init__(self, space, graph)
        self.graph.setFlag(CO_NEWLOCALS)
        self.setDocstring(klass.w_doc)

    def get_module(self):
        return self.module

    def finish(self, node=None):
        self.emit('LOAD_LOCALS')
        self.emit('RETURN_VALUE')

class ClassCodeGenerator(AbstractClassCode):

    def __init__(self, space, klass, module):
        assert klass.scope is not None
        self.scope = klass.scope
        AbstractClassCode.__init__(self, space, klass, module)
        self.graph.setFreeVars(self.scope.get_free_vars_in_scope())
        self.graph.setCellVars(self.scope.get_cell_vars())
        self.set_lineno(klass)
        self.emitop("LOAD_GLOBAL", "__name__")
        self.storeName("__module__", klass.lineno)
        if not space.is_w(klass.w_doc, space.w_None):
            self.emitop_obj("LOAD_CONST", klass.w_doc)
            self.storeName('__doc__', klass.lineno)

def findOp(node):
    """Find the op (DELETE, LOAD, STORE) in an AssTuple tree"""
    v = OpFinder()
    node.accept(v)
    return v.op

class OpFinder(ast.ASTVisitor):
    def __init__(self):
        self.op = OP_NONE

    def visitAssName(self, node):
        if self.op is OP_NONE:
            self.op = node.flags
        elif self.op != node.flags:
            raise ValueError("mixed ops in stmt")
    def visitAssAttr(self, node):
        if self.op is OP_NONE:
            self.op = node.flags
        elif self.op != node.flags:
            raise ValueError("mixed ops in stmt")
    def visitSubscript(self, node):
        if self.op is OP_NONE:
            self.op = node.flags
        elif self.op != node.flags:
            raise ValueError("mixed ops in stmt")


class AugLoadVisitor(ast.ASTVisitor):
    def __init__(self, main_visitor):
        self.main = main_visitor

    def default(self, node):
        raise SyntaxError("illegal expression for augmented assignment",
                          node.lineno)

    def visitName(self, node ):
        self.main.loadName(node.varname, node.lineno)

    def visitGetattr(self, node):
        node.expr.accept( self.main )
        self.main.emit('DUP_TOP')
        self.main.emitop('LOAD_ATTR', self.main.mangle(node.attrname))

    def visitSlice(self, node):
        self.main._visitSlice(node, True)

    def visitSubscript(self, node):
        self.main._visitSubscript(node, True)

    def visitYield(self, node):
        raise SyntaxError("augmented assignment to yield expression not possible",
                          node.lineno)

class AugStoreVisitor(ast.ASTVisitor):
    def __init__(self, main_visitor):
        self.main = main_visitor
        
    def default(self, node):
        raise pyassem.InternalCompilerError("shouldn't arrive here!")
    
    def visitName(self, node):
        self.main.storeName(node.varname, node.lineno)

    def visitGetattr(self, node):
        self.main.emit('ROT_TWO')
        self.main.emitop('STORE_ATTR', self.main.mangle(node.attrname))

    def visitSlice(self, node):
        slice = 0
        if node.lower:
            slice = slice | 1
        if node.upper:
            slice = slice | 2
        if slice == 0:
            self.main.emit('ROT_TWO')
        elif slice == 3:
            self.main.emit('ROT_FOUR')
        else:
            self.main.emit('ROT_THREE')
        self.main.emit('STORE_SLICE+%d' % slice)

    def visitSubscript(self, node):
        self.main.emit('ROT_THREE')
        self.main.emit('STORE_SUBSCR')
