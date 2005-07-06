

from grammar import BaseGrammarBuilder
import pypy.interpreter.astcompiler.ast as ast

def get_atoms( builder, nb ):
    L = []
    i = nb
    while i>0:
        obj = builder.pop()
        if isinstance(obj,RuleObject):
            i+=obj.count
        else:
            L.append( obj )
        i -= 1
    L.reverse()
    return L
    

def build_single_input( builder, nb ):
    pass

def build_atom( builder, nb ):
    L = get_atoms( builder, nb )
    top = L[0]
    if isinstance(top, TokenObject):
        if top.name == "(":
            builder. ast.Tuple(L[1:-1], top.line)
        elif top.name == "[":
            builder.push( ast.List( L[1:-1], top.line) )
        elif top.name == "{":
            builder.push( ast.Dict( L[1:-1], top.line) )
        elif top.name == "NAME":
            builder.push( ast.Name(top.value) )
        elif top.name == "NUMBER":
            builder.push( ast.Const(eval(top.value)) )
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
        if L[0].name == "+":
            builder.push( ast.UnaryAdd( L[1] ) )
        if L[0].name == "-":
            builder.push( ast.UnarySub( L[1] ) )
        if L[0].name == "~":
            builder.push( ast.Invert( L[1] ) )

def build_term( builder, nb ):
    L = get_atoms( builder, nb )
    l = len(L)
    left = L[0]
    for i in range(2,l,2):
        right = L[i]
        op = L[i-1].name
        if op == "*":
            left = ast.Mul( [ left, right ] )
        elif op == "/":
            left = ast.Div( [ left, right ] )
        elif op == "%":
            left = ast.Mod( [ left, right ] )
        elif op == "//":
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
        if op == "+":
            left = ast.Add( [ left, right ] )
        elif op == "-":
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
        if op == "<<":
            left = ast.LeftShift( [ left, right ] )
        elif op == ">>":
            left = ast.RightShift( [ left, right ] )
        else:
            raise ValueError, "unexpected token: %s : %s" % L[i-1]
    builder.push( left )

    
ASTRULES = {
#    "single_input" : build_single_input,
    "atom" : build_atom,
    "power" : build_power,
    "factor" : build_factor,
    "term" : build_term,
    "arith_expr" : build_arith_expr,
    "shift_expr" : build_shift_expr,
    }

class RuleObject(ast.Node):
    """A simple object used to wrap a rule or token"""
    def __init__(self, name, count, src ):
        self.name = name
        self.count = count
        self.line = 0 # src.getline()
        self.col = 0  # src.getcol()

    def __str__(self):
        return "<Rule: %s>" % (self.name,)

class TokenObject(ast.Node):
    """A simple object used to wrap a rule or token"""
    def __init__(self, name, value, src ):
        self.name = name
        self.value = value
        self.count = 0
        self.line = 0 # src.getline()
        self.col = 0  # src.getcol()

    def __str__(self):
        return "<Token: %s=%s>" % (self.name, self.value)
    
class AstBuilder(BaseGrammarBuilder):
    """A builder that directly produce the AST"""

    def __init__( self, rules=None, debug=0 ):
        BaseGrammarBuilder.__init__(self, rules, debug )
        self.rule_stack = []

    def pop(self):
        return self.rule_stack.pop(-1)

    def push(self, obj):
        if not isinstance(obj, RuleObject) and not isinstance(obj, TokenObject):
            print "Pushed:", str(obj), len(self.rule_stack)
        self.rule_stack.append( obj )

    def push_tok(self, name, value, src ):
        self.push( TokenObject( name, value, src ) )

    def push_rule(self, name, count, src ):
        self.push( RuleObject( name, count, src ) )

    def alternative( self, rule, source ):
        # Do nothing, keep rule on top of the stack
        if rule.is_root():
            print "ALT:",rule.name
            F = ASTRULES.get(rule.name)
            if F:
                F( self, 1 )
        else:
            self.push_rule( rule.name, 1, source )
        return True

    def sequence(self, rule, source, elts_number):
        """ """
        if rule.is_root():
            print "SEQ:", rule.name
            F = ASTRULES.get(rule.name)
            if F:
                F( self, elts_number )
        else:
            self.push_rule( rule.name, elts_number, source )
        return True

    def token(self, name, value, source):
        print "TOK:", name, value
        self.push_tok( name, value, source )
        return True
