

from grammar import BaseGrammarBuilder, AbstractContext
from pypy.interpreter.astcompiler import ast, consts
import pypy.interpreter.pyparser.pysymbol as sym
import pypy.interpreter.pyparser.pytoken as tok

## these tests should be methods of the ast objects
DEBUG_MODE = False

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
    elif len(L) == 2:
        arguments, stararg, dstararg = L[1].value
        builder.push(ast.CallFunc(L[0], arguments, stararg, dstararg))
    elif len(L) == 3:
        builder.push(ast.Power([L[0], L[2]]))
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


def build_binary_expr(builder, nb, OP):
    L = get_atoms(builder, nb)
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
    if l == 1:
        builder.push( L[0] )
        return
    else:
        # a < b < c is transalted into:
        # Compare(Name('a'), [('<', Name(b)), ('<', Name(c))])
        left_token = L[0]
        ops = []
        for i in range(1, l, 2):
            # if tok.name isn't in rpunct, then it should be
            # 'is', 'is not', 'not' or 'not in' => tok.value
            op_name = tok.tok_rpunct.get(L[i].name, L[i].value)
            ops.append((op_name, L[i+1]))
        builder.push(ast.Compare(L[0], ops))

def build_comp_op(builder, nb):
    """comp_op reducing has 2 different cases:
     1. There's only one token to reduce => nothing to
        do, just re-push it on the stack
     2. Two tokens to reduce => it's either 'not in' or 'is not',
        so we need to find out which one it is, and re-push a
        single token

    Note: reducing comp_op is needed because reducing comparison
          rules is much easier when we can assume the comparison
          operator is one and only one token on the stack (which
          is not the case, by default, with 'not in' and 'is not')
    """
    L = get_atoms(builder, nb)
    l = len(L)
    # l==1 means '<', '>', '<=', etc.
    if l == 1:
        builder.push(L[0])
    # l==2 means 'not in' or 'is not'
    elif l == 2:
        if L[0].value == 'not':
            builder.push(TokenObject(tok.NAME, 'not in', None))
        else:
            builder.push(TokenObject(tok.NAME, 'is not', None))
    else:
        assert False, "TODO" # uh ?
        
def build_and_test( builder, nb ):
    return build_binary_expr( builder, nb, ast.And )

def build_test( builder, nb ):
    return build_binary_expr( builder, nb, ast.Or)
    
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
        node = L[n]
        if isinstance(node, TokenObject) and node.name == tok.NEWLINE:
            nodes.append(ast.Discard(ast.Const(None)))
        else:
            nodes.append(node)
    builder.push( ast.Stmt(nodes) )

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

def build_varargslist(builder, nb):
    pass

def build_lambdef(builder, nb):
    L = get_atoms(builder, nb)
    code = L[-1]
    names, defaults, flags = parse_arglist(L[1:-2])
    builder.push(ast.Lambda(names, defaults, flags, code))


def build_trailer(builder, nb):
    """trailer: '(' ')' | '(' arglist ')' | '[' subscriptlist ']' | '.' NAME
    """
    L = get_atoms(builder, nb)
    # Case 1 : '(' ...
    if L[0].name == tok.LPAR:
        if len(L) == 2: # and L[1].token == tok.RPAR:
            builder.push(ArglistObject('arglist', ([], None, None), None))
        elif len(L) == 3: # '(' Arglist ')'
            # push arglist on the stack
            builder.push(L[1])
    else:
        assert False, "Trailer reducing implementation incomplete !"

def build_arglist(builder, nb):
    L = get_atoms(builder, nb)
    builder.push(ArglistObject('arglist', parse_argument(L), None))


def parse_argument(tokens):
    """parses function call arguments"""
    l = len(tokens)
    index = 0
    arguments = []
    last_token = None
    building_kw = False
    kw_built = False
    stararg_token = None
    dstararg_token = None
    while index < l:
        cur_token = tokens[index]
        index += 1
        if not isinstance(cur_token, TokenObject):
            if not building_kw:
                arguments.append(cur_token)
            elif kw_built:
                raise SyntaxError("non-keyword arg after keyword arg (%s)" % (cur_token))
            else:
                last_token = arguments.pop()
                assert isinstance(last_token, ast.Name) # used by rtyper
                arguments.append(ast.Keyword(last_token.name, cur_token))
                building_kw = False
                kw_built = True
        elif cur_token.name == tok.COMMA:
            continue
        elif cur_token.name == tok.EQUAL:
            building_kw = True
            continue
        elif cur_token.name == tok.STAR or cur_token.name == tok.DOUBLESTAR:
            if cur_token.name == tok.STAR:
                stararg_token = tokens[index]
                index += 1
                if index >= l:
                    break
                index += 2 # Skip COMMA and DOUBLESTAR
            dstararg_token = tokens[index]
            break
    return arguments, stararg_token, dstararg_token

