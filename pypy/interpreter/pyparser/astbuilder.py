

from grammar import BaseGrammarBuilder, AbstractContext
from pypy.interpreter.astcompiler import ast, consts
from pypy.interpreter.astcompiler.transformer import WalkerError
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
    
def eval_number(value):
    """temporary implementation"""
    return eval(value)

def eval_string(value):
    """temporary implementation"""
    return eval(value)

def build_atom(builder, nb):
    L = get_atoms( builder, nb )
    top = L[0]
    if isinstance(top, TokenObject):
        print "\t reducing atom (%s) (top.name) = %s" % (nb, top.name)
        if top.name == tok.LPAR:
            builder.push( L[1] )
        elif top.name == tok.LSQB:
            if len(L) == 2:
                builder.push(ast.List([], top.line))
            else:
                list_node = L[1]
                # XXX lineno is not on *every* child class of ast.Node
                #     (will probably crash the annotator, but should be
                #      easily fixed)
                list_node.lineno = top.line
                builder.push(list_node)
        elif top.name == tok.LBRACE:
            items = []
            for index in range(1, len(L)-1, 4):
                # a   :   b   ,   c : d
                # ^  +1  +2  +3  +4
                items.append((L[index], L[index+2]))
            builder.push(ast.Dict(items, top.line))
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
            

def build_power(builder, nb):
    L = get_atoms(builder, nb)
    if len(L) == 1:
        builder.push( L[0] )
    elif len(L) == 2:
        arguments, stararg, dstararg = L[1].value
        builder.push(ast.CallFunc(L[0], arguments, stararg, dstararg))
    elif len(L) == 3:
        if isinstance(L[1], TokenObject) and L[1].name == tok.DOT:
            builder.push(ast.Getattr(L[0], L[2].value))
        else:
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
    return build_binary_expr(builder, nb, ast.Or)
    
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
        builder.push( ast.AugAssign( lvalue, op.get_name(), L[2] ) )

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
    builder.push(ast.Stmt(nodes))

def build_return_stmt(builder, nb):
    L = get_atoms(builder, nb)
    if len(L) > 2:
        assert False, "return several stmts not implemented"
    elif len(L) == 1:
        builder.push(ast.Return(Const(None), None)) # XXX lineno
    else:
        builder.push(ast.Return(L[1], None)) # XXX lineno

def build_file_input(builder, nb):
    # FIXME: need to handle docstring !
    doc = None
    # doc = self.get_docstring(nodelist, symbol.file_input)
    # if doc is not None:
    #     i = 1
    # else:
    #     i = 0
    stmts = []
    L = get_atoms(builder, nb)
    for node in L:
        if isinstance(node, ast.Stmt):
            stmts.extend(node.nodes)
        elif isinstance(node, TokenObject) and node.name == tok.ENDMARKER:
            # XXX Can't we just remove the last element of the list ?
            break    
        elif isinstance(node, TokenObject) and node.name == tok.NEWLINE:
            continue
        else:
            stmts.append(node)
    return builder.push(ast.Module(doc, ast.Stmt(stmts)))

def build_single_input( builder, nb ):
    L = get_atoms( builder, nb )
    l = len(L)
    if l >= 1:
        builder.push(ast.Module(None, L[0]))
    else:
        assert False, "Forbidden path"

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
        # genfor: 'i for i in j'
        # GenExpr(GenExprInner(Name('i'), [GenExprFor(AssName('i', 'OP_ASSIGN'), Name('j'), [])])))]))
        expr = L[0]
        genexpr_for = parse_genexpr_for(L[1:])
        builder.push(ast.GenExpr(ast.GenExprInner(expr, genexpr_for)))
        return
    builder.push(ast.Tuple(items))
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
    elif len(L) == 2:
        # Attribute access: '.' NAME
        # XXX Warning: fails if trailer is used in lvalue
        builder.push(L[0])
        builder.push(L[1])
        builder.push(TempRuleObject('pending-attr-access', 2, None))
    else:
        assert False, "Trailer reducing implementation incomplete !"

def build_arglist(builder, nb):
    L = get_atoms(builder, nb)
    builder.push(ArglistObject('arglist', parse_argument(L), None))


