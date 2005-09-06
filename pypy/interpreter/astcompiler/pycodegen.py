import imp
import os
import marshal
import struct
import sys
import types
from cStringIO import StringIO

from pypy.interpreter.astcompiler import ast, parse, walk, syntax
from pypy.interpreter.astcompiler import pyassem, misc, future, symbols
from pypy.interpreter.astcompiler.consts import SC_LOCAL, SC_GLOBAL, \
    SC_FREE, SC_CELL, SC_REALLY_GLOBAL
from pypy.interpreter.astcompiler.consts import CO_VARARGS, CO_VARKEYWORDS, \
    CO_NEWLOCALS, CO_NESTED, CO_GENERATOR, CO_GENERATOR_ALLOWED, CO_FUTURE_DIVISION
from pypy.interpreter.astcompiler.pyassem import TupleArg
from pypy.interpreter.pyparser.error import SyntaxError

# drop VERSION dependency since it the ast transformer for 2.4 doesn't work with 2.3 anyway
VERSION = 2

callfunc_opcode_info = {
    # (Have *args, Have **args) : opcode
    (0,0) : "CALL_FUNCTION",
    (1,0) : "CALL_FUNCTION_VAR",
    (0,1) : "CALL_FUNCTION_KW",
    (1,1) : "CALL_FUNCTION_VAR_KW",
}

LOOP = 1
EXCEPT = 2
TRY_FINALLY = 3
END_FINALLY = 4

def compileFile(filename, display=0):
    f = open(filename, 'U')
    buf = f.read()
    f.close()
    mod = Module(buf, filename)
    try:
        mod.compile(display)
    except SyntaxError:
        raise
    else:
        f = open(filename + "c", "wb")
        mod.dump(f)
        f.close()

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

    mode = None # defined by subclass

    def __init__(self, source, filename):
        self.source = source
        self.filename = filename
        self.code = None

    def _get_tree(self):
        tree = parse(self.source, self.mode)
        misc.set_filename(self.filename, tree)
        syntax.check(tree)
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

    def dump(self, f):
        f.write(self.getPycHeader())
        marshal.dump(self.code, f)

    MAGIC = imp.get_magic()

    def getPycHeader(self):
        # compile.c uses marshal to write a long directly, with
        # calling the interface that would also generate a 1-byte code
        # to indicate the type of the value.  simplest way to get the
        # same effect is to call marshal and then skip the code.
        mtime = os.path.getmtime(self.filename)
        mtime = struct.pack('<i', mtime)
        return self.MAGIC + mtime

class LocalNameFinder(ast.ASTVisitor):
    """Find local names in scope"""
    def __init__(self, names=()):
        self.names = misc.Set()
        self.globals = misc.Set()
        for name in names:
            self.names.add(name)

    # XXX list comprehensions and for loops

    def getLocals(self):
        for elt in self.globals.elements():
            if self.names.has_elt(elt):
                self.names.remove(elt)
        return self.names

    def visitDict(self, node):
        pass

    def visitGlobal(self, node):
        for name in node.names:
            self.globals.add(name)

    def visitFunction(self, node):
        self.names.add(node.name)

    def visitLambda(self, node):
        pass

    def visitImport(self, node):
        for name, alias in node.names:
            self.names.add(alias or name)

    def visitFrom(self, node):
        for name, alias in node.names:
            self.names.add(alias or name)

    def visitClass(self, node):
        self.names.add(node.name)

    def visitAssName(self, node):
        self.names.add(node.name)

def is_constant_false(node):
    if isinstance(node, ast.Const):
        if not node.value:
            return 1
    return 0