def parse_arglist(tokens):
    """returns names, defaults, flags"""
    l = len(tokens)
    index = 0
    defaults = []
    names = []
    flags = 0
    while index < l:
        cur_token = tokens[index]
        index += 1
        if not isinstance(cur_token, TokenObject):
            # XXX: think of another way to write this test
            defaults.append(cur_token)
        elif cur_token.name == tok.COMMA:
            # We could skip test COMMA by incrementing index cleverly
            # but we might do some experiment on the grammar at some point
            continue
        elif cur_token.name == tok.STAR or cur_token.name == tok.DOUBLESTAR:
            if cur_token.name == tok.STAR:
                cur_token = tokens[index]
                index += 1
                if cur_token.name == tok.NAME:
                    names.append(cur_token.value)
                    flags |= consts.CO_VARARGS
                    index += 1
                    if index >= l:
                        break
                    else:
                        # still more tokens to read
                        cur_token = tokens[index]
                        index += 1
                else:
                    raise ValueError("FIXME: SyntaxError (incomplete varags) ?")
            if cur_token.name != tok.DOUBLESTAR:
                raise ValueError("Unexpected token: %s" % cur_token)
            cur_token = tokens[index]
            index += 1
            if cur_token.name == tok.NAME:
                names.append(cur_token.value)
                flags |= consts.CO_VARKEYWORDS
                index +=  1
            else:
                raise ValueError("FIXME: SyntaxError (incomplete varags) ?")
            if index < l:
                raise ValueError("unexpected token: %s" % tokens[index])
        elif cur_token.name == tok.NAME:
            names.append(cur_token.value)
    return names, defaults, flags


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
    sym.comp_op : build_comp_op,
    sym.and_test : build_and_test,
    sym.test : build_test,
    sym.testlist : build_testlist,
    sym.expr_stmt : build_expr_stmt,
    sym.small_stmt : return_one,
    sym.simple_stmt : build_simple_stmt,
    sym.single_input : build_single_input,
    sym.testlist_gexp : build_testlist_gexp,
    sym.lambdef : build_lambdef,
    sym.varargslist : build_varargslist,
    sym.trailer : build_trailer,
    sym.arglist : build_arglist,
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
        return "<Token: (%s,%s)>" % (tok.tok_rpunct.get(self.name,
                                                      tok.tok_name.get(self.name,str(self.name))),
                                   self.value)
    
    def __repr__(self):
        return "<Token: (%r,%s)>" % (tok.tok_rpunct.get(self.name,
                                                      tok.tok_name.get(self.name,str(self.name))),
                                   self.value)

class ArglistObject(ast.Node):
    """helper class to build function's arg list"""
    def __init__(self, name, value, src):
        self.name = name
        self.value = value
        self.count = 0
        self.line = 0 # src.getline()
        self.col = 0  # src.getcol()

    def __str__(self):
        return "<ArgList: (%s, %s, %s)>" % self.value
    
    def __repr__(self):
        return "<ArgList: (%s, %s, %s)>" % self.value
    

class AstBuilderContext(AbstractContext):
    """specific context management for AstBuidler"""
    def __init__(self, rule_stack):
        self.rule_stack = list(rule_stack)

class AstBuilder(BaseGrammarBuilder):
    """A builder that directly produce the AST"""

    def __init__( self, rules=None, debug=0 ):
        BaseGrammarBuilder.__init__(self, rules, debug )
        self.rule_stack = []

    def context(self):
        return AstBuilderContext(self.rule_stack)

    def restore(self, ctx):
        print "Restoring context (%s)" % (len(ctx.rule_stack))
        assert isinstance(ctx, AstBuilderContext)
        self.rule_stack = ctx.rule_stack

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
        rule_stack = self.rule_stack[:]
        if rule.is_root():
            print "ALT:", sym.sym_name[rule.codename], self.rule_stack
            F = ASTRULES.get(rule.codename)
            if F:
                # print "REDUCING ALTERNATIVE %s" % sym.sym_name[rule.codename]
                F( self, 1 )
            else:
                print "No reducing implementation for %s, just push it on stack" % (
                    sym.sym_name[rule.codename])
                self.push_rule( rule.codename, 1, source )
        else:
            self.push_rule( rule.codename, 1, source )
        if DEBUG_MODE:
            show_stack(rule_stack, self.rule_stack)
            x = raw_input("Continue ?")
        return True

    def sequence(self, rule, source, elts_number):
        """ """
        rule_stack = self.rule_stack[:]
        if rule.is_root():
            print "SEQ:", sym.sym_name[rule.codename]
            F = ASTRULES.get(rule.codename)
            if F:
                # print "REDUCING SEQUENCE %s" % sym.sym_name[rule.codename]
                F( self, elts_number )
            else:
                print "No reducing implementation for %s, just push it on stack" % (
                    sym.sym_name[rule.codename])
                self.push_rule( rule.codename, elts_number, source )
        else:
            self.push_rule( rule.codename, elts_number, source )
        if DEBUG_MODE:
            show_stack(rule_stack, self.rule_stack)
            x = raw_input("Continue ?")
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
        print "% 3d | %30s | %30s" % (i, obj1, obj2)
    