def build_listmaker(builder, nb):
    """listmaker: test ( list_for | (',' test)* [','] )"""
    L = get_atoms(builder, nb)
    if len(L) >= 2 and isinstance(L[1], TokenObject) and L[1].value == 'for':
        # list comp
        expr = L[0]
        list_for = parse_listcomp(L[1:])
        builder.push(ast.ListComp(expr, list_for))
    else:
        # regular list building (like in [1, 2, 3,])
        index = 0
        nodes = []
        while index < len(L):
            nodes.append(L[index])
            index += 2 # skip comas
        builder.push(ast.List(nodes))
    

def build_funcdef(builder, nb):
    """funcdef: [decorators] 'def' NAME parameters ':' suite
    """
    L = get_atoms(builder, nb)
    funcname = L[1]
    arglist = []
    index = 3
    while not (isinstance(L[index], TokenObject) and L[index].name == tok.RPAR):
        arglist.append(L[index])
        index += 1
    names, default, flags = parse_arglist(arglist)
    funcname = L[1].value
    arglist = L[2]
    code = L[-1]
    # FIXME: decorators and docstring !
    builder.push(ast.Function(None, funcname, names, default, flags, None, code))
        

def build_suite(builder, nb):
    """suite: simple_stmt | NEWLINE INDENT stmt+ DEDENT"""
    L = get_atoms(builder, nb)
    if len(L) == 1:
        builder.push(L[0])
    elif len(L) == 4:
        # Only one statement for (stmt+)
        stmt = L[2]
        if not isinstance(stmt, ast.Stmt):
            stmt = ast.Stmt([stmt])
        builder.push(stmt)
    else:
        # several statements
        stmts = []
        nodes = L[2:-1]
        for node in nodes:
            if isinstance(node, ast.Stmt):
                stmts.extend(node.nodes)
            else:
                stmts.append(node)
        builder.push(ast.Stmt(stmts))


def build_if_stmt(builder, nb):
    L = get_atoms(builder, nb)
    tests = []
    tests.append((L[1], L[3]))
    index = 4
    else_ = None
    while index < len(L):
        cur_token = L[index]
        assert isinstance(cur_token, TokenObject) # rtyper
        if cur_token.value == 'elif':
            tests.append((L[index+1], L[index+3]))
            index += 4
        else: # cur_token.value == 'else'
            else_ = L[index+2]
            break # break is not necessary
    builder.push(ast.If(tests, else_))

def build_pass_stmt(builder, nb):
    """past_stmt: 'pass'"""
    L = get_atoms(builder, nb)
    assert len(L) == 1
    builder.push(ast.Pass())


def build_break_stmt(builder, nb):
    """past_stmt: 'pass'"""
    L = get_atoms(builder, nb)
    assert len(L) == 1
    builder.push(ast.Break())


def build_for_stmt(builder, nb):
    """for_stmt: 'for' exprlist 'in' testlist ':' suite ['else' ':' suite]"""
    L = get_atoms(builder, nb)
    else_ = None
    # skip 'for'
    assign = to_lvalue(L[1], consts.OP_ASSIGN)
    # skip 'in'
    iterable = L[3]
    # skip ':'
    body = L[5]
    # if there is a "else" statement
    if len(L) > 6:
        # skip 'else' and ':'
        else_ = L[8]
    builder.push(ast.For(assign, iterable, body, else_))


def build_while_stmt(builder, nb):
    """while_stmt: 'while' test ':' suite ['else' ':' suite]"""
    L = get_atoms(builder, nb)
    else_ = None
    # skip 'while'
    test =  L[1]
    # skip ':'
    body = L[3]
    # if there is a "else" statement
    if len(L) > 4:
        # skip 'else' and ':'
        else_ = L[6]
    builder.push(ast.While(test, body, else_))


