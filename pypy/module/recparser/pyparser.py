# Emulation layer for the recparser module
# make it so that pyparser matches the 'parser' module interface

from pypy.interpreter.baseobjspace import ObjSpace, Wrappable, W_Root
from pypy.interpreter.gateway import interp2app, applevel
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.typedef import interp_attrproperty, GetSetProperty
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.pyparser.syntaxtree import TokenNode, SyntaxNode, AbstractSyntaxVisitor
from pypy.interpreter.pyparser.pythonutil import PYTHON_PARSER, ParseError
from pypy.interpreter.pyparser import grammar, pysymbol, pytoken

__all__ = [ "ASTType", "STType", "suite", "expr" ]


class SyntaxToTupleVisitor(AbstractSyntaxVisitor):
    def __init__(self, space, line_info):
        self.space = space
        self.line_info = line_info
        self.tuple_stack_w = []

    def w_result( self ):
        return self.tuple_stack_w[-1]

    def visit_syntaxnode( self, node ):
        space = self.space
        # visiting in depth first order
        for n in node.nodes:
            n.visit(self)
        n = len(node.nodes)
        start = len(self.tuple_stack_w) - n
        assert start >= 0   # annotator hint
        l = [ space.wrap( node.name ) ] + self.tuple_stack_w[start:]
        del self.tuple_stack_w[start:]
        self.tuple_stack_w.append( space.newtuple( l ) )

    def visit_tempsyntaxnode( self, node ):
        assert False, "Should not come here"

    def visit_tokennode( self, node ):
        space = self.space
        num = node.name
        lineno = node.lineno
        if node.value is not None:
            val = node.value
        else:
            if num not in ( pytoken.NEWLINE, pytoken.INDENT,
                            pytoken.DEDENT, pytoken.ENDMARKER ):
                val = pytoken.tok_rpunct[num]
            else:
                val = node.value or ''
        if self.line_info:
            self.tuple_stack_w.append( space.newtuple( [space.wrap(num),
                                                        space.wrap(val),
                                                        space.wrap(lineno)]))
        else:
            self.tuple_stack_w.append( space.newtuple( [space.wrap(num),
                                                        space.wrap(val)]))


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

    def descr_totuple(self, line_info = True):
        """STType.totuple()
        Convert the ST object into a tuple representation.
        """
        visitor = SyntaxToTupleVisitor(self.space, line_info )
        self.node.visit( visitor )
        return visitor.w_result()

    descr_totuple.unwrap_spec=['self', int]

    def tolist(self, line_info = True):
        """STType.tolist()
        Convert the ST object into a list representation.
        """
        return self.node.tolist( line_info )

    def isexpr(self):
        """STType.isexpr()
        Returns true if the root node in the syntax tree is an expr node,
        false otherwise.
        """
        return self.node.name == pysymbol.eval_input

    def issuite(self):
        """STType.issuite()
        Returns true if the root node in the syntax tree is a suite node,
        false otherwise.
        """
        return self.node.name == pysymbol.file_input

    def descr_compile(self, w_filename = "<syntax_tree>"):
        """STType.compile()
        """
        # We use the compiler module for that
        space = self.space
        w_tup = self.descr_totuple(line_info=True)
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

def parse_python_source(space, source, goal):
    builder = grammar.BaseGrammarBuilder(debug=False, rules=PYTHON_PARSER.rules)
    try:
        PYTHON_PARSER.parse_source(source, goal, builder )
        return builder.stack[-1]
    except ParseError, e:
        raise OperationError(space.w_SyntaxError,
                             e.wrap_info(space, '<string>'))

def suite( space, source ):
    # make the annotator life easier (don't use str.splitlines())
    syntaxtree = parse_python_source( space, source, "file_input" )
    return space.wrap( STType(space, syntaxtree) )

suite.unwrap_spec = [ObjSpace, str]

def expr( space, source ):
    # make the annotator life easier (don't use str.splitlines())
    syntaxtree = parse_python_source( space, source, "eval_input" )
    return space.wrap( STType(space, syntaxtree) )

expr.unwrap_spec = [ObjSpace, str]

def ast2tuple(space, node, line_info=0):
    """Quick dummy implementation of parser.ast2tuple(tree) function"""
    return node.descr_totuple( line_info )

ast2tuple.unwrap_spec = [ObjSpace, STType, int]


def unwrap_syntax_tree( space, w_sequence ):
    items = space.unpackiterable( w_sequence )
    nodetype = space.int_w( items[0] )
    is_syntax = True
    if nodetype>=0 and nodetype<pytoken.N_TOKENS:
        is_syntax = False
    if is_syntax:
        nodes = []
        for w_node in items[1:]:
            node = unwrap_syntax_tree( space, w_node )
            nodes.append( node )
        return SyntaxNode( nodetype, nodes )
    else:
        value = space.str_w( items[1] )
        lineno = -1
        if len(items)>2:
            lineno = space.int_w( items[2] )
        return TokenNode( nodetype, value, lineno )

def sequence2st(space, w_sequence):
    syntaxtree = unwrap_syntax_tree( space, w_sequence )
    return space.wrap( STType(space, syntaxtree) )


def decode_string_literal(space, s, w_encoding=None):
    from pypy.interpreter.pyparser.parsestring import parsestr
    if space.is_true(w_encoding):
        encoding = space.str_w(w_encoding)
    else:
        encoding = None
    return parsestr(space, encoding, s)
decode_string_literal.unwrap_spec = [ObjSpace, str, W_Root]
