

from grammar import BaseGrammarBuilder
from pypy.interpreter.astcompiler import ast, consts
import pypy.interpreter.pyparser.pysymbol as sym
import pypy.interpreter.pyparser.pytoken as tok

## these tests should be methods of the ast objects

def is_lvalue( ast_node ):
    return True

def to_lvalue( ast_node, OP ):
    if isinstance( ast_node, ast.Name ):
        return ast.AssName( ast_node.name, OP )
    elif isinstance(ast_node, ast.Tuple):
        nodes = []
        for node in ast_node.getChildren():
            nodes.append(ast.AssName(node.name, consts.OP_ASSIGN))
        return ast.AssTuple(nodes)
    else:
        assert False, "TODO"

def is_augassign( ast_node ):
    if ( isinstance( ast_node, ast.Name ) or
         isinstance( ast_node, ast.Slice ) or
         isinstance( ast_node, ast.Subscript ) or
         isinstance( ast_node, ast.Getattr ) ):
        return True
    return False

## building functions helpers
## --------------------------
##
## Naming convention:
## to provide a function handler for a grammar rule name yyy
## you should provide a build_yyy( builder, nb ) function
## where builder is the AstBuilder instance used to build the
## ast tree and nb is the number of items this rule is reducing
##
## Example:
## for example if the rule
##    term <- var ( '+' expr )*
## matches
##    x + (2*y) + z
## build_term will be called with nb == 2
## and get_atoms( builder, nb ) should return a list
## of 5 objects : Var TokenObject('+') Expr('2*y') TokenObject('+') Expr('z')
## where Var and Expr are AST subtrees and Token is a not yet
## reduced token
##
## AST_RULES is kept as a dictionnary to be rpython compliant this is the
## main reason why build_* functions are not methods of the AstBuilder class
##
def get_atoms( builder, nb ):
    L = []
    i = nb
    while i>0:
        obj = builder.pop()
        if isinstance(obj, RuleObject):
            i += obj.count
        else:
            L.append( obj )
        i -= 1
    L.reverse()
    return L
    
def build_single_input( builder, nb ):
    pass

def eval_number(value):
    """temporary implementation"""
    return eval(value)

def eval_string(value):
    """temporary implementation"""
    return eval(value)

def build_atom( builder, nb ):
    L = get_atoms( builder, nb )
    top = L[0]
    if isinstance(top, TokenObject):
        print "\t reducing atom (%s) (top.name) = %s" % (nb, top.name)
        if top.name == tok.LPAR:
            builder.push( L[1] )
        elif top.name == tok.LSQB:
            builder.push( ast.List( L[1].nodes, top.line) )
        elif top.name == tok.LBRACE:
            builder.push( ast.Dict( L[1:-1], top.line) )
        elif top.name == tok.NAME:
            builder.push( ast.Name(top.value) )
        elif top.name == tok.NUMBER:
            builder.push( ast.Const(eval_number(top.value)) )
        elif top.name == tok.STRING:
            # need to concatenate strings in L
            s = ''
            for token in L:
                s += eval_string(token.value)
            builder.push( ast.Const(s) )
            # assert False, "TODO (String)"
        else:
            raise ValueError, "unexpected tokens (%d): %s" % (nb,[ str(i) for i in L] )
            

def build_power( builder, nb ):
    L = get_atoms( builder, nb )
    if len(L) == 1:
        builder.push( L[0] )
    elif len(L) == 3:
        builder.push( ast.Power( [ L[0], L[2] ] ) )
    else:
        raise ValueError, "unexpected tokens: %s" % L

def build_factor( builder, nb ):
    L = get_atoms( builder, nb )
    if len(L) == 1:
        builder.push( L[0] )
    elif len(L) == 2 and isinstance(L[0],TokenObject):
        if L[0].name == tok.PLUS:
            builder.push( ast.UnaryAdd( L[1] ) )
        if L[0].name == tok.MINUS:
            builder.push( ast.UnarySub( L[1] ) )
        if L[0].name == tok.TILDE:
            builder.push( ast.Invert( L[1] ) )