def build_import_name(builder, nb):
    """import_name: 'import' dotted_as_names

    dotted_as_names: dotted_as_name (',' dotted_as_name)*
    dotted_as_name: dotted_name [NAME NAME]
    dotted_name: NAME ('.' NAME)*

    written in an unfolded way:
    'import' NAME(.NAME)* [NAME NAME], (NAME(.NAME)* [NAME NAME],)*

    XXX: refactor build_import_name and build_import_from
    """
    L = get_atoms(builder, nb)
    index = 1 # skip 'import'
    l = len(L)
    names = []
    while index < l:
        as_name = None
        # dotted name (a.b.c)
        incr, name = parse_dotted_names(L[index:])
        index += incr
        # 'as' value
        if index < l and L[index].value == 'as':
            as_name = L[index+1].value
            index += 2
        names.append((name, as_name))
        # move forward until next ','
        while index < l and L[index].name != tok.COMMA:
            index += 1
        index += 1
    builder.push(ast.Import(names))


def build_import_from(builder, nb):
    """
    import_from: 'from' dotted_name 'import' ('*' | '(' import_as_names ')' | import_as_names)

    import_as_names: import_as_name (',' import_as_name)* [',']
    import_as_name: NAME [NAME NAME]
    """
    L = get_atoms(builder, nb)
    index = 1
    incr, from_name = parse_dotted_names(L[index:])
    index += (incr + 1) # skip 'import'
    if L[index].name == tok.STAR:
        names = [('*', None)]
    else:
        if L[index].name == tok.LPAR:
            # mutli-line imports
            tokens = L[index+1:-1]
        else:
            tokens = L[index:]
        index = 0
        l = len(tokens)
        names = []
        while index < l:
            name = tokens[index].value
            as_name = None
            index += 1
            if index < l:
                if tokens[index].value == 'as':
                    as_name = tokens[index+1].value
                    index += 2
            names.append((name, as_name))
            if index < l: # case ','
                index += 1
    builder.push(ast.From(from_name, names))


def build_yield_stmt(builder, nb):
    L = get_atoms(builder, nb)
    builder.push(ast.Yield(L[1]))

def build_continue_stmt(builder, nb):
    L = get_atoms(builder, nb)
    builder.push(ast.Continue())

def build_del_stmt(builder, nb):
    L = get_atoms(builder, nb)
    assert isinstance(L[1], ast.Name), "build_del_stmt implementation is incomplete !"
    builder.push(ast.AssName(L[1].name, consts.OP_DELETE))

def build_assert_stmt(builder, nb):
    """assert_stmt: 'assert' test [',' test]"""
    L = get_atoms(builder, nb)
    test = L[1]
    if len(L) == 4:
        fail = L[3]
    else:
        fail = None
    builder.push(ast.Assert(test, fail))

def build_exec_stmt(builder, nb):
    """exec_stmt: 'exec' expr ['in' test [',' test]]"""
    L = get_atoms(builder, nb)
    expr = L[1]
    loc = None
    glob = None
    if len(L) > 2:
        loc = L[3]
        if len(L) > 4:
            glob = L[5]
    builder.push(ast.Exec(expr, loc, glob))

def build_print_stmt(builder, nb):
    """
    print_stmt: 'print' ( '>>' test [ (',' test)+ [','] ] | [ test (',' test)* [','] ] )
    """
    L = get_atoms(builder, nb)
    l = len(L)
    items = []
    dest = None
    start = 1
    if l > 1:
        if isinstance(L[1], TokenObject) and L[1].name == tok.RIGHTSHIFT:
            dest = L[2]
            # skip following comma
            start = 4
    for index in range(start, l, 2):
        items.append(L[index])
    if isinstance(L[-1], TokenObject) and L[-1].name == tok.COMMA:
        builder.push(ast.Print(items, dest))
    else:
        builder.push(ast.Printnl(items, dest))

def build_global_stmt(builder, nb):
    """global_stmt: 'global' NAME (',' NAME)*"""
    L = get_atoms(builder, nb)
    names = []
    for index in range(1, len(L), 2):
        token = L[index]
        assert isinstance(token, TokenObject)
        names.append(token.value)
    builder.push(ast.Global(names))

def parse_dotted_names(tokens):
    """parses NAME('.' NAME)* and returns full dotted name

    this function doesn't assume that the <tokens> list ends after the
    last 'NAME' element
    """
    name = tokens[0].value
    l = len(tokens)
    index = 1
    for index in range(1, l, 2):
        token = tokens[index]
        assert isinstance(token, TokenObject)
        if token.name != tok.DOT:
            break
        name = name + '.' + tokens[index+1].value
    return (index, name)

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