class CodeGenerator(ast.ASTVisitor):
    """Defines basic code generator for Python bytecode

    This class is an abstract base class.  Concrete subclasses must
    define an __init__() that defines self.graph and then calls the
    __init__() defined in this class.
    """

    optimized = 0 # is namespace access optimized?
    __initialized = None
    class_name = None # provide default for instance variable

    def __init__(self, space):
        self.space = space
        self.checkClass()
        self.locals = misc.Stack()
        self.setups = misc.Stack()
        self.last_lineno = -1
        self._div_op = "BINARY_DIVIDE"
        self.genexpr_cont_stack = []

        # XXX set flags based on future features
        futures = self.get_module().futures
        for feature in futures:
            if feature == "division":
                self.graph.setFlag(CO_FUTURE_DIVISION)
                self._div_op = "BINARY_TRUE_DIVIDE"
            elif feature == "generators":
                self.graph.setFlag(CO_GENERATOR_ALLOWED)

    def checkClass(self):
        """Verify that class is constructed correctly"""
        try:
            assert hasattr(self, 'graph')
        except AssertionError, msg:
            intro = "Bad class construction for %s" % self.__class__.__name__
            raise AssertionError, intro


    def emit(self, inst ):
        return self.graph.emit( inst )

    def emitop(self, inst, op):
        return self.graph.emitop_name( inst, op )

    def emitop_obj(self, inst, obj):
        return self.graph.emitop_obj( inst, obj )

    def emitop_int(self, inst, op):
        assert type(op) == int
        return self.graph.emitop_int( inst, op )

    def emitop_block(self, inst, block):
        return self.graph.emitop_block( inst, block )

    def nextBlock(self, block=None ):
        """graph delegation"""
        return self.graph.nextBlock( block )

    def startBlock(self, block ):
        """graph delegation"""
        return self.graph.startBlock( block )

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
        if self.class_name is not None:
            return misc.mangle(name, self.class_name)
        else:
            return name

    def parseSymbols(self, tree):
        s = symbols.SymbolVisitor()
        walk(tree, s)
        return s.scopes

    def get_module(self):
        raise RuntimeError, "should be implemented by subclasses"

    # Next five methods handle name access

    def isLocalName(self, name):
        return self.locals.top().has_elt(name)

    def storeName(self, name):
        self._nameOp('STORE', name)

    def loadName(self, name):
        self._nameOp('LOAD', name)

    def delName(self, name):
        self._nameOp('DELETE', name)

    def _nameOp(self, prefix, name):
        name = self.mangle(name)
        scope = self.scope.check_name(name)
        if scope == SC_LOCAL:
            if not self.optimized:
                self.emitop(prefix + '_NAME', name)
            else:
                self.emitop(prefix + '_FAST', name)
        elif scope == SC_GLOBAL:
            if not self.optimized:
                self.emitop(prefix + '_NAME', name)
            else:
                self.emitop(prefix + '_GLOBAL', name)
        elif scope == SC_FREE or scope == SC_CELL:
            self.emitop(prefix + '_DEREF', name)
        elif scope == SC_REALLY_GLOBAL:
            self.emitop(prefix +  '_GLOBAL', name)
        else:
            raise RuntimeError, "unsupported scope for var %s: %d" % \
                  (name, scope)

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
        self.scopes = self.parseSymbols(node)
        self.scope = self.scopes[node]
        self.emitop_int('SET_LINENO', 0)
        if node.doc:
            self.emitop_obj('LOAD_CONST', node.doc)
            self.storeName('__doc__')
        lnf = LocalNameFinder()
        node.node.accept(lnf)
        self.locals.push(lnf.getLocals())
        node.node.accept( self )
        self.emitop_obj('LOAD_CONST', self.space.w_None )
        self.emit('RETURN_VALUE')

    def visitExpression(self, node):
        self.set_lineno(node)
        self.scopes = self.parseSymbols(node)
        self.scope = self.scopes[node]
        node.node.accept( self )
        self.emit('RETURN_VALUE')

    def visitFunction(self, node):
        self._visitFuncOrLambda(node, isLambda=0)
        if node.doc:
            self.setDocstring(node.doc)
        self.storeName(node.name)

    def visitLambda(self, node):
        self._visitFuncOrLambda(node, isLambda=1)

    def _visitFuncOrLambda(self, node, isLambda=0):
        if not isLambda and node.decorators:
            for decorator in node.decorators.nodes:
                decorator.accept( self )
            ndecorators = len(node.decorators.nodes)
        else:
            ndecorators = 0

        gen = FunctionCodeGenerator(self.space, node, self.scopes, isLambda,
                               self.class_name, self.get_module())
        walk(node.code, gen)
        gen.finish()
        self.set_lineno(node)
        for default in node.defaults:
            default.accept( self )
        frees = gen.scope.get_free_vars()
        if frees:
            for name in frees:
                self.emitop('LOAD_CLOSURE', name)
            self.emitop_obj('LOAD_CONST', gen)
            # self.emitop_obj('LOAD_CONST', gen.getCode())
            self.emitop_int('MAKE_CLOSURE', len(node.defaults))
        else:
            self.emitop_obj('LOAD_CONST', gen)
            # self.emitop_obj('LOAD_CONST', gen.getCode())
            self.emitop_int('MAKE_FUNCTION', len(node.defaults))

        for i in range(ndecorators):
            self.emitop_int('CALL_FUNCTION', 1)

    def visitClass(self, node):
        gen = ClassCodeGenerator(self.space, node, self.scopes,
                                 self.get_module())
        walk(node.code, gen)
        gen.finish()
        self.set_lineno(node)
        self.emitop_obj('LOAD_CONST', self.space.wrap(node.name) )
        for base in node.bases:
            base.accept( self )
        self.emitop_int('BUILD_TUPLE', len(node.bases))
        frees = gen.scope.get_free_vars()
        for name in frees:
            self.emitop('LOAD_CLOSURE', name)
        self.emitop_obj('LOAD_CONST', gen)
        # self.emitop_obj('LOAD_CONST', gen.getCode())
        if frees:
            self.emitop_int('MAKE_CLOSURE', 0)
        else:
            self.emitop_int('MAKE_FUNCTION', 0)
        self.emitop_int('CALL_FUNCTION', 0)
        self.emit('BUILD_CLASS')
        self.storeName(node.name)

    # The rest are standard visitor methods

    # The next few implement control-flow statements

    def visitIf(self, node):
        end = self.newBlock()
        for test, suite in node.tests:
            if is_constant_false(test):
                # XXX will need to check generator stuff here
                continue
            self.set_lineno(test)
            test.accept( self )
            nextTest = self.newBlock()
            self.emitop_block('JUMP_IF_FALSE', nextTest)
            self.nextBlock()
            self.emit('POP_TOP')
            suite.accept( self )
            self.emitop_block('JUMP_FORWARD', end)
            self.startBlock(nextTest)
            self.emit('POP_TOP')
        if node.else_:
            node.else_.accept( self )
        self.nextBlock(end)

    def visitWhile(self, node):
        self.set_lineno(node)

        loop = self.newBlock()
        else_ = self.newBlock()

        after = self.newBlock()
        self.emitop_block('SETUP_LOOP', after)

        self.nextBlock(loop)
        self.setups.push((LOOP, loop))

        self.set_lineno(node, force=True)
        node.test.accept( self )
        self.emitop_block('JUMP_IF_FALSE', else_ or after)

        self.nextBlock()
        self.emit('POP_TOP')
        node.body.accept( self )
        self.emitop_block('JUMP_ABSOLUTE', loop)

        self.startBlock(else_) # or just the POPs if not else clause
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
        self.setups.push((LOOP, start))

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
        if not self.setups:
            raise SyntaxError( "'break' outside loop (%s, %d)" %
                               (node.filename, node.lineno) )
        self.set_lineno(node)
        self.emit('BREAK_LOOP')

    def visitContinue(self, node):
        if not self.setups:
            raise SyntaxError( "'continue' not properly in loop"
                               # (%s, %d)" % (node.filename, node.lineno)
                               )
        kind, block = self.setups.top()
        if kind == LOOP:
            self.set_lineno(node)
            self.emitop_block('JUMP_ABSOLUTE', block)
            self.nextBlock()
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
            if kind != LOOP:
                raise SyntaxError( "'continue' not properly in loop"
                                   # (%s, %d)" % (node.filename, node.lineno)
                                   )
            self.emitop_block('CONTINUE_LOOP', loop_block)
            self.nextBlock()
        elif kind == END_FINALLY:
            msg = "'continue' not supported inside 'finally' clause" # " (%s, %d)"
            raise SyntaxError( msg ) # % (node.filename, node.lineno)

    def _visitTest(self, node, jump):
        end = self.newBlock()
        for child in node.nodes[:-1]:
            child.accept( self )
            self.emitop_block(jump, end)
            self.nextBlock()
            self.emit('POP_TOP')
        node.nodes[-1].accept( self )
        self.nextBlock(end)

    def visitAnd(self, node):
        self._visitTest(node, 'JUMP_IF_FALSE')

    def visitOr(self, node):
        self._visitTest(node, 'JUMP_IF_TRUE')

    def visitCompare(self, node):
        node.expr.accept( self )
        cleanup = self.newBlock()
        for op, code in node.ops[:-1]:
            code.accept( self )
            self.emit('DUP_TOP')
            self.emit('ROT_THREE')
            self.emitop('COMPARE_OP', op)
            self.emitop_block('JUMP_IF_FALSE', cleanup)
            self.nextBlock()
            self.emit('POP_TOP')
        # now do the last comparison
        if node.ops:
            op, code = node.ops[-1]
            code.accept( self )
            self.emitop('COMPARE_OP', op)
        if len(node.ops) > 1:
            end = self.newBlock()
            self.emitop_block('JUMP_FORWARD', end)
            self.startBlock(cleanup)
            self.emit('ROT_TWO')
            self.emit('POP_TOP')
            self.nextBlock(end)

    # list comprehensions
    __list_count = 0

    def visitListComp(self, node):
        self.set_lineno(node)
        # setup list
        append = "$append%d" % self.__list_count
        self.__list_count = self.__list_count + 1
        self.emitop_int('BUILD_LIST', 0)
        self.emit('DUP_TOP')
        self.emitop('LOAD_ATTR', 'append')
        self._implicitNameOp('STORE', append)


        stack = []
        for i, for_ in zip(range(len(node.quals)), node.quals):
            start, anchor = for_.accept( self )
            self.genexpr_cont_stack.append( None )
            for if_ in for_.ifs:
                if self.genexpr_cont_stack[-1] is None:
                    self.genexpr_cont_stack[-1] = self.newBlock()
                if_.accept( self )
            stack.insert(0, (start, self.genexpr_cont_stack[-1], anchor))
            self.genexpr_cont_stack.pop()

        self._implicitNameOp('LOAD', append)
        node.expr.accept( self )
        self.emitop_int('CALL_FUNCTION', 1)
        self.emit('POP_TOP')

        for start, cont, anchor in stack:
            if cont:
                skip_one = self.newBlock()
                self.emitop_block('JUMP_FORWARD', skip_one)
                self.startBlock(cont)
                self.emit('POP_TOP')
                self.nextBlock(skip_one)
            self.emitop_block('JUMP_ABSOLUTE', start)
            self.startBlock(anchor)
        self._implicitNameOp('DELETE', append)

        self.__list_count = self.__list_count - 1

    def visitListCompFor(self, node):
        start = self.newBlock()
        anchor = self.newBlock()

        node.list.accept( self )
        self.emit('GET_ITER')
        self.nextBlock(start)
        self.set_lineno(node, force=True)
        self.emitop_block('FOR_ITER', anchor)
        self.nextBlock()
        node.assign.accept( self )
        return start, anchor

    def visitListCompIf(self, node):
        branch = self.genexpr_cont_stack[-1]
        self.set_lineno(node, force=True)
        node.test.accept( self )
        self.emitop_block('JUMP_IF_FALSE', branch)
        self.newBlock()
        self.emit('POP_TOP')

    def visitGenExpr(self, node):
        gen = GenExprCodeGenerator(self.space, node, self.scopes, self.class_name,
                                   self.get_module())
        walk(node.code, gen)
        gen.finish()
        self.set_lineno(node)
        frees = gen.scope.get_free_vars()
        if frees:
            for name in frees:
                self.emitop('LOAD_CLOSURE', name)
            self.emitop_obj('LOAD_CONST', gen)
            # self.emitop_obj('LOAD_CONST', gen.getCode())            
            self.emitop_int('MAKE_CLOSURE', 0)
        else:
            self.emitop_obj('LOAD_CONST', gen)
            # self.emitop_obj('LOAD_CONST', gen.getCode())            
            self.emitop_int('MAKE_FUNCTION', 0)

        # precomputation of outmost iterable
        node.code.quals[0].iter.accept( self )
        self.emit('GET_ITER')
        self.emitop_int('CALL_FUNCTION', 1)

    def visitGenExprInner(self, node):
        self.set_lineno(node)
        # setup list

        stack = []
        for i, for_ in zip(range(len(node.quals)), node.quals):
            start, anchor = for_.accept( self )
            self.genexpr_cont_stack.append( None )
            for if_ in for_.ifs:
                if self.genexpr_cont_stack[-1] is None:
                    self.genexpr_cont_stack[-1] = self.newBlock()
                if_.accept( self )
            stack.insert(0, (start, self.genexpr_cont_stack[-1], anchor))
            self.genexpr_cont_stack.pop()

        node.expr.accept( self )
        self.emit('YIELD_VALUE')

        for start, cont, anchor in stack:
            if cont:
                skip_one = self.newBlock()
                self.emitop_block('JUMP_FORWARD', skip_one)
                self.startBlock(cont)
                self.emit('POP_TOP')
                self.nextBlock(skip_one)
            self.emitop_block('JUMP_ABSOLUTE', start)
            self.startBlock(anchor)
        self.emitop_obj('LOAD_CONST', self.space.w_None)

    def visitGenExprFor(self, node):
        start = self.newBlock()
        anchor = self.newBlock()

        if node.is_outmost:
            self.loadName('[outmost-iterable]')
        else:
            node.iter.accept( self )
            self.emit('GET_ITER')

        self.nextBlock(start)
        self.set_lineno(node, force=True)
        self.emitop_block('FOR_ITER', anchor)
        self.nextBlock()
        node.assign.accept( self )
        return start, anchor

    def visitGenExprIf(self, node ):
        branch = self.genexpr_cont_stack[-1]
        self.set_lineno(node, force=True)
        node.test.accept( self )
        self.emitop_block('JUMP_IF_FALSE', branch)
        self.newBlock()
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
            self.nextBlock()
            node.test.accept( self )
            self.emitop_block('JUMP_IF_TRUE', end)
            self.nextBlock()
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
        self.setups.push((EXCEPT, body))
        node.body.accept( self )
        self.emit('POP_BLOCK')
        self.setups.pop()
        self.emitop_block('JUMP_FORWARD', lElse)
        self.startBlock(handlers)

        last = len(node.handlers) - 1
        next = None
        for expr, target, body in node.handlers:
            if expr:
                self.set_lineno(expr)
                self.emit('DUP_TOP')
                expr.accept( self )
                self.emitop('COMPARE_OP', 'exception match')
                next = self.newBlock()
                self.emitop_block('JUMP_IF_FALSE', next)
                self.nextBlock()
                self.emit('POP_TOP')
            else:
                next = None
            self.emit('POP_TOP')
            if target:
                target.accept( self )
            else:
                self.emit('POP_TOP')
            self.emit('POP_TOP')
            body.accept( self )
            self.emitop_block('JUMP_FORWARD', end)
            self.nextBlock(next)
            if expr: # XXX
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
        self.setups.push((TRY_FINALLY, body))
        node.body.accept( self )
        self.emit('POP_BLOCK')
        self.setups.pop()
        self.emitop_obj('LOAD_CONST', self.space.w_None)
        self.nextBlock(final)
        self.setups.push((END_FINALLY, final))
        node.final.accept( self )
        self.emit('END_FINALLY')
        self.setups.pop()

    # misc

    def visitDiscard(self, node):
        self.set_lineno(node)
        node.expr.accept( self )
        self.emit('POP_TOP')

    def visitConst(self, node):
        self.emitop_obj('LOAD_CONST', node.value)

    def visitKeyword(self, node):
        self.emitop_obj('LOAD_CONST', self.space.wrap(node.name) )
        node.expr.accept( self )

    def visitGlobal(self, node):
        # no code to generate
        pass

    def visitName(self, node):
        self.set_lineno(node)
        self.loadName(node.varname)

    def visitPass(self, node):
        self.set_lineno(node)

    def visitImport(self, node):
        self.set_lineno(node)
        for name, alias in node.names:
            self.emitop_obj('LOAD_CONST', self.space.w_None)
            self.emitop('IMPORT_NAME', name)
            mod = name.split(".")[0]
            if alias:
                self._resolveDots(name)
                self.storeName(alias)
            else:
                self.storeName(mod)

    def visitFrom(self, node):
        self.set_lineno(node)
        fromlist = [ self.space.wrap(name) for name,alias in node.names ]
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
                self.storeName(alias or name)
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
        node.expr.accept( self )
        dups = len(node.nodes) - 1
        for i in range(len(node.nodes)):
            elt = node.nodes[i]
            if i < dups:
                self.emit('DUP_TOP')
            if isinstance(elt, ast.Node):
                elt.accept( self )

    def visitAssName(self, node):
        if node.flags == 'OP_ASSIGN':
            self.storeName(node.name)
        elif node.flags == 'OP_DELETE':
            self.set_lineno(node)
            self.delName(node.name)
        else:
            print "oops", node.flags

    def visitAssAttr(self, node):
        node.expr.accept( self )
        if node.flags == 'OP_ASSIGN':
            self.emitop('STORE_ATTR', self.mangle(node.attrname))
        elif node.flags == 'OP_DELETE':
            self.emitop('DELETE_ATTR', self.mangle(node.attrname))
        else:
            print "warning: unexpected flags:", node.flags
            print node

    def _visitAssSequence(self, node, op='UNPACK_SEQUENCE'):
        if findOp(node) != 'OP_DELETE':
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
        pos = 0
        kw = 0
        self.set_lineno(node)
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
        opcode = callfunc_opcode_info[have_star, have_dstar]
        self.emitop_int(opcode, kw << 8 | pos)

    def visitPrint(self, node, newline=0):
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
        if node.dest and not newline:
            self.emit('POP_TOP')

    def visitPrintnl(self, node):
        self.visitPrint(node, newline=1)
        if node.dest:
            self.emit('PRINT_NEWLINE_TO')
        else:
            self.emit('PRINT_NEWLINE')

    def visitReturn(self, node):
        self.set_lineno(node)
        node.value.accept( self )
        self.emit('RETURN_VALUE')

    def visitYield(self, node):
        self.set_lineno(node)
        node.value.accept( self )
        self.emit('YIELD_VALUE')

    # slice and subscript stuff

    def visitSlice(self, node, aug_flag=None):
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
        if node.flags == 'OP_APPLY':
            self.emit('SLICE+%d' % slice)
        elif node.flags == 'OP_ASSIGN':
            self.emit('STORE_SLICE+%d' % slice)
        elif node.flags == 'OP_DELETE':
            self.emit('DELETE_SLICE+%d' % slice)
        else:
            print "weird slice", node.flags
            raise

    def visitSubscript(self, node, aug_flag=None):
        node.expr.accept( self )
        for sub in node.subs:
            sub.accept( self )
        if aug_flag:
            self.emitop_int('DUP_TOPX', 2)
        if len(node.subs) > 1:
            self.emitop_int('BUILD_TUPLE', len(node.subs))
        if node.flags == 'OP_APPLY':
            self.emit('BINARY_SUBSCR')
        elif node.flags == 'OP_ASSIGN':
            self.emit('STORE_SUBSCR')
        elif node.flags == 'OP_DELETE':
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
    scopes = None

    def __init__(self, space, tree, futures = []):
        self.graph = pyassem.PyFlowGraph(space, "<module>", tree.filename)
        self.futures = future.find_futures(tree)
        for f in futures:
            if f not in self.futures:
                self.futures.append(f)
        CodeGenerator.__init__(self, space)
        walk(tree, self)

    def get_module(self):
        return self

