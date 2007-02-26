# Copyright (c) 2000-2003 LOGILAB S.A. (Paris, FRANCE).
# http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""

"""

__revision__ = "$Id: $"

import pythonutil
from compiler.visitor import ASTVisitor
from compiler.bytecode import *

def compile(source, filename, mode, flags=None, dont_inherit=None):
    """Replacement for builtin compile() function"""
    # source to ast conversion
    if mode == "single":
        tree = pythonutil.ast_single_input( source )
    elif mode == "eval":
        tree = pythonutil.ast_eval_input( source )
    elif mode == "exec":
        tree = pythonutil.ast_srcfile_input( source, filename )
    else:
        raise RuntimeError("Not found")
    return compile_ast( tree, filename, flags=None, dont_inherit=None)


def compile_ast( tree, filename, flags=None, dont_inherit=None ):
    v = CompilerVisitor( filename, flags, dont_inherit )
    tree.visit(v)
    return tree, v


class PrintContext(object):
    def __init__(self):
        self.lineno = 0
        
    def emit(self, insn):
        print "% 5d     %s" % (self.lineno, insn)

    def emit_arg(self, insn, arg ):
        print "% 5d     %8s  %s" % (self.lineno, insn, arg)

    def set_lineno(self, lineno):
        self.lineno = lineno


class Block(object):
    def __init__(self):
        self.insns = []
        self.start_pos = 0

    def append(self, insn ):
        self.insns.append( insn )

    def get_size(self):
        s = 0
        for i in self.insns:
            s += i.size()
        return s

    def set_start_pos(self, pos ):
        self.start_pos = pos

###########################
### XXX MUST FIX SET_LINENO
###########################

    
class CompilerVisitor(ASTVisitor):
    """Basic code generator for Python Bytecode"""

    LOOP = 1
    EXCEPT = 2
    TRY_FINALLY = 3
    END_FINALLY = 4

    def __init__(self, filename, flags, dont_inherit ):
        self.scopes = []
        self.blocks = []
        self.setups = [] # for loops and try/finally
        self.code = None
        self.current_block = None
        self.ctx = PrintContext()

    ### Visitor functions

    def visitModule( self, node ):
        # setup doc
        self.newBlock()
        node.node.visit( self )
        
        # build code object
        for block in self.blocks:
            pass

    def visitExpression(self, node):
        pass

    def visitFunction(self, node):
        pass

    def visitIf(self, node):
        end = Block()
        for test, suite in node.tests:
            if is_constant_false(test):
                continue
            test.visit(self) # emit test code in current block
            nextTest = Block()
            self.emit(CondJump('IF_FALSE', nextTest))
            self.nextBlock()
            self.emit(PopTop())
            suite.visit(self)
            self.emit(CondJump('FWD', end))
            self.startBlock(nextTest)
            self.emit(PopTop())
        if node.else_:
            node.else_.visit(self)
        self.nextBlock(end)
                           
    def visitWhile(self, node):
        # XXX emit LINENO here ?
        loop = self.newBlock()
        else_ = self.newBlock()
        after = self.newBlock()

        self.emit(SetupLoop(after))
        
        self.nextBlock(loop)
        self.setups.append((self.LOOP, loop))

        node.test.visit(self)
        self.emit(CondJump('IF_FALSE', else_or, after))

        self.nextBlock()
        self.emit(PopTop())
        node.body.visit(self)
        self.emit(CondJump('ABOSLUTE', loop))

        self.startBlock(else_) # or just the POPs if not else clause
        self.emit(PopTop())
        self.emit(PopBlock())
        self.setups.pop()
        if node.else_:
            node.else_.visit(self)
        self.nextBlock(after)
        

    def visitFor(self, node):
        start = self.newBlock()
        anchor = self.newBlock()
        after = self.newBlock()

        self.setups.append((self.LOOP, start))

        self.emit(SetupLoop(after))
        node.list.visit(self)
        self.emit(GetIter())

        self.nextBlock(start)
        self.set_lineno(node, force=1)
        self.emit(ForIter(anchor))
        node.assign.visit(self)
        node.body.visit(self)
        self.emit(CondJump('ABSOLUTE', start))
        self.nextBlock(anchor)
        self.emit(PopBlock())
        self.setups.pop()
        if node.else_:
            node.else_.visist(self)
        self.nextBlock(after)

    def visitBreak(self, node):
        if not self.setups:
            raise SyntaxError("'break' outside loop (%s, %d)" % \
                              (node.filename, node.lineno))
        # self.set_lineno(node)
        self.emit(BreakLoop())


    ## Shortcut methods
    def emit(self, bytecode):
        bytecode.emit(self.ctx)
            
    ### Block handling functions
    def newBlock(self):
        """Create a new block and make it current"""
        b = Block()
        self.blocks.append(b)
        # self.current_block = b
        return b

    def nextBlock(self, block=None):
        """goto next block in the flow graph"""
        if block is None:
            block = self.newBlock()

        self.blocks.append(block)
        self.startBlock(block)
    
    def startBlock(self, block):
        self.current_block = block

if __name__ == "__main__":
    testf = file("pycodegen2.py").read()
    ast, v = compile(testf,"pycodegen2.py","exec")
    print ast
    print v
    