def build_term( builder, nb ):
    L = get_atoms( builder, nb )
    l = len(L)
    left = L[0]
    for i in range(2,l,2):
        right = L[i]
        op = L[i-1].name
        if op == tok.STAR:
            left = ast.Mul( [ left, right ] )
        elif op == tok.SLASH:
            left = ast.Div( [ left, right ] )
        elif op == tok.PERCENT:
            left = ast.Mod( [ left, right ] )
        elif op == tok.DOUBLESLASH:
            left = ast.FloorDiv( [ left, right ] )
        else:
            raise ValueError, "unexpected token: %s" % L[i-1]
    builder.push( left )

def build_arith_expr( builder, nb ):
    L = get_atoms( builder, nb )
    l = len(L)
    left = L[0]
    for i in range(2,l,2):
        right = L[i]
        op = L[i-1].name
        if op == tok.PLUS:
            left = ast.Add( [ left, right ] )
        elif op == tok.MINUS:
            left = ast.Sub( [ left, right ] )
        else:
            raise ValueError, "unexpected token: %s : %s" % L[i-1]
    builder.push( left )

def build_shift_expr( builder, nb ):
    L = get_atoms( builder, nb )
    l = len(L)
    left = L[0]
    for i in range(2,l,2):
        right = L[i]
        op = L[i-1].name
        if op == tok.LEFTSHIFT:
            left = ast.LeftShift( [ left, right ] )
        elif op == tok.RIGHTSHIFT:
            left = ast.RightShift( [ left, right ] )
        else:
            raise ValueError, "unexpected token: %s : %s" % L[i-1]
    builder.push( left )


def build_binary_expr( builder, nb, OP ):
    L = get_atoms( builder, nb )
    l = len(L)
    if l==1:
        builder.push( L[0] )
        return
    items = []
    for i in range(0,l,2): # this is L not 1
        items.append( L[i] )
    builder.push( OP( items ) )
    return

def build_and_expr( builder, nb ):
    return build_binary_expr( builder, nb, ast.Bitand )

def build_xor_expr( builder, nb ):
    return build_binary_expr( builder, nb, ast.Bitxor )

def build_expr( builder, nb ):
    return build_binary_expr( builder, nb, ast.Bitor )

def build_comparison( builder, nb ):
    L = get_atoms( builder, nb )
    l = len(L)
    if l==1:
        builder.push( L[0] )
        return
    # TODO
    assert False

def build_and_test( builder, nb ):
    return build_binary_expr( builder, nb, ast.And )

def build_test( builder, nb ):
    return build_binary_expr( builder, nb, ast.Or )

def build_testlist( builder, nb ):
    return build_binary_expr( builder, nb, ast.Tuple )

def build_not_test( builder, nb ):
    L = get_atoms( builder, nb )
    l = len(L)
    if l==1:
        builder.push( L[0] )
        return

def build_expr_stmt( builder, nb ):
    L = get_atoms( builder, nb )
    l = len(L)
    if l==1:
        builder.push( ast.Discard( L[0] ) )
        return
    op = L[1]
    if op.name == tok.EQUAL:
        nodes = []
        for i in range(0,l-2,2):
            lvalue = to_lvalue( L[i], consts.OP_ASSIGN )
            nodes.append( lvalue )
        rvalue = L[-1]
        builder.push( ast.Assign( nodes, rvalue ) )
        pass
    else:
        assert l==3
        lvalue = L[0]
        assert is_augassign( lvalue )
        builder.push( ast.AugAssign( lvalue, op, L[2] ) )

def return_one( builder, nb ):
    L = get_atoms( builder, nb )
    l = len(L)
    if l==1:
        builder.push( L[0] )
        return
    raise WalkerError("missing one node in stack")

def build_simple_stmt( builder, nb ):
    L = get_atoms( builder, nb )
    l = len(L)
    nodes = []
    for n in range(0,l,2):
        nodes.append(L[n])
    builder.push( ast.Stmt(nodes) )
    return

def build_single_input( builder, nb ):
    L = get_atoms( builder, nb )
    l = len(L)
    if l >= 1:
        builder.push(ast.Module(None, L[0]))
        return
    raise WalkerError("error")
    