class ExpressionCodeGenerator(CodeGenerator):
    scopes = None

    def __init__(self, space, tree, futures=[]):
        self.graph = pyassem.PyFlowGraph(space, "<expression>", tree.filename)
        self.futures = futures[:]
        CodeGenerator.__init__(self, space)
        walk(tree, self)

    def get_module(self):
        return self

class InteractiveCodeGenerator(CodeGenerator):
    scopes = None

    def __init__(self, space, tree, futures=[]):
        self.graph = pyassem.PyFlowGraph(space, "<interactive>", tree.filename)
        self.futures = future.find_futures(tree)
        for f in futures:
            if f not in self.futures:
                self.futures.append(f)
        CodeGenerator.__init__(self, space)
        self.set_lineno(tree)
        walk(tree, self)
        self.emit('RETURN_VALUE')

    def get_module(self):
        return self

    def visitDiscard(self, node):
        # XXX Discard means it's an expression.  Perhaps this is a bad
        # name.
        node.expr.accept( self )
        self.emit('PRINT_EXPR')

class AbstractFunctionCode(CodeGenerator):
    optimized = 1
    lambdaCount = 0

    def __init__(self, space, func, scopes, isLambda, class_name, mod):
        self.class_name = class_name
        self.module = mod
        if isLambda:
            klass = FunctionCodeGenerator
            name = "<lambda.%d>" % klass.lambdaCount
            klass.lambdaCount = klass.lambdaCount + 1
        else:
            name = func.name

        args, hasTupleArg = generateArgList(func.argnames)
        self.graph = pyassem.PyFlowGraph(space, name, func.filename, args,
                                         optimized=1)
        self.isLambda = isLambda
        CodeGenerator.__init__(self, space)

        if not isLambda and func.doc:
            self.setDocstring(func.doc)

        lnf = LocalNameFinder(args)
        func.code.accept(lnf)
        self.locals.push(lnf.getLocals())
        if func.varargs:
            self.graph.setFlag(CO_VARARGS)
        if func.kwargs:
            self.graph.setFlag(CO_VARKEYWORDS)
        self.set_lineno(func)
        if hasTupleArg:
            self.generateArgUnpack(func.argnames)

    def get_module(self):
        return self.module

    def finish(self):
        self.graph.startExitBlock()
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
                self._nameOp('STORE', elt.name)
            elif isinstance(elt, ast.AssTuple):
                self.unpackSequence( elt )
            else:
                raise TypeError( "Got argument %s of type %s" % (elt,type(elt)))

    unpackTuple = unpackSequence