def parse_listcomp(tokens):
    """parses 'for j in k for i in j if i %2 == 0' and returns
    a GenExprFor instance
    XXX: refactor with listmaker ?
    """
    list_fors = []
    ifs = []
    index = 0
    while index < len(tokens):
        if tokens[index].value == 'for':
            index += 1 # skip 'for'
            ass_node = to_lvalue(tokens[index], consts.OP_ASSIGN)
            index += 2 # skip 'in'
            iterable = tokens[index]
            index += 1
            while index < len(tokens) and tokens[index].value == 'if':
                ifs.append(ast.ListCompIf(tokens[index+1]))
                index += 2
            list_fors.append(ast.ListCompFor(ass_node, iterable, ifs))
            ifs = []
        else:
            raise ValueError('Unexpected token: %s' % tokens[index])
    return list_fors


def parse_genexpr_for(tokens):
    """parses 'for j in k for i in j if i %2 == 0' and returns
    a GenExprFor instance
    XXX: if RPYTHON supports to pass a class object to a function,
         we could refactor parse_listcomp and parse_genexpr_for,
         and call :
           - parse_listcomp(tokens, forclass=ast.GenExprFor, ifclass=...)
         or:
           - parse_listcomp(tokens, forclass=ast.ListCompFor, ifclass=...)
    """
    genexpr_fors = []
    ifs = []
    index = 0
    while index < len(tokens):
        if tokens[index].value == 'for':
            index += 1 # skip 'for'
            ass_node = to_lvalue(tokens[index], consts.OP_ASSIGN)
            index += 2 # skip 'in'
            iterable = tokens[index]
            index += 1
            while index < len(tokens) and tokens[index].value == 'if':
                ifs.append(ast.GenExprIf(tokens[index+1]))
                index += 2
            genexpr_fors.append(ast.GenExprFor(ass_node, iterable, ifs))
            ifs = []
        else:
            raise ValueError('Unexpected token: %s' % tokens[index])
    return genexpr_fors


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
    sym.file_input : build_file_input,
    sym.testlist_gexp : build_testlist_gexp,
    sym.lambdef : build_lambdef,
    sym.varargslist : build_varargslist,
    sym.trailer : build_trailer,
    sym.arglist : build_arglist,
    sym.listmaker : build_listmaker,
    sym.funcdef : build_funcdef,
    sym.return_stmt : build_return_stmt,
    sym.suite : build_suite,
    sym.if_stmt : build_if_stmt,
    sym.pass_stmt : build_pass_stmt,
    sym.break_stmt : build_break_stmt,
    sym.for_stmt : build_for_stmt,
    sym.while_stmt : build_while_stmt,
    sym.import_name : build_import_name,
    sym.import_from : build_import_from,
    sym.yield_stmt : build_yield_stmt,
    sym.continue_stmt : build_continue_stmt,
    sym.del_stmt : build_del_stmt,
    sym.assert_stmt : build_assert_stmt,
    sym.exec_stmt : build_exec_stmt,
    sym.print_stmt : build_print_stmt,
    sym.global_stmt : build_global_stmt,
    # sym.parameters : build_parameters,
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


class TempRuleObject(RuleObject):
    """used to keep track of how many items get_atom() should pop"""
    def __str__(self):
        return "<Rule: %s/%d>" % (self.name, self.count)

    def __repr__(self):
        return "<Rule: %s/%d>" % (self.name, self.count)

    
class TokenObject(ast.Node):
    """A simple object used to wrap a rule or token"""
    def __init__(self, name, value, src ):
        self.name = name
        self.value = value
        self.count = 0
        self.line = 0 # src.getline()
        self.col = 0  # src.getcol()

    def get_name(self):
        return tok.tok_rpunct.get(self.name, tok.tok_name.get(self.name,str(self.name)))
        
    def __str__(self):
        return "<Token: (%s,%s)>" % (self.get_name(), self.value)
    
    def __repr__(self):
        return "<Token: (%r,%s)>" % (self.get_name(), self.value)


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
        elif isinstance(obj, TempRuleObject):
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
    
