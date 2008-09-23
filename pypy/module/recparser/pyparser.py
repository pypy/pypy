# Emulation layer for the recparser module
# make it so that pyparser matches the 'parser' module interface

from pypy.interpreter.baseobjspace import ObjSpace, Wrappable, W_Root
from pypy.interpreter.gateway import interp2app, applevel
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.typedef import interp_attrproperty, GetSetProperty
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.pyparser.syntaxtree import TokenNode, SyntaxNode, AbstractSyntaxVisitor
from pypy.interpreter.pyparser.error import SyntaxError
from pypy.interpreter.pyparser import grammar, symbol, pytoken
from pypy.interpreter.argument import Arguments

# backward compat (temp)


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
        tokens = space.default_compiler.parser.tokens
        num = node.name
        lineno = node.lineno
        if node.value is not None:
            val = node.value
        else:
            if num != tokens['NEWLINE'] and \
               num != tokens['INDENT'] and \
               num != tokens['DEDENT'] and \
               num != tokens['ENDMARKER']:
                val = space.default_compiler.parser.tok_rvalues[num]
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
        return self.node.name == symbol.eval_input

    def issuite(self):
        """STType.issuite()
        Returns true if the root node in the syntax tree is a suite node,
        false otherwise.
        """
        return self.node.name == symbol.file_input

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

def get(space, name):
    w_module = space.getbuiltinmodule('parser')
    return space.getattr(w_module, space.wrap(name))

def get_ast_compiler(space):
    from pypy.interpreter.pycompiler import PythonAstCompiler
    compiler = space.createcompiler()
    if not isinstance(compiler, PythonAstCompiler):
        raise OperationError(space.w_RuntimeError,
                             space.wrap("not implemented in a PyPy with "
                                        "a non-AST compiler"))
    return compiler

def parse_python_source(space, source, mode):
    parser = get_ast_compiler(space).get_parser()
    builder = grammar.BaseGrammarBuilder(debug=False, parser=parser)
    builder.space = space
    try:
        parser.parse_source(source, mode, builder)
        return builder.stack[-1]
    except SyntaxError, e:
        raise OperationError(space.w_SyntaxError,
                             e.wrap_info(space, '<string>'))

def suite( space, source ):
    # make the annotator life easier (don't use str.splitlines())
    syntaxtree = parse_python_source( space, source, "exec" )
    return space.wrap( STType(space, syntaxtree) )

suite.unwrap_spec = [ObjSpace, str]

def expr( space, source ):
    # make the annotator life easier (don't use str.splitlines())
    syntaxtree = parse_python_source( space, source, "eval" )
    return space.wrap( STType(space, syntaxtree) )

expr.unwrap_spec = [ObjSpace, str]

def ast2tuple(space, node, line_info=0):
    """Quick dummy implementation of parser.ast2tuple(tree) function"""
    return node.descr_totuple( line_info )

ast2tuple.unwrap_spec = [ObjSpace, STType, int]

def check_length(space, items, length):
    if len(items) < length:
        raise OperationError(get(space, "ParserError"),
                             space.wrap("argument too small"))

def unwrap_syntax_tree( space, w_sequence ):
    items = space.unpackiterable( w_sequence )
    parser = space.default_compiler.parser
    check_length(space, items, 1)
    nodetype = space.int_w( items[0] )
    if parser.is_base_token(nodetype):
        nodes = []
        for w_node in items[1:]:
            node = unwrap_syntax_tree( space, w_node )
            nodes.append( node )
        return SyntaxNode( nodetype, nodes )
    else:
        check_length(space, items, 2)
        value = space.str_w( items[1] )
        lineno = -1
        if len(items)>2:
            lineno = space.int_w( items[2] )
        return TokenNode( nodetype, value, lineno )

def sequence2st(space, w_sequence):
    syntaxtree = unwrap_syntax_tree( space, w_sequence )
    return space.wrap( STType(space, syntaxtree) )


def source2ast(space, source):
    from pypy.interpreter.pyparser.error import SyntaxError
    compiler = get_ast_compiler(space)
    try:
        return space.wrap(compiler.source2ast(source, 'exec'))
    except SyntaxError, e:
        raise OperationError(space.w_SyntaxError, e.wrap_info(space, "<parser-module>"))
source2ast.unwrap_spec = [ObjSpace, str]


def decode_string_literal(space, s, w_encoding=None):
    from pypy.interpreter.pyparser.parsestring import parsestr
    if space.is_true(w_encoding):
        encoding = space.str_w(w_encoding)
    else:
        encoding = None
    return parsestr(space, encoding, s)
decode_string_literal.unwrap_spec = [ObjSpace, str, W_Root]


# append typedefs to the grammar objects
from pypy.interpreter.pyparser.grammar import GrammarElement, Alternative
from pypy.interpreter.pyparser.grammar import Sequence, KleeneStar, Token


def descr_grammarelement_repr( self, space ):
    """TODO: make __repr__ RPython"""
    import symbol
    return space.wrap( self.display(0, symbol.sym_name) )