class FunctionCodeGenerator(AbstractFunctionCode):
    scopes = None

    def __init__(self, space, func, scopes, isLambda, class_name, mod):
        self.scopes = scopes
        self.scope = scopes[func]
        AbstractFunctionCode.__init__(self, space, func, scopes, isLambda, class_name, mod)
        self.graph.setFreeVars(self.scope.get_free_vars())
        self.graph.setCellVars(self.scope.get_cell_vars())
        if self.scope.generator is not None:
            self.graph.setFlag(CO_GENERATOR)

class GenExprCodeGenerator(AbstractFunctionCode):
    scopes = None

    def __init__(self, space, gexp, scopes, class_name, mod):
        self.scopes = scopes
        self.scope = scopes[gexp]
        AbstractFunctionCode.__init__(self, space, gexp, scopes, 1, class_name, mod)
        self.graph.setFreeVars(self.scope.get_free_vars())
        self.graph.setCellVars(self.scope.get_cell_vars())
        self.graph.setFlag(CO_GENERATOR)

class AbstractClassCode(CodeGenerator):

    def __init__(self, space, klass, scopes, module):
        self.class_name = klass.name
        self.module = module
        self.graph = pyassem.PyFlowGraph( space, klass.name, klass.filename,
                                           optimized=0, klass=1)
        CodeGenerator.__init__(self, space)
        lnf = LocalNameFinder()
        klass.code.accept(lnf)
        self.locals.push(lnf.getLocals())
        self.graph.setFlag(CO_NEWLOCALS)
        if klass.doc:
            self.setDocstring(klass.doc)

    def get_module(self):
        return self.module

    def finish(self):
        self.graph.startExitBlock()
        self.emit('LOAD_LOCALS')
        self.emit('RETURN_VALUE')