def build_testlist_gexp(builder, nb):
    L = get_atoms(builder, nb)
    l = len(L)
    if l == 1:
        builder.push(L[0])
        return
    items = []
    if L[1].name == tok.COMMA:
        for i in range(0, l, 2): # this is L not 1
            items.append(L[i])
    else:
        # genfor
        assert False, "TODO"
    builder.push( Tuple( items ) )
    return

ASTRULES = {
#    "single_input" : build_single_input,
    sym.atom : build_atom,
    sym.power : build_power,
    sym.factor : build_factor,
    sym.term : build_term,
    sym.arith_expr : build_arith_expr,
    sym.shift_expr : build_shift_expr,
    sym.and_expr : build_and_expr,
    sym.xor_expr : build_xor_expr,
    sym.expr : build_expr,
    sym.comparison : build_comparison,
    sym.and_test : build_and_test,
    sym.test : build_test,
    sym.testlist : build_testlist,
    sym.expr_stmt : build_expr_stmt,
    sym.small_stmt : return_one,
    sym.simple_stmt : build_simple_stmt,
    sym.single_input : build_single_input,
    sym.testlist_gexp : build_testlist_gexp,
    }

class RuleObject(ast.Node):
    """A simple object used to wrap a rule or token"""
    def __init__(self, name, count, src ):
        self.name = name
        self.count = count
        self.line = 0 # src.getline()
        self.col = 0  # src.getcol()

    def __str__(self):
        return "<Rule: %s/%d>" % (sym.sym_name[self.name], self.count)

    def __repr__(self):
        return "<Rule: %s/%d>" % (sym.sym_name[self.name], self.count)

class TokenObject(ast.Node):
    """A simple object used to wrap a rule or token"""
    def __init__(self, name, value, src ):
        self.name = name
        self.value = value
        self.count = 0
        self.line = 0 # src.getline()
        self.col = 0  # src.getcol()

    def __str__(self):
        return "<Token: %s=%s>" % (tok.tok_rpunct.get(self.name,
                                                      tok.tok_name.get(self.name,str(self.name))),
                                   self.value)
    
    def __repr__(self):
        return "<Token: %r=%s>" % (tok.tok_rpunct.get(self.name,
                                                      tok.tok_name.get(self.name,str(self.name))),
                                   self.value)
    
class AstBuilder(BaseGrammarBuilder):
    """A builder that directly produce the AST"""

    def __init__( self, rules=None, debug=0 ):
        BaseGrammarBuilder.__init__(self, rules, debug )
        self.rule_stack = []

    def pop(self):
        return self.rule_stack.pop(-1)

    def push(self, obj):
        self.rule_stack.append( obj )
        if not isinstance(obj, RuleObject) and not isinstance(obj, TokenObject):
            print "Pushed:", str(obj), len(self.rule_stack)
        # print "\t", self.rule_stack

    def push_tok(self, name, value, src ):
        self.push( TokenObject( name, value, src ) )

    def push_rule(self, name, count, src ):
        self.push( RuleObject( name, count, src ) )

    def alternative( self, rule, source ):
        # Do nothing, keep rule on top of the stack
        if rule.is_root():
            print "ALT:", sym.sym_name[rule.codename], self.rule_stack
            F = ASTRULES.get(rule.codename)
            if F:
                # print "REDUCING ALTERNATIVE %s" % sym.sym_name[rule.codename]
                F( self, 1 )
        else:
            self.push_rule( rule.codename, 1, source )
        return True

    def sequence(self, rule, source, elts_number):
        """ """
        if rule.is_root():
            print "SEQ:", sym.sym_name[rule.codename]
            F = ASTRULES.get(rule.codename)
            if F:
                # print "REDUCING SEQUENCE %s" % sym.sym_name[rule.codename]
                F( self, elts_number )
            else:
                self.push_rule( rule.codename, elts_number, source )
        else:
            self.push_rule( rule.codename, elts_number, source )
        return True

    def token(self, name, value, source):
        print "TOK:", tok.tok_name[name], name, value
        self.push_tok( name, value, source )
        return True

def show_stack(before, after):
    L1 = len(before)
    L2 = len(after)
    for i in range(max(L1,L2)):
        if i<L1:
            obj1 = str(before[i])
        else:
            obj1 = "-"
        if i<L2:
            obj2 = str(after[i])
        else:
            obj2 = "-"
        print "% 3d | %30s | %30s"
    
