# Emulation layer for the recparser module
# make it so that pyparser matches the 'parser' module interface

from pypy.interpreter.baseobjspace import ObjSpace, Wrappable, W_Root
from pypy.interpreter.gateway import interp2app, applevel
from pypy.interpreter.error import OperationError 
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.typedef import interp_attrproperty, GetSetProperty
from pypy.interpreter.pycode import PyCode 
from pypy.interpreter.pyparser.syntaxtree import SyntaxNode
from pypy.interpreter.pyparser.pythonparse import parse_python_source
from pypy.interpreter.pyparser.pythonutil import PYTHON_PARSER

__all__ = [ "ASTType", "STType", "suite", "expr" ]

class STType (Wrappable):
    """Class STType
    """
    def __init__ (self, space, syntaxnode ):
        """STType.__init__()
        Wrapper for parse tree data returned by parse_python_source.
        This encapsulate the syntaxnode at the head of the syntax tree
        """
        self.space = space 
        self.node = syntaxnode

    def totuple (self, line_info = False ):
        """STType.totuple()
        Convert the ST object into a tuple representation.
        """
        # lineinfo is ignored for now
        return self.node.totuple( line_info )

    def descr_totuple(self, line_info = False): 
        return self.space.wrap(self.totuple(line_info))
       
    descr_totuple.unwrap_spec=['self', int]

    def tolist (self, line_info = False):
        """STType.tolist()
        Convert the ST object into a list representation.
        """
        return self.node.tolist( line_info )

    def isexpr (self):
        """STType.isexpr()
        Returns true if the root node in the syntax tree is an expr node,
        false otherwise.
        """
        return self.node.name == "eval_input"

    def issuite (self):
        """STType.issuite()
        Returns true if the root node in the syntax tree is a suite node,
        false otherwise.
        """
        return self.node.name == "file_input"

    def descr_compile (self, w_filename = "<syntax_tree>"): 
        """STType.compile()
        """
        # We use the compiler module for that
        space = self.space 
        tup = self.totuple(line_info=1) 
        w_tup = space.wrap(tup)   
        w_compileAST = mycompile(space, w_tup, w_filename) 
        if self.isexpr(): 
            return exprcompile(space, w_compileAST) 
        else: 
            return modcompile(space, w_compileAST) 

ASTType = STType

app = applevel(""" 
    def mycompile(tup, filename): 
        import compiler 
        transformer = compiler.transformer.Transformer()
        compileAST = transformer.compile_node(tup) 
        compiler.misc.set_filename(filename, compileAST)
        return compileAST 

    def exprcompile(compileAST): 
        import compiler
        gen = compiler.pycodegen.ExpressionCodeGenerator(compileAST)
        return gen.getCode()

    def modcompile(compileAST): 
        import compiler
        gen = compiler.pycodegen.ModuleCodeGenerator(compileAST)
        return gen.getCode() 
""", filename=__file__)

mycompile = app.interphook("mycompile")
exprcompile = app.interphook("exprcompile")
modcompile = app.interphook("modcompile")

STType.typedef = TypeDef("parser.st",
    compile = interp2app(STType.descr_compile),
    totuple = interp2app(STType.descr_totuple),
)

def suite( space, source ):
    # make the annotator life easier (don't use str.splitlines())
    strings = [line + '\n' for line in source.split('\n')]
    builder = parse_python_source( strings, PYTHON_PARSER, "file_input" )
    return space.wrap( STType(space, builder.stack[-1]) )    

suite.unwrap_spec = [ObjSpace, str]

def expr( space, source ):
    # make the annotator life easier (don't use str.splitlines())
    strings = [line + '\n' for line in source.split('\n')]
    builder = parse_python_source( strings, PYTHON_PARSER, "eval_input" )
    return space.wrap( STType(space, builder.stack[-1]) )    

expr.unwrap_spec = [ObjSpace, str]

def ast2tuple(space, node, line_info=0):
    """Quick dummy implementation of parser.ast2tuple(tree) function"""
    tuples = node.totuple(line_info)
    return space.wrap(tuples)

ast2tuple.unwrap_spec = [ObjSpace, STType, int]