class ClassCodeGenerator(AbstractClassCode):
    scopes = None

    def __init__(self, space, klass, scopes, module):
        self.scopes = scopes
        self.scope = scopes[klass]
        AbstractClassCode.__init__(self, space, klass, scopes, module)
        self.graph.setFreeVars(self.scope.get_free_vars())
        self.graph.setCellVars(self.scope.get_cell_vars())
        self.set_lineno(klass)
        self.emitop("LOAD_GLOBAL", "__name__")
        self.storeName("__module__")
        if klass.doc:
            self.emitop_obj("LOAD_CONST", klass.doc)
            self.storeName('__doc__')

def generateArgList(arglist):
    """Generate an arg list marking TupleArgs"""
    args = []
    extra = []
    count = 0
    for i in range(len(arglist)):
        elt = arglist[i]
        if isinstance(elt, ast.AssName):
            args.append(elt)
        elif isinstance(elt, ast.AssTuple):
            args.append(TupleArg(i * 2, elt))
            extra.extend(ast.flatten(elt))
            count = count + 1
        else:
            raise ValueError( "unexpect argument type: %s" % elt )
    return args + extra, count

def findOp(node):
    """Find the op (DELETE, LOAD, STORE) in an AssTuple tree"""
    v = OpFinder()
    # walk(node, v, verbose=0)
    node.accept(v)
    return v.op