def descr_grammarelement_get_children( self, space ):
    return space.newlist( [ space.wrap(it) for it in self.args ] )

GrammarElement.descr_grammarelement_repr = descr_grammarelement_repr
GrammarElement.descr_grammarelement_get_children = descr_grammarelement_get_children

GrammarElement.typedef = TypeDef( "GrammarElement",
                                  #__repr__ = interp2app(GrammarElement.descr_grammarelement_repr,
                                  #                      unwrap_spec=['self', ObjSpace] ),
                                  get_children = interp2app(GrammarElement.descr_grammarelement_get_children,
                                                            unwrap_spec=['self', ObjSpace] ),
                                  )



def descr_alternative_append( self, space, w_rule ):
    rule = space.interp_w(GrammarElement, w_rule)
    self.args.append( rule )


def descr_alternative___getitem__(self, space, idx ):
    return space.wrap(self.args[idx])
    
def descr_alternative___setitem__(self, space, idx, w_rule ):
    rule = space.interp_w(GrammarElement, w_rule)
    return space.wrap( self.args[idx] )

def descr_alternative___delitem__(self, space, idx ):
    del self.args[idx]

def descr_alternative_insert(self, space, idx, w_rule ):
    rule = space.interp_w(GrammarElement, w_rule)
    if idx<0 or idx>len(self.args):
        raise OperationError( space.w_IndexError, space.wrap("Invalid index") )
    self.args.insert( idx, rule )

Alternative.descr_alternative_append = descr_alternative_append
Alternative.descr_alternative_insert = descr_alternative_insert
Alternative.descr_alternative___getitem__ = descr_alternative___getitem__
Alternative.descr_alternative___setitem__ = descr_alternative___setitem__
Alternative.descr_alternative___delitem__ = descr_alternative___delitem__


Alternative.typedef = TypeDef("Alternative", GrammarElement.typedef,
                              __getitem__ = interp2app( Alternative.descr_alternative___getitem__,
                                                        unwrap_spec=['self',ObjSpace,int]),
                              __setitem__ = interp2app( Alternative.descr_alternative___setitem__,
                                                        unwrap_spec=['self',ObjSpace,int,W_Root]),
                              __delitem__ = interp2app( Alternative.descr_alternative___delitem__,
                                                        unwrap_spec=['self',ObjSpace,int]),
                              insert = interp2app( Alternative.descr_alternative_insert,
                                                   unwrap_spec = ['self', ObjSpace, int, W_Root ] ),
                              append = interp2app( Alternative.descr_alternative_append,
                                                   unwrap_spec = ['self', ObjSpace, W_Root ] ),
                              )

Sequence.descr_alternative_append = descr_alternative_append
Sequence.descr_alternative_insert = descr_alternative_insert
Sequence.descr_alternative___getitem__ = descr_alternative___getitem__
Sequence.descr_alternative___setitem__ = descr_alternative___setitem__
Sequence.descr_alternative___delitem__ = descr_alternative___delitem__


Sequence.typedef = TypeDef("Sequence", GrammarElement.typedef,
                              __getitem__ = interp2app( Sequence.descr_alternative___getitem__,
                                                        unwrap_spec=['self',ObjSpace,int]),
                              __setitem__ = interp2app( Sequence.descr_alternative___setitem__,
                                                        unwrap_spec=['self',ObjSpace,int,W_Root]),
                              __delitem__ = interp2app( Sequence.descr_alternative___delitem__,
                                                        unwrap_spec=['self',ObjSpace,int]),
                              insert = interp2app( Sequence.descr_alternative_insert,
                                                   unwrap_spec = ['self', ObjSpace, int, W_Root ] ),
                              append = interp2app( Sequence.descr_alternative_append,
                                                   unwrap_spec = ['self', ObjSpace, W_Root ] ),
                              )

def descr_kleenestar___getitem__(self, space, idx ):
    if idx!=0:
        raise OperationError( space.w_ValueError, space.wrap("KleeneStar only support one child"))
    return space.wrap(self.args[idx])
    
def descr_kleenestar___setitem__(self, space, idx, w_rule ):
    if idx!=0:
        raise OperationError( space.w_ValueError, space.wrap("KleeneStar only support one child"))
    rule = space.interp_w(GrammarElement, w_rule)
    self.args[idx] = rule

KleeneStar.descr_kleenestar___getitem__ = descr_kleenestar___getitem__
KleeneStar.descr_kleenestar___setitem__ = descr_kleenestar___setitem__

KleeneStar.typedef = TypeDef("KleeneStar", GrammarElement.typedef,
                             __getitem__ = interp2app(KleeneStar.descr_kleenestar___getitem__,
                                                      unwrap_spec=[ 'self', ObjSpace, int]),
                             __setitem__ = interp2app(KleeneStar.descr_kleenestar___setitem__,
                                                      unwrap_spec=[ 'self', ObjSpace, int, W_Root ]),
                             )

Token.typedef = TypeDef("Token", GrammarElement.typedef )