class OpFinder(ast.ASTVisitor):
    def __init__(self):
        self.op = None
    def visitAssName(self, node):
        if self.op is None:
            self.op = node.flags
        elif self.op != node.flags:
            raise ValueError, "mixed ops in stmt"
    visitAssAttr = visitAssName
    visitSubscript = visitAssName



class AugLoadVisitor(ast.ASTVisitor):
    def __init__(self, main_visitor):
        self.main = main_visitor

    def default(self, node):
        raise RuntimeError("shouldn't arrive here!")
    
    def visitName(self, node ):
        self.main.loadName(node.varname)

    def visitGetattr(self, node):
        node.expr.accept( self )
        self.main.emit('DUP_TOP')
        self.main.emitop('LOAD_ATTR', self.main.mangle(node.attrname))

    def visitSlice(self, node):
        self.main.visitSlice(node, 1)

    def visitSubscript(self, node):
        if len(node.subs) > 1:
            raise SyntaxError( "augmented assignment to tuple is not possible" )
        self.main.visitSubscript(node, 1)


class AugStoreVisitor(ast.ASTVisitor):
    def __init__(self, main_visitor):
        self.main = main_visitor
        
    def default(self, node):
        raise RuntimeError("shouldn't arrive here!")
    
    def visitName(self, node):
        self.main.storeName(node.varname)

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
        if len(node.subs) > 1:
            raise SyntaxError( "augmented assignment to tuple is not possible" )
        self.main.emit('ROT_THREE')
        self.main.emit('STORE_SUBSCR')

if __name__ == "__main__":
    for file in sys.argv[1:]:
        compileFile(file)
