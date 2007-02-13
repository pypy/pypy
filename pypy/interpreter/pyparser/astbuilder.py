"""This module provides the astbuilder class which is to be used
by GrammarElements to directly build the AST during parsing
without going through the nested tuples step
"""

from grammar import BaseGrammarBuilder, AbstractContext
from pypy.interpreter.astcompiler import ast, consts
from pypy.interpreter.pyparser import pythonparse
import pypy.interpreter.pyparser.pytoken as tok
from pypy.interpreter.pyparser.error import SyntaxError
from pypy.interpreter.pyparser.parsestring import parsestr

sym      = pythonparse.PYTHON_PARSER.symbols

DEBUG_MODE = 0

### Parsing utilites #################################################
def parse_except_clause(tokens):
    """parses 'except' [test [',' test]] ':' suite
    and returns a 4-tuple : (tokens_read, expr1, expr2, except_body)
    """
    lineno = tokens[0].lineno
    clause_length = 1
    # Read until end of except clause (bound by following 'else',
    # or 'except' or end of tokens)
    while clause_length < len(tokens):
        token = tokens[clause_length]
        if isinstance(token, TokenObject) and \
           (token.get_value() == 'except' or token.get_value() == 'else'):
            break
        clause_length += 1
    if clause_length == 3:
        # case 'except: body'
        return (3, None, None, tokens[2])
    elif clause_length == 4:
        # case 'except Exception: body':
        return (4, tokens[1], None, tokens[3])
    else:
        # case 'except Exception, exc: body'
        return (6, tokens[1], to_lvalue(tokens[3], consts.OP_ASSIGN), tokens[5])


def parse_dotted_names(tokens):
    """parses NAME('.' NAME)* and returns full dotted name

    this function doesn't assume that the <tokens> list ends after the
    last 'NAME' element
    """
    first = tokens[0]
    assert isinstance(first, TokenObject)
    name = first.get_value()
    l = len(tokens)
    index = 1
    for index in range(1, l, 2):
        token = tokens[index]
        assert isinstance(token, TokenObject)
        if token.name != tok.DOT:
            break
        token = tokens[index+1]
        assert isinstance(token, TokenObject)
        name += '.'
        value = token.get_value()
        name += value
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
        if not isinstance(cur_token, TokenObject):
            index += 1
            if not building_kw:
                arguments.append(cur_token)
            else:
                last_token = arguments.pop()
                assert isinstance(last_token, ast.Name) # used by rtyper
                arguments.append(ast.Keyword(last_token.varname, cur_token, last_token.lineno))
                building_kw = False
                kw_built = True
            continue
        elif cur_token.name == tok.COMMA:
            index += 1
            continue
        elif cur_token.name == tok.EQUAL:
            index += 1
            building_kw = True
            continue
        elif cur_token.name == tok.STAR or cur_token.name == tok.DOUBLESTAR:
            index += 1
            if cur_token.name == tok.STAR:
                stararg_token = tokens[index]
                index += 1
                if index >= l:
                    break
                index += 2 # Skip COMMA and DOUBLESTAR
            dstararg_token = tokens[index]
            break
        elif cur_token.get_value() == 'for':
            if len(arguments) != 1:
                raise SyntaxError("invalid syntax", cur_token.lineno,
                                  cur_token.col)
            expr = arguments[0]
            genexpr_for = parse_genexpr_for(tokens[index:])
            genexpr_for[0].is_outmost = True
            gexp = ast.GenExpr(ast.GenExprInner(expr, genexpr_for, expr.lineno), expr.lineno)
            arguments[0] = gexp
            break
    return arguments, stararg_token, dstararg_token


def parse_fpdef(tokens, index):
    """fpdef: fpdef: NAME | '(' fplist ')'
    fplist: fpdef (',' fpdef)* [',']

    This intend to be a RPYTHON compliant implementation of _parse_fpdef,
    but it can't work with the default compiler.
    We switched to use astcompiler module now
    """
    nodes = []
    comma = False
    while True:
        token = tokens[index]
        index += 1
        assert isinstance(token, TokenObject)
        if token.name == tok.LPAR:       # nested item
            index, node = parse_fpdef(tokens, index)
        elif token.name == tok.RPAR:     # end of current nesting
            break
        else:                            # name
            val = token.get_value()
            node = ast.AssName(val, consts.OP_ASSIGN, token.lineno)
        nodes.append(node)

        token = tokens[index]
        index += 1
        assert isinstance(token, TokenObject)
        if token.name == tok.COMMA:
            comma = True
        else:
            assert token.name == tok.RPAR
            break
    if len(nodes) == 1 and not comma:
        node = nodes[0]
    else:
        node = ast.AssTuple(nodes, token.lineno)
    return index, node

def parse_arglist(tokens):
    """returns names, defaults, flags"""
    l = len(tokens)
    index = 0
    defaults = []
    names = []
    flags = 0
    first_with_default = -1
    while index < l:
        cur_token = tokens[index]
        index += 1
        if not isinstance(cur_token, TokenObject):
            # XXX: think of another way to write this test
            defaults.append(cur_token)
            if first_with_default == -1:
                first_with_default = len(names) - 1
        elif cur_token.name == tok.COMMA:
            # We could skip test COMMA by incrementing index cleverly
            # but we might do some experiment on the grammar at some point
            continue
        elif cur_token.name == tok.LPAR:
            index, node = parse_fpdef(tokens, index)
            names.append(node)
        elif cur_token.name == tok.STAR or cur_token.name == tok.DOUBLESTAR:
            if cur_token.name == tok.STAR:
                cur_token = tokens[index]
                assert isinstance(cur_token, TokenObject)
                index += 1
                if cur_token.name == tok.NAME:
                    val = cur_token.get_value()
                    names.append( ast.AssName( val, consts.OP_ASSIGN ) )
                    flags |= consts.CO_VARARGS
                    index += 1
                    if index >= l:
                        break
                    else:
                        # still more tokens to read
                        cur_token = tokens[index]
                        index += 1
                else:
                    raise SyntaxError("incomplete varags", cur_token.lineno,
                                      cur_token.col)
            assert isinstance(cur_token, TokenObject)
            if cur_token.name != tok.DOUBLESTAR:
                raise SyntaxError("Unexpected token", cur_token.lineno,
                                  cur_token.col)
            cur_token = tokens[index]
            index += 1
            assert isinstance(cur_token, TokenObject)
            if cur_token.name == tok.NAME:
                val = cur_token.get_value()
                names.append( ast.AssName( val, consts.OP_ASSIGN ) )
                flags |= consts.CO_VARKEYWORDS
                index +=  1
            else:
                raise SyntaxError("incomplete varags", cur_token.lineno,
                                  cur_token.col)
            if index < l:
                token = tokens[index]
                raise SyntaxError("unexpected token" , token.lineno,
                                  token.col)
        elif cur_token.name == tok.NAME:
            val = cur_token.get_value()
            names.append( ast.AssName( val, consts.OP_ASSIGN ) )

    if first_with_default != -1:
        num_expected_with_default = len(names) - first_with_default
        if flags & consts.CO_VARKEYWORDS:
            num_expected_with_default -= 1
        if flags & consts.CO_VARARGS:
            num_expected_with_default -= 1
        if len(defaults) != num_expected_with_default:
            raise SyntaxError('non-default argument follows default argument',
                              tokens[0].lineno, tokens[0].col)
    return names, defaults, flags


def parse_listcomp(tokens):
    """parses 'for j in k for i in j if i %2 == 0' and returns
    a GenExprFor instance
    XXX: refactor with listmaker ?
    """
    list_fors = []
    ifs = []
    index = 0
    if tokens:
        lineno = tokens[0].lineno
    else:
        lineno = -1
    while index < len(tokens):
        token = tokens[index]
        assert isinstance(token, TokenObject) # rtyper info + check
        if token.get_value() == 'for':
            index += 1 # skip 'for'
            ass_node = to_lvalue(tokens[index], consts.OP_ASSIGN)
            index += 2 # skip 'in'
            iterables = [tokens[index]]
            index += 1
            while index < len(tokens):
                tok2 = tokens[index]
                if not isinstance(tok2, TokenObject):
                    break
                if tok2.name != tok.COMMA:
                    break
                iterables.append(tokens[index+1])
                index += 2
            if len(iterables) == 1:
                iterable = iterables[0]
            else:
                iterable = ast.Tuple(iterables, token.lineno)
            while index < len(tokens):
                token = tokens[index]
                assert isinstance(token, TokenObject) # rtyper info
                if token.get_value() == 'if':
                    ifs.append(ast.ListCompIf(tokens[index+1], token.lineno))
                    index += 2
                else:
                    break
            list_fors.append(ast.ListCompFor(ass_node, iterable, ifs, lineno))
            ifs = []
        else:
            assert False, 'Unexpected token: expecting for in listcomp'
        #
        # Original implementation:
        #
        # if tokens[index].get_value() == 'for':
        #     index += 1 # skip 'for'
        #     ass_node = to_lvalue(tokens[index], consts.OP_ASSIGN)
        #     index += 2 # skip 'in'
        #     iterable = tokens[index]
        #     index += 1
        #     while index < len(tokens) and tokens[index].get_value() == 'if':
        #         ifs.append(ast.ListCompIf(tokens[index+1]))
        #         index += 2
        #     list_fors.append(ast.ListCompFor(ass_node, iterable, ifs))
        #     ifs = []
        # else:
        #     raise ValueError('Unexpected token: %s' % tokens[index])
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
    if tokens:
        lineno = tokens[0].lineno
    else:
        lineno = -1
    while index < len(tokens):
        token = tokens[index]
        assert isinstance(token, TokenObject) # rtyper info + check
        if token.get_value() == 'for':
            index += 1 # skip 'for'
            ass_node = to_lvalue(tokens[index], consts.OP_ASSIGN)
            index += 2 # skip 'in'
            iterable = tokens[index]
            index += 1
            while index < len(tokens):
                token = tokens[index]
                assert isinstance(token, TokenObject) # rtyper info
                if token.get_value() == 'if':
                    ifs.append(ast.GenExprIf(tokens[index+1], token.lineno))
                    index += 2
                else:
                    break
            genexpr_fors.append(ast.GenExprFor(ass_node, iterable, ifs, lineno))
            ifs = []
        else:
            raise SyntaxError('invalid syntax',
                              token.lineno, token.col)
    return genexpr_fors


def get_docstring(builder,stmt):
    """parses a Stmt node.

    If a docstring if found, the Discard node is **removed**
    from <stmt> and the docstring is returned.

    If no docstring is found, <stmt> is left unchanged
    and None is returned
    """
    if not isinstance(stmt, ast.Stmt):
        return None
    doc = builder.wrap_none()
    if len(stmt.nodes):
        first_child = stmt.nodes[0]
        if isinstance(first_child, ast.Discard):
            expr = first_child.expr
            if builder.is_basestring_const(expr):
                # This *is* a docstring, remove it from stmt list
                assert isinstance(expr, ast.Const)
                del stmt.nodes[0]
                doc = expr.value
    return doc


def to_lvalue(ast_node, flags):
    lineno = ast_node.lineno
    if isinstance( ast_node, ast.Name ):
        return ast.AssName(ast_node.varname, flags, lineno)
        # return ast.AssName(ast_node.name, flags)
    elif isinstance(ast_node, ast.Tuple):
        nodes = []
        # FIXME: should ast_node.getChildren() but it's not annotable
        #        because of flatten()
        for node in ast_node.nodes:
            nodes.append(to_lvalue(node, flags))
        return ast.AssTuple(nodes, lineno)
    elif isinstance(ast_node, ast.List):
        nodes = []
        # FIXME: should ast_node.getChildren() but it's not annotable
        #        because of flatten()
        for node in ast_node.nodes:
            nodes.append(to_lvalue(node, flags))
        return ast.AssList(nodes, lineno)
    elif isinstance(ast_node, ast.Getattr):
        expr = ast_node.expr
        assert isinstance(ast_node, ast.Getattr)
        attrname = ast_node.attrname
        return ast.AssAttr(expr, attrname, flags, lineno)
    elif isinstance(ast_node, ast.Subscript):
        ast_node.flags = flags
        return ast_node
    elif isinstance(ast_node, ast.Slice):
        ast_node.flags = flags
        return ast_node
    else:
        if isinstance(ast_node, ast.GenExpr):
            raise SyntaxError("assign to generator expression not possible",
                             lineno, 0, '')
        elif isinstance(ast_node, ast.ListComp):
            raise SyntaxError("can't assign to list comprehension",
                             lineno, 0, '')
        elif isinstance(ast_node, ast.CallFunc):
            if flags == consts.OP_DELETE:
                raise SyntaxError("can't delete function call",
                                 lineno, 0, '')
            else:
                raise SyntaxError("can't assign to function call",
                                 lineno, 0, '')
        else:
            raise SyntaxError("can't assign to non-lvalue",
                             lineno, 0, '')

def is_augassign( ast_node ):
    if ( isinstance( ast_node, ast.Name ) or
         isinstance( ast_node, ast.Slice ) or
         isinstance( ast_node, ast.Subscript ) or
         isinstance( ast_node, ast.Getattr ) ):
        return True
    return False

def get_atoms(builder, nb):
    atoms = []
    i = nb
    while i>0:
        obj = builder.pop()
        if isinstance(obj, BaseRuleObject):
            i += obj.count
        else:
            atoms.append( obj )
        i -= 1
    atoms.reverse()
    return atoms

#def eval_string(value):
#    """temporary implementation
#
#    FIXME: need to be finished (check compile.c (parsestr) and
#    stringobject.c (PyString_DecodeEscape()) for complete implementation)
#    """
#    # return eval(value)
#    if len(value) == 2:
#        return ''
#    result = ''
#    length = len(value)
#    quotetype = value[0]
#    index = 1
#    while index < length and value[index] == quotetype:
#        index += 1
#    if index == 6:
#        # empty strings like """""" or ''''''
#        return ''
#    # XXX: is it RPYTHON to do this value[index:-index]
#    chars = [char for char in value[index:len(value)-index]]
#    result = ''.join(chars)
#    result = result.replace('\\\\', '\\')
#    d = {'\\b' : '\b', '\\f' : '\f', '\\t' : '\t', '\\n' : '\n',
#         '\\r' : '\r', '\\v' : '\v', '\\a' : '\a',
#         }
#    for escaped, value in d.items():
#        result = result.replace(escaped, value)
#    return result


## misc utilities, especially for power: rule
def reduce_callfunc(obj, arglist):
    """generic factory for CallFunc nodes"""
    assert isinstance(arglist, ArglistObject)
    return ast.CallFunc(obj, arglist.arguments,
                        arglist.stararg, arglist.dstararg, arglist.lineno)

def reduce_subscript(obj, subscript):
    """generic factory for Subscript nodes"""
    assert isinstance(subscript, SubscriptObject)
    return ast.Subscript(obj, consts.OP_APPLY, subscript.value, subscript.lineno)

def reduce_slice(obj, sliceobj):
    """generic factory for Slice nodes"""
    assert isinstance(sliceobj, SlicelistObject)
    if sliceobj.fake_rulename == 'slice':
        start = sliceobj.value[0]
        end = sliceobj.value[1]
        return ast.Slice(obj, consts.OP_APPLY, start, end, sliceobj.lineno)
    else:
        return ast.Subscript(obj, consts.OP_APPLY, ast.Sliceobj(sliceobj.value,
                                                                sliceobj.lineno), sliceobj.lineno)

def parse_attraccess(tokens):
    """parses token list like ['a', '.', 'b', '.', 'c', ...]

    and returns an ast node : ast.Getattr(Getattr(Name('a'), 'b'), 'c' ...)
    """
    token = tokens[0]
    # XXX HACK for when parse_attraccess is called from build_decorator
    if isinstance(token, TokenObject):
        val = token.get_value()
        result = ast.Name(val, token.lineno)
    else:
        result = token
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if isinstance(token, TokenObject) and token.name == tok.DOT:
            index += 1
            token = tokens[index]
            assert isinstance(token, TokenObject)
            result = ast.Getattr(result, token.get_value(), token.lineno)
        elif isinstance(token, ArglistObject):
            result = reduce_callfunc(result, token)
        elif isinstance(token, SubscriptObject):
            result = reduce_subscript(result, token)
        elif isinstance(token, SlicelistObject):
            result = reduce_slice(result, token)
        else:
            assert False, "Don't know how to handle index %s of %s" % (index, len(tokens))
        index += 1
    return result


## building functions helpers
## --------------------------
##
## Builder functions used to reduce the builder stack into appropriate
## AST nodes. All the builder functions have the same interface
##
## Naming convention:
## to provide a function handler for a grammar rule name yyy
## you should provide a build_yyy(builder, nb) function
## where builder is the AstBuilder instance used to build the
## ast tree and nb is the number of items this rule is reducing
##
## Example:
## for example if the rule
##    term <- var ( '+' expr )*
## matches
##    x + (2*y) + z
## build_term will be called with nb == 2
## and get_atoms(builder, nb) should return a list
## of 5 objects : Var TokenObject('+') Expr('2*y') TokenObject('+') Expr('z')
## where Var and Expr are AST subtrees and Token is a not yet
## reduced token
##
## ASTRULES is kept as a dictionnary to be rpython compliant this is the
## main reason why build_* functions are not methods of the AstBuilder class
##

def build_atom(builder, nb):
    atoms = get_atoms(builder, nb)
    top = atoms[0]
    if isinstance(top, TokenObject):
        # assert isinstance(top, TokenObject) # rtyper
        if top.name == tok.LPAR:
            if len(atoms) == 2:
                builder.push(ast.Tuple([], top.lineno))
            else:
                builder.push( atoms[1] )
        elif top.name == tok.LSQB:
            if len(atoms) == 2:
                builder.push(ast.List([], top.lineno))
            else:
                list_node = atoms[1]
                list_node.lineno = top.lineno
                builder.push(list_node)
        elif top.name == tok.LBRACE:
            items = []
            for index in range(1, len(atoms)-1, 4):
                # a   :   b   ,   c : d
                # ^  +1  +2  +3  +4
                items.append((atoms[index], atoms[index+2]))
            builder.push(ast.Dict(items, top.lineno))
        elif top.name == tok.NAME:
            val = top.get_value()
            builder.push( ast.Name(val, top.lineno) )
        elif top.name == tok.NUMBER:
            builder.push(ast.Const(builder.eval_number(top.get_value()), top.lineno))
        elif top.name == tok.STRING:
            # need to concatenate strings in atoms
            s = ''
            if len(atoms) == 1:
                token = atoms[0]
                assert isinstance(token, TokenObject)
                builder.push(ast.Const(parsestr(builder.space, builder.source_encoding, token.get_value()), top.lineno))
            else:
                space = builder.space
                empty = space.wrap('')
                accum = []
                for token in atoms:
                    assert isinstance(token, TokenObject)
                    accum.append(parsestr(builder.space, builder.source_encoding, token.get_value()))
                w_s = space.call_method(empty, 'join', space.newlist(accum))
                builder.push(ast.Const(w_s, top.lineno))
        elif top.name == tok.BACKQUOTE:
            builder.push(ast.Backquote(atoms[1], atoms[1].lineno))
        else:
            raise SyntaxError("unexpected tokens", top.lineno, top.col)

def slicecut(lst, first, endskip): # endskip is negative
    last = len(lst)+endskip
    if last > first:
        return lst[first:last]
    else:
        return []


def build_power(builder, nb):
    """power: atom trailer* ['**' factor]"""
    atoms = get_atoms(builder, nb)
    if len(atoms) == 1:
        builder.push(atoms[0])
    else:
        lineno = atoms[0].lineno
        token = atoms[-2]
        if isinstance(token, TokenObject) and token.name == tok.DOUBLESTAR:
            obj = parse_attraccess(slicecut(atoms, 0, -2))
            builder.push(ast.Power( obj, atoms[-1], lineno))
        else:
            obj = parse_attraccess(atoms)
            builder.push(obj)

def build_factor(builder, nb):
    atoms = get_atoms(builder, nb)
    if len(atoms) == 1:
        builder.push( atoms[0] )
    elif len(atoms) == 2:
        token = atoms[0]
        lineno = token.lineno
        if isinstance(token, TokenObject):
            if token.name == tok.PLUS:
                builder.push( ast.UnaryAdd( atoms[1], lineno) )
            if token.name == tok.MINUS:
                builder.push( ast.UnarySub( atoms[1], lineno) )
            if token.name == tok.TILDE:
                builder.push( ast.Invert( atoms[1], lineno) )

def build_term(builder, nb):
    atoms = get_atoms(builder, nb)
    l = len(atoms)
    left = atoms[0]
    for i in range(2,l,2):
        right = atoms[i]
        op_node = atoms[i-1]
        assert isinstance(op_node, TokenObject)
        if op_node.name == tok.STAR:
            left = ast.Mul( left, right, left.lineno )
        elif op_node.name == tok.SLASH:
            left = ast.Div( left, right, left.lineno )
        elif op_node.name == tok.PERCENT:
            left = ast.Mod( left, right, left.lineno )
        elif op_node.name == tok.DOUBLESLASH:
            left = ast.FloorDiv( left, right, left.lineno )
        else:
            token = atoms[i-1]
            raise SyntaxError("unexpected token", token.lineno, token.col)
    builder.push( left )

def build_arith_expr(builder, nb):
    atoms = get_atoms(builder, nb)
    l = len(atoms)
    left = atoms[0]
    for i in range(2,l,2):
        right = atoms[i]
        op_node = atoms[i-1]
        assert isinstance(op_node, TokenObject)
        if op_node.name == tok.PLUS:
            left = ast.Add( left, right, left.lineno)
        elif op_node.name == tok.MINUS:
            left = ast.Sub( left, right, left.lineno)
        else:
            token = atoms[i-1]
            raise SyntaxError("unexpected token", token.lineno, token.col)
    builder.push( left )

def build_shift_expr(builder, nb):
    atoms = get_atoms(builder, nb)
    l = len(atoms)
    left = atoms[0]
    lineno = left.lineno
    for i in range(2,l,2):
        right = atoms[i]
        op_node = atoms[i-1]
        assert isinstance(op_node, TokenObject)
        if op_node.name == tok.LEFTSHIFT:
            left = ast.LeftShift( left, right, lineno )
        elif op_node.name == tok.RIGHTSHIFT:
            left = ast.RightShift( left, right, lineno )
        else:
            token = atoms[i-1]
            raise SyntaxError("unexpected token", token.lineno, token.col)
    builder.push(left)


def build_binary_expr(builder, nb, OP):
    atoms = get_atoms(builder, nb)
    l = len(atoms)
    if l==1:
        builder.push(atoms[0])
        return
    # Here, len(atoms) >= 2
    items = []
    # Apparently, lineno should be set to the line where
    # the first OP occurs
    lineno = atoms[1].lineno
    for i in range(0,l,2): # this is atoms not 1
        items.append(atoms[i])
    builder.push(OP(items, lineno))
    return

def build_and_expr(builder, nb):
    return build_binary_expr(builder, nb, ast.Bitand)

def build_xor_expr(builder, nb):
    return build_binary_expr(builder, nb, ast.Bitxor)

def build_expr(builder, nb):
    return build_binary_expr(builder, nb, ast.Bitor)

def build_comparison(builder, nb):
    atoms = get_atoms(builder, nb)
    l = len(atoms)
    if l == 1:
        builder.push( atoms[0] )
        return
    else:
        # a < b < c is transalted into:
        # Compare(Name('a'), [('<', Name(b)), ('<', Name(c))])
        left_token = atoms[0]
        ops = []
        for i in range(1, l, 2):
            # if tok.name isn't in rpunct, then it should be
            # 'is', 'is not', 'not' or 'not in' => tok.get_value()
            token = atoms[i]
            assert isinstance(token, TokenObject)
            op_name = tok.tok_rpunct.get(token.name, token.get_value())
            ops.append((op_name, atoms[i+1]))
        builder.push(ast.Compare(atoms[0], ops, atoms[0].lineno))

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
    atoms = get_atoms(builder, nb)
    l = len(atoms)
    # l==1 means '<', '>', '<=', etc.
    if l == 1:
        builder.push(atoms[0])
    # l==2 means 'not in' or 'is not'
    elif l == 2:
        token = atoms[0]
        lineno = token.lineno
        assert isinstance(token, TokenObject)
        if token.get_value() == 'not':
            builder.push(TokenObject(tok.NAME, 'not in', lineno))
        else:
            builder.push(TokenObject(tok.NAME, 'is not', lineno))
    else:
        assert False, "TODO" # uh ?

def build_or_test(builder, nb):
    return build_binary_expr(builder, nb, ast.Or)

def build_and_test(builder, nb):
    return build_binary_expr(builder, nb, ast.And)

def build_not_test(builder, nb):
    atoms = get_atoms(builder, nb)
    if len(atoms) == 1:
        builder.push(atoms[0])
    elif len(atoms) == 2:
        builder.push(ast.Not(atoms[1], atoms[1].lineno))
    else:
        assert False, "not_test implementation incomplete in not_test"

def build_test(builder, nb):
    atoms = get_atoms(builder, nb)
    l = len(atoms)
    if l == 1:
        builder.push(atoms[0])
    elif l == 5 and atoms[1].get_value() == 'if':
        builder.push(
            ast.CondExpr(atoms[2], atoms[0], atoms[4], atoms[1].lineno))
    else:
        lineno = atoms[1].lineno
        items = []
        for i in range(0,l,2): # this is atoms not 1
            items.append(atoms[i])
        builder.push(ast.Or(items, lineno))

# Note: we do not include a build_old_test() because it does not need to do
# anything.

def build_testlist(builder, nb):
    return build_binary_expr(builder, nb, ast.Tuple)

def build_expr_stmt(builder, nb):
    """expr_stmt: testlist (augassign testlist | ('=' testlist)*)
    """
    atoms = get_atoms(builder, nb)
    if atoms:
        lineno = atoms[0].lineno
    else:
        lineno = -1
    l = len(atoms)
    if l==1:
        builder.push(ast.Discard(atoms[0], lineno))
        return
    op = atoms[1]
    assert isinstance(op, TokenObject)
    if op.name == tok.EQUAL:
        nodes = []
        for i in range(0,l-2,2):
            lvalue = to_lvalue(atoms[i], consts.OP_ASSIGN)
            nodes.append(lvalue)
        rvalue = atoms[-1]
        builder.push( ast.Assign(nodes, rvalue, lineno) )
        pass
    else:
        assert l==3
        lvalue = atoms[0]
        if isinstance(lvalue, ast.GenExpr) or isinstance(lvalue, ast.Tuple):
            raise SyntaxError("augmented assign to tuple literal or generator expression not possible",
                             lineno, 0, "")
        assert isinstance(op, TokenObject)
        builder.push(ast.AugAssign(lvalue, op.get_name(), atoms[2], lineno))

def return_one(builder, nb):
    atoms = get_atoms(builder, nb)
    l = len(atoms)
    assert l == 1, "missing one node in stack"
    builder.push( atoms[0] )
    return

def build_simple_stmt(builder, nb):
    atoms = get_atoms(builder, nb)
    l = len(atoms)
    nodes = []
    if atoms:
        lineno = atoms[0].lineno
    else:
        lineno = -1
    for n in range(0,l,2):
        node = atoms[n]
        if isinstance(node, TokenObject) and node.name == tok.NEWLINE:
            nodes.append(ast.Discard(ast.Const(builder.wrap_none()), node.lineno))
        else:
            nodes.append(node)
    builder.push(ast.Stmt(nodes, lineno))

def build_return_stmt(builder, nb):
    atoms = get_atoms(builder, nb)
    lineno = atoms[0].lineno
    if len(atoms) > 2:
        assert False, "return several stmts not implemented"
    elif len(atoms) == 1:
        builder.push(ast.Return(None, lineno))
    else:
        builder.push(ast.Return(atoms[1], lineno))

def build_file_input(builder, nb):
    stmts = []
    atoms = get_atoms(builder, nb)
    if atoms:
        lineno = atoms[0].lineno
    else:
        lineno = -1
    for node in atoms:
        if isinstance(node, ast.Stmt):
            stmts.extend(node.nodes)
        elif isinstance(node, TokenObject) and node.name == tok.ENDMARKER:
            # XXX Can't we just remove the last element of the list ?
            break
        elif isinstance(node, TokenObject) and node.name == tok.NEWLINE:
            continue
        else:
            stmts.append(node)
    main_stmt = ast.Stmt(stmts, lineno)
    doc = get_docstring(builder,main_stmt)
    return builder.push(ast.Module(doc, main_stmt, lineno))

def build_eval_input(builder, nb):
    doc = builder.wrap_none()
    stmts = []
    atoms = get_atoms(builder, nb)
    assert len(atoms)>=1
    return builder.push(ast.Expression(atoms[0]))

def build_single_input(builder, nb):
    atoms = get_atoms(builder, nb)
    l = len(atoms)
    if l == 1 or l==2:
        atom0 = atoms[0]
        if isinstance(atom0, TokenObject) and atom0.name == tok.NEWLINE:
            atom0 = ast.Pass(atom0.lineno)
        elif not isinstance(atom0, ast.Stmt):
            atom0 = ast.Stmt([atom0], atom0.lineno)
        builder.push(ast.Module(builder.wrap_none(), atom0, atom0.lineno))
    else:
        assert False, "Forbidden path"

def build_testlist_gexp(builder, nb):
    atoms = get_atoms(builder, nb)
    if atoms:
        lineno = atoms[0].lineno
    else:
        lineno = -1
    l = len(atoms)
    if l == 1:
        builder.push(atoms[0])
        return
    items = []
    token = atoms[1]
    if isinstance(token, TokenObject) and token.name == tok.COMMA:
        for i in range(0, l, 2): # this is atoms not 1
            items.append(atoms[i])
    else:
        # genfor: 'i for i in j'
        # GenExpr(GenExprInner(Name('i'), [GenExprFor(AssName('i', 'OP_ASSIGN'), Name('j'), [])])))]))
        expr = atoms[0]
        genexpr_for = parse_genexpr_for(atoms[1:])
        genexpr_for[0].is_outmost = True
        builder.push(ast.GenExpr(ast.GenExprInner(expr, genexpr_for, lineno), lineno))
        return
    isConst = True
    values = []
    for item in items:
        if isinstance(item, ast.Const):
            values.append(item.value)
        else:
            isConst = False
            break
    if isConst:
        builder.push(ast.Const(builder.space.newtuple(values), lineno))
    else:
        builder.push(ast.Tuple(items, lineno))
    return

def build_lambdef(builder, nb):
    """lambdef: 'lambda' [varargslist] ':' test"""
    atoms = get_atoms(builder, nb)
    lineno = atoms[0].lineno
    code = atoms[-1]
    names, defaults, flags = parse_arglist(slicecut(atoms, 1, -2))
    builder.push(ast.Lambda(names, defaults, flags, code, lineno))

def build_trailer(builder, nb):
    """trailer: '(' ')' | '(' arglist ')' | '[' subscriptlist ']' | '.' NAME
    """
    atoms = get_atoms(builder, nb)
    first_token = atoms[0]
    # Case 1 : '(' ...
    if isinstance(first_token, TokenObject) and first_token.name == tok.LPAR:
        if len(atoms) == 2: # and atoms[1].token == tok.RPAR:
            builder.push(ArglistObject([], None, None, first_token.lineno))
        elif len(atoms) == 3: # '(' Arglist ')'
            # push arglist on the stack
            builder.push(atoms[1])
    elif isinstance(first_token, TokenObject) and first_token.name == tok.LSQB:
        if len(atoms) == 3 and isinstance(atoms[1], SlicelistObject):
            builder.push(atoms[1])
        else:
            # atoms is a list of, alternatively, values and comma tokens,
            # with '[' and ']' tokens at the end
            subs = []
            for index in range(1, len(atoms)-1, 2):
                atom = atoms[index]
                if isinstance(atom, SlicelistObject):
                    num_slicevals = 3
                    slicevals = []
                    if atom.fake_rulename == 'slice':
                        num_slicevals = 2
                    for val in atom.value[:num_slicevals]:
                        if val is None:
                            slicevals.append(ast.Const(builder.wrap_none(), atom.lineno))
                        else:
                            slicevals.append(val)
                    subs.append(ast.Sliceobj(slicevals, atom.lineno))
                else:
                    subs.append(atom)
            if len(atoms) > 3:   # at least one comma
                sub = ast.Tuple(subs, first_token.lineno)
            else:
                [sub] = subs
            builder.push(SubscriptObject('subscript', sub, first_token.lineno))
    elif len(atoms) == 2:
        # Attribute access: '.' NAME
        builder.push(atoms[0])
        builder.push(atoms[1])
        builder.push(TempRuleObject('pending-attr-access', 2, first_token.lineno))
    else:
        assert False, "Trailer reducing implementation incomplete !"

def build_arglist(builder, nb):
    """
    arglist: (argument ',')* ( '*' test [',' '**' test] |
                               '**' test |
                                argument |
                                [argument ','] )
    """
    atoms = get_atoms(builder, nb)
    arguments, stararg, dstararg = parse_argument(atoms)
    if atoms:
        lineno = atoms[0].lineno
    else:
        lineno = -1
    builder.push(ArglistObject(arguments, stararg, dstararg, lineno))


def build_subscript(builder, nb):
    """'.' '.' '.' | [test] ':' [test] [':' [test]] | test"""
    atoms = get_atoms(builder, nb)
    token = atoms[0]
    lineno = token.lineno
    if isinstance(token, TokenObject) and token.name == tok.DOT:
        # Ellipsis:
        builder.push(ast.Ellipsis(lineno))
    elif len(atoms) == 1:
        if isinstance(token, TokenObject) and token.name == tok.COLON:
            sliceinfos = [None, None, None]
            builder.push(SlicelistObject('slice', sliceinfos, lineno))
        else:
            # test
            builder.push(token)
    else: # elif len(atoms) > 1:
        sliceinfos = [None, None, None]
        infosindex = 0
        for token in atoms:
            if isinstance(token, TokenObject) and token.name == tok.COLON:
                infosindex += 1
            else:
                sliceinfos[infosindex] = token
        if infosindex == 2:
            sliceobj_infos = []
            for value in sliceinfos:
                if value is None:
                    sliceobj_infos.append(ast.Const(builder.wrap_none(), lineno))
                else:
                    sliceobj_infos.append(value)
            builder.push(SlicelistObject('sliceobj', sliceobj_infos, lineno))
        else:
            builder.push(SlicelistObject('slice', sliceinfos, lineno))


def build_listmaker(builder, nb):
    """listmaker: test ( list_for | (',' test)* [','] )"""
    atoms = get_atoms(builder, nb)
    if len(atoms) >= 2:
        token = atoms[1]
        lineno = token.lineno
        if isinstance(token, TokenObject):
            if token.get_value() == 'for':
                # list comp
                expr = atoms[0]
                list_for = parse_listcomp(atoms[1:])
                builder.push(ast.ListComp(expr, list_for, lineno))
                return
    # regular list building (like in [1, 2, 3,])
    index = 0
    nodes = []
    while index < len(atoms):
        nodes.append(atoms[index])
        index += 2 # skip comas
    if atoms:
        lineno = atoms[0].lineno
    else:
        lineno = -1
    builder.push(ast.List(nodes, lineno))


def build_decorator(builder, nb):
    """decorator: '@' dotted_name [ '(' [arglist] ')' ] NEWLINE"""
    atoms = get_atoms(builder, nb)
    nodes = []
    # remove '@', '(' and ')' from atoms and use parse_attraccess
    for token in atoms[1:]:
        if isinstance(token, TokenObject) and \
               token.name in (tok.LPAR, tok.RPAR, tok.NEWLINE):
            # skip those ones
            continue
        else:
            nodes.append(token)
    obj = parse_attraccess(nodes)
    builder.push(obj)

def build_funcdef(builder, nb):
    """funcdef: [decorators] 'def' NAME parameters ':' suite
    """
    atoms = get_atoms(builder, nb)
    index = 0
    decorators = []
    decorator_node = None
    lineno = atoms[0].lineno
    # the original loop was:
    # while not (isinstance(atoms[index], TokenObject) and atoms[index].get_value() == 'def'):
    #     decorators.append(atoms[index])
    #     index += 1
    while index < len(atoms):
        atom = atoms[index]
        if isinstance(atom, TokenObject) and atom.get_value() == 'def':
            break
        decorators.append(atoms[index])
        index += 1
    if decorators:
        decorator_node = ast.Decorators(decorators, lineno)
    atoms = atoms[index:]
    funcname = atoms[1]
    lineno = funcname.lineno
    arglist = []
    index = 3
    arglist = slicecut(atoms, 3, -3)
    names, default, flags = parse_arglist(arglist)
    funcname_token = atoms[1]
    assert isinstance(funcname_token, TokenObject)
    funcname = funcname_token.get_value()
    assert funcname is not None
    arglist = atoms[2]
    code = atoms[-1]
    doc = get_docstring(builder, code)
    builder.push(ast.Function(decorator_node, funcname, names, default, flags, doc, code, lineno))


def build_classdef(builder, nb):
    """classdef: 'class' NAME ['(' testlist ')'] ':' suite"""
    atoms = get_atoms(builder, nb)
    lineno = atoms[0].lineno
    l = len(atoms)
    classname_token = atoms[1]
    assert isinstance(classname_token, TokenObject)
    classname = classname_token.get_value()
    if l == 4:
        basenames = []
        body = atoms[3]
    else:
        assert l == 7
        basenames = []
        body = atoms[6]
        base = atoms[3]
        if isinstance(base, ast.Tuple):
            for node in base.nodes:
                basenames.append(node)
        else:
            basenames.append(base)
    doc = get_docstring(builder,body)
    builder.push(ast.Class(classname, basenames, doc, body, lineno))

def build_suite(builder, nb):
    """suite: simple_stmt | NEWLINE INDENT stmt+ DEDENT"""
    atoms = get_atoms(builder, nb)
    if len(atoms) == 1:
        builder.push(atoms[0])
    elif len(atoms) == 4:
        # Only one statement for (stmt+)
        stmt = atoms[2]
        if not isinstance(stmt, ast.Stmt):
            stmt = ast.Stmt([stmt], atoms[0].lineno)
        builder.push(stmt)
    else:
        # several statements
        stmts = []
        nodes = slicecut(atoms, 2,-1)
        for node in nodes:
            if isinstance(node, ast.Stmt):
                stmts.extend(node.nodes)
            else:
                stmts.append(node)
        builder.push(ast.Stmt(stmts, atoms[0].lineno))


def build_if_stmt(builder, nb):
    """
    if_stmt: 'if' test ':' suite ('elif' test ':' suite)* ['else' ':' suite]
    """
    atoms = get_atoms(builder, nb)
    tests = []
    tests.append((atoms[1], atoms[3]))
    index = 4
    else_ = None
    while index < len(atoms):
        cur_token = atoms[index]
        assert isinstance(cur_token, TokenObject) # rtyper
        if cur_token.get_value() == 'elif':
            tests.append((atoms[index+1], atoms[index+3]))
            index += 4
        else: # cur_token.get_value() == 'else'
            else_ = atoms[index+2]
            break # break is not necessary
    builder.push(ast.If(tests, else_, atoms[0].lineno))

def build_pass_stmt(builder, nb):
    """past_stmt: 'pass'"""
    atoms = get_atoms(builder, nb)
    assert len(atoms) == 1
    builder.push(ast.Pass(atoms[0].lineno))


def build_break_stmt(builder, nb):
    """past_stmt: 'pass'"""
    atoms = get_atoms(builder, nb)
    assert len(atoms) == 1
    builder.push(ast.Break(atoms[0].lineno))


def build_for_stmt(builder, nb):
    """for_stmt: 'for' exprlist 'in' testlist ':' suite ['else' ':' suite]"""
    atoms = get_atoms(builder, nb)
    else_ = None
    # skip 'for'
    assign = to_lvalue(atoms[1], consts.OP_ASSIGN)
    # skip 'in'
    iterable = atoms[3]
    # skip ':'
    body = atoms[5]
    # if there is a "else" statement
    if len(atoms) > 6:
        # skip 'else' and ':'
        else_ = atoms[8]
    builder.push(ast.For(assign, iterable, body, else_, atoms[0].lineno))

def build_exprlist(builder, nb):
    """exprlist: expr (',' expr)* [',']"""
    atoms = get_atoms(builder, nb)
    if len(atoms) <= 2:
        builder.push(atoms[0])
    else:
        names = []
        values = []
        isConst = True
        for index in range(0, len(atoms), 2):
            item = atoms[index]
            names.append(item)
            if isinstance(item, ast.Const):
                values.append(item)
            else:
                isConst = False
        if isConst:
            builder.push(ast.Const(builder.space.newtuple(values), atoms[0].lineno))
        else:
            builder.push(ast.Tuple(names, atoms[0].lineno))


def build_while_stmt(builder, nb):
    """while_stmt: 'while' test ':' suite ['else' ':' suite]"""
    atoms = get_atoms(builder, nb)
    else_ = None
    # skip 'while'
    test =  atoms[1]
    # skip ':'
    body = atoms[3]
    # if there is a "else" statement
    if len(atoms) > 4:
        # skip 'else' and ':'
        else_ = atoms[6]
    builder.push(ast.While(test, body, else_, atoms[0].lineno))

def build_with_stmt(builder, nb):
    """with_stmt: 'with' test [ NAME expr ] ':' suite"""

    atoms = get_atoms(builder, nb)
    # skip 'with'
    test =  atoms[1]
    if len(atoms) == 4:
        body = atoms[3]
        var = None
    # if there is an "as" clause
    else:
        token = atoms[2]
        assert isinstance(token, TokenObject)
        varexpr = atoms[3]
        var = to_lvalue(varexpr, consts.OP_ASSIGN)
        body = atoms[5]
    builder.push(ast.With(test, body, var, atoms[0].lineno))

def build_import_name(builder, nb):
    """import_name: 'import' dotted_as_names

    dotted_as_names: dotted_as_name (',' dotted_as_name)*
    dotted_as_name: dotted_name [NAME NAME]
    dotted_name: NAME ('.' NAME)*

    written in an unfolded way:
    'import' NAME(.NAME)* [NAME NAME], (NAME(.NAME)* [NAME NAME],)*

    XXX: refactor build_import_name and build_import_from
    """
    atoms = get_atoms(builder, nb)
    index = 1 # skip 'import'
    l = len(atoms)
    names = []
    while index < l:
        as_name = None
        # dotted name (a.b.c)
        incr, name = parse_dotted_names(atoms[index:])
        index += incr
        # 'as' value
        if index < l:
            token = atoms[index]
            assert isinstance(token, TokenObject)
            if token.get_value() == 'as':
                token = atoms[index+1]
                assert isinstance(token, TokenObject)
                as_name = token.get_value()
                index += 2
        names.append((name, as_name))
        # move forward until next ','
        # XXX: what is it supposed to do ?
        while index<l:
            atom = atoms[index]
#        for atom in atoms[index:]:
            if isinstance(atom, TokenObject) and atom.name == tok.COMMA:
                break
            index += 1
##         while index < l and isinstance(atoms[index], TokenObject) and \
##                 atoms[index].name != tok.COMMA:
##             index += 1
        index += 1
    builder.push(ast.Import(names, atoms[0].lineno))


def build_import_from(builder, nb):
    """
    import_from: 'from' dotted_name 'import' ('*' | '(' import_as_names [','] ')' | import_as_names)

    import_as_names: import_as_name (',' import_as_name)*
    import_as_name: NAME [NAME NAME]
    """
    atoms = get_atoms(builder, nb)
    index = 1
    incr, from_name = parse_dotted_names(atoms[index:])
    index += (incr + 1) # skip 'import'
    token = atoms[index]
    assert isinstance(token, TokenObject) # XXX
    if token.name == tok.STAR:
        names = [('*', None)]
    else:
        if token.name == tok.LPAR:
            # mutli-line imports
            tokens = slicecut( atoms, index+1, -1 )
        else:
            tokens = atoms[index:]
        index = 0
        l = len(tokens)
        names = []
        while index < l:
            token = tokens[index]
            assert isinstance(token, TokenObject)
            name = token.get_value()
            as_name = None
            index += 1
            if index < l:
                token = tokens[index]
                assert isinstance(token, TokenObject)
                if token.get_value() == 'as':
                    token = tokens[index+1]
                    assert isinstance(token, TokenObject)
                    as_name = token.get_value()
                    index += 2
            names.append((name, as_name))
            if index < l: # case ','
                index += 1
    if from_name == '__future__':
        for name, asname in names:
            if name == 'with_statement':
                # found from __future__ import with_statement
                if not builder.with_enabled:
                    builder.enable_with()
                    #raise pythonparse.AlternateGrammarException()
    builder.push(ast.From(from_name, names, atoms[0].lineno))


def build_yield_stmt(builder, nb):
    atoms = get_atoms(builder, nb)
    builder.push(ast.Yield(atoms[1], atoms[0].lineno))

def build_continue_stmt(builder, nb):
    atoms = get_atoms(builder, nb)
    builder.push(ast.Continue(atoms[0].lineno))

def build_del_stmt(builder, nb):
    atoms = get_atoms(builder, nb)
    builder.push(to_lvalue(atoms[1], consts.OP_DELETE))


def build_assert_stmt(builder, nb):
    """assert_stmt: 'assert' test [',' test]"""
    atoms = get_atoms(builder, nb)
    test = atoms[1]
    if len(atoms) == 4:
        fail = atoms[3]
    else:
        fail = None
    builder.push(ast.Assert(test, fail, atoms[0].lineno))

def build_exec_stmt(builder, nb):
    """exec_stmt: 'exec' expr ['in' test [',' test]]"""
    atoms = get_atoms(builder, nb)
    expr = atoms[1]
    loc = None
    glob = None
    if len(atoms) > 2:
        loc = atoms[3]
        if len(atoms) > 4:
            glob = atoms[5]
    builder.push(ast.Exec(expr, loc, glob, atoms[0].lineno))

def build_print_stmt(builder, nb):
    """
    print_stmt: 'print' ( '>>' test [ (',' test)+ [','] ] | [ test (',' test)* [','] ] )
    """
    atoms = get_atoms(builder, nb)
    l = len(atoms)
    items = []
    dest = None
    start = 1
    if l > 1:
        token = atoms[1]
        if isinstance(token, TokenObject) and token.name == tok.RIGHTSHIFT:
            dest = atoms[2]
            # skip following comma
            start = 4
    for index in range(start, l, 2):
        items.append(atoms[index])
    last_token = atoms[-1]
    if isinstance(last_token, TokenObject) and last_token.name == tok.COMMA:
        builder.push(ast.Print(items, dest, atoms[0].lineno))
    else:
        builder.push(ast.Printnl(items, dest, atoms[0].lineno))

def build_global_stmt(builder, nb):
    """global_stmt: 'global' NAME (',' NAME)*"""
    atoms = get_atoms(builder, nb)
    names = []
    for index in range(1, len(atoms), 2):
        token = atoms[index]
        assert isinstance(token, TokenObject)
        names.append(token.get_value())
    builder.push(ast.Global(names, atoms[0].lineno))


def build_raise_stmt(builder, nb):
    """raise_stmt: 'raise' [test [',' test [',' test]]]"""
    atoms = get_atoms(builder, nb)
    l = len(atoms)
    expr1 = None
    expr2 = None
    expr3 = None
    if l >= 2:
        expr1 = atoms[1]
        if l >= 4:
            expr2 = atoms[3]
            if l == 6:
                expr3 = atoms[5]
    builder.push(ast.Raise(expr1, expr2, expr3, atoms[0].lineno))

def build_try_stmt(builder, nb):
    """
    try_stmt: ('try' ':' suite (except_clause ':' suite)+ #diagram:break
               ['else' ':' suite] | 'try' ':' suite 'finally' ':' suite)
    # NB compile.c makes sure that the default except clause is last
    except_clause: 'except' [test [',' test]]

    """
    atoms = get_atoms(builder, nb)
    l = len(atoms)
    handlers = []
    else_ = None
    body = atoms[2]
    token = atoms[3]
    assert isinstance(token, TokenObject)
    if token.get_value() == 'finally':
        builder.push(ast.TryFinally(body, atoms[5], atoms[0].lineno))
    else: # token.get_value() == 'except'
        index = 3
        token = atoms[index]
        while isinstance(token, TokenObject) and token.get_value() == 'except':
            tokens_read, expr1, expr2, except_body = parse_except_clause(atoms[index:])
            handlers.append((expr1, expr2, except_body))
            index += tokens_read
            if index < l:
                token = atoms[index]
            else:
                break
        if index < l:
            token = atoms[index]
            assert isinstance(token, TokenObject)
            assert token.get_value() == 'else'
            else_ = atoms[index+2] # skip ':'
        builder.push(ast.TryExcept(body, handlers, else_, atoms[0].lineno))

ASTRULES_Template = {
    'atom' : build_atom,
    'power' : build_power,
    'factor' : build_factor,
    'term' : build_term,
    'arith_expr' : build_arith_expr,
    'shift_expr' : build_shift_expr,
    'and_expr' : build_and_expr,
    'xor_expr' : build_xor_expr,
    'expr' : build_expr,
    'comparison' : build_comparison,
    'comp_op' : build_comp_op,
    'or_test' : build_or_test,
    'and_test' : build_and_test,
    'not_test' : build_not_test,
    'test' : build_test,
    'testlist' : build_testlist,
    'expr_stmt' : build_expr_stmt,
    'small_stmt' : return_one,
    'simple_stmt' : build_simple_stmt,
    'single_input' : build_single_input,
    'file_input' : build_file_input,
    'testlist_gexp' : build_testlist_gexp,
    'lambdef' : build_lambdef,
    'old_lambdef' : build_lambdef,
    'trailer' : build_trailer,
    'arglist' : build_arglist,
    'subscript' : build_subscript,
    'listmaker' : build_listmaker,
    'funcdef' : build_funcdef,
    'classdef' : build_classdef,
    'return_stmt' : build_return_stmt,
    'suite' : build_suite,
    'if_stmt' : build_if_stmt,
    'pass_stmt' : build_pass_stmt,
    'break_stmt' : build_break_stmt,
    'for_stmt' : build_for_stmt,
    'while_stmt' : build_while_stmt,
    'import_name' : build_import_name,
    'import_from' : build_import_from,
    'yield_stmt' : build_yield_stmt,
    'continue_stmt' : build_continue_stmt,
    'del_stmt' : build_del_stmt,
    'assert_stmt' : build_assert_stmt,
    'exec_stmt' : build_exec_stmt,
    'print_stmt' : build_print_stmt,
    'global_stmt' : build_global_stmt,
    'raise_stmt' : build_raise_stmt,
    'try_stmt' : build_try_stmt,
    'exprlist' : build_exprlist,
    'decorator' : build_decorator,
    'eval_input' : build_eval_input,
    'with_stmt' : build_with_stmt,
    }

# Build two almost identical ASTRULES dictionaries
ASTRULES      = dict([(sym[key], value) for (key, value) in
                      ASTRULES_Template.iteritems() if key in sym])
del ASTRULES_Template

## Stack elements definitions ###################################

class BaseRuleObject(ast.Node):
    """Base class for unnamed rules"""
    def __init__(self, count, lineno):
        self.count = count
        self.lineno = lineno # src.getline()
        self.col = 0  # src.getcol()


class RuleObject(BaseRuleObject):
    """A simple object used to wrap a rule or token"""
    def __init__(self, name, count, lineno):
        BaseRuleObject.__init__(self, count, lineno)
        self.rulename = name

    def __str__(self):
        return "<Rule: %s/%d>" % (sym.sym_name[self.rulename], self.count)

    def __repr__(self):
        return "<Rule: %s/%d>" % (sym.sym_name[self.rulename], self.count)


class TempRuleObject(BaseRuleObject):
    """used to keep track of how many items get_atom() should pop"""

    def __init__(self, name, count, lineno):
        BaseRuleObject.__init__(self, count, lineno)
        self.temp_rulename = name

    def __str__(self):
        return "<Rule: %s/%d>" % (self.temp_rulename, self.count)

    def __repr__(self):
        return "<Rule: %s/%d>" % (self.temp_rulename, self.count)


class TokenObject(ast.Node):
    """A simple object used to wrap a rule or token"""
    def __init__(self, name, value, lineno):
        self.name = name
        self.value = value
        self.count = 0
        # self.line = 0 # src.getline()
        self.col = 0  # src.getcol()
        self.lineno = lineno

    def get_name(self):
        return tok.tok_rpunct.get(self.name,
                                  tok.tok_name.get(self.name, str(self.name)))

    def get_value(self):
        value = self.value
        if value is None:
            value = ''
        return value

    def __str__(self):
        return "<Token: (%s,%s)>" % (self.get_name(), self.value)

    def __repr__(self):
        return "<Token: (%r,%s)>" % (self.get_name(), self.value)


class ObjectAccessor(ast.Node):
    """base class for ArglistObject, SubscriptObject and SlicelistObject

    FIXME: think about a more appropriate name
    """

class ArglistObject(ObjectAccessor):
    """helper class to build function's arg list
    """
    def __init__(self, arguments, stararg, dstararg, lineno):
        self.fake_rulename = 'arglist'
        self.arguments = arguments
        self.stararg = stararg
        self.dstararg = dstararg
        self.lineno = lineno

    def __str__(self):
        return "<ArgList: (%s, %s, %s)>" % self.value

    def __repr__(self):
        return "<ArgList: (%s, %s, %s)>" % self.value

class SubscriptObject(ObjectAccessor):
    """helper class to build subscript list

    self.value represents the __getitem__ argument
    """
    def __init__(self, name, value, lineno):
        self.fake_rulename = name
        self.value = value
        self.lineno = lineno

    def __str__(self):
        return "<SubscriptList: (%s)>" % self.value

    def __repr__(self):
        return "<SubscriptList: (%s)>" % self.value

class SlicelistObject(ObjectAccessor):
    """helper class to build slice objects

    self.value is a list [start, end, step]
    self.fake_rulename can either be 'slice' or 'sliceobj' depending
    on if a step is specfied or not (see Python's AST
    for more information on that)
    """
    def __init__(self, name, value, lineno):
        self.fake_rulename = name
        self.value = value
        self.lineno = lineno

    def __str__(self):
        return "<SliceList: (%s)>" % self.value

    def __repr__(self):
        return "<SliceList: (%s)>" % self.value


class AstBuilderContext(AbstractContext):
    """specific context management for AstBuidler"""
    def __init__(self, rule_stack):
        #self.rule_stack = list(rule_stack)
        self.d = len(rule_stack)

class AstBuilder(BaseGrammarBuilder):
    """A builder that directly produce the AST"""

    def __init__(self, rules=None, debug=0, space=None):
        BaseGrammarBuilder.__init__(self, rules, debug)
        self.rule_stack = []
        self.space = space
        self.source_encoding = None
        self.with_enabled = False

    def enable_with(self):
        if self.with_enabled:
            return
        self.with_enabled = True
        self.keywords.update({'with':None, 'as': None})

    def context(self):
        return AstBuilderContext(self.rule_stack)

    def restore(self, ctx):
##         if DEBUG_MODE:
##             print "Restoring context (%s)" % (len(ctx.rule_stack))
        assert isinstance(ctx, AstBuilderContext)
        assert len(self.rule_stack) >= ctx.d
        del self.rule_stack[ctx.d:]
        #self.rule_stack = ctx.rule_stack

    def pop(self):
        return self.rule_stack.pop(-1)

    def push(self, obj):
        self.rule_stack.append(obj)
        if not isinstance(obj, RuleObject) and not isinstance(obj, TokenObject):
##             if DEBUG_MODE:
##                 print "Pushed:", str(obj), len(self.rule_stack)
            pass
        elif isinstance(obj, TempRuleObject):
##             if DEBUG_MODE:
##                 print "Pushed:", str(obj), len(self.rule_stack)
            pass
        # print "\t", self.rule_stack

    def push_tok(self, name, value, src ):
        self.push( TokenObject( name, value, src._token_lnum ) )

    def push_rule(self, name, count, src ):
        self.push( RuleObject( name, count, src._token_lnum ) )

    def alternative( self, rule, source ):
        # Do nothing, keep rule on top of the stack
##        rule_stack = self.rule_stack[:]
        if rule.is_root():
##             if DEBUG_MODE:
##                 print "ALT:", sym.sym_name[rule.codename], self.rule_stack
            builder_func = ASTRULES.get(rule.codename, None)
            if builder_func:
                builder_func(self, 1)
            else:
##                 if DEBUG_MODE:
##                     print "No reducing implementation for %s, just push it on stack" % (
##                         sym.sym_name[rule.codename])
                self.push_rule(rule.codename, 1, source)
        else:
            self.push_rule(rule.codename, 1, source)
##         if DEBUG_MODE > 1:
##             show_stack(rule_stack, self.rule_stack)
##             x = raw_input("Continue ?")
        return True

    def sequence(self, rule, source, elts_number):
        """ """
##        rule_stack = self.rule_stack[:]
        if rule.is_root():
##             if DEBUG_MODE:
##                 print "SEQ:", sym.sym_name[rule.codename]
            builder_func = ASTRULES.get(rule.codename, None)
            if builder_func:
                # print "REDUCING SEQUENCE %s" % sym.sym_name[rule.codename]
                builder_func(self, elts_number)
            else:
##                 if DEBUG_MODE:
##                     print "No reducing implementation for %s, just push it on stack" % (
##                         sym.sym_name[rule.codename])
                self.push_rule(rule.codename, elts_number, source)
        else:
            self.push_rule(rule.codename, elts_number, source)
##         if DEBUG_MODE > 1:
##             show_stack(rule_stack, self.rule_stack)
##             raw_input("Continue ?")
        return True

    def token(self, name, value, source):
##         if DEBUG_MODE:
##             print "TOK:", tok.tok_name[name], name, value
        self.push_tok(name, value, source)
        return True

    def eval_number(self, value):
        """temporary implementation
        eval_number intends to replace number = eval(value) ; return number
        """
        space = self.space
        base = 10
        if value.startswith("0x") or value.startswith("0X"):
            base = 16
        elif value.startswith("0"):
            base = 8
        if value.endswith('l') or value.endswith('L'):
            l = space.builtin.get('long')
            return space.call_function(l, space.wrap(value), space.wrap(base))
        if value.endswith('j') or value.endswith('J'):
            c = space.builtin.get('complex')
            return space.call_function(c, space.wrap(value))
        try:
            i = space.builtin.get('int')
            return space.call_function(i, space.wrap(value), space.wrap(base))
        except:
            f = space.builtin.get('float')
            return space.call_function(f, space.wrap(value))

    def is_basestring_const(self, expr):
        if not isinstance(expr,ast.Const):
            return False
        space = self.space
        return space.is_true(space.isinstance(expr.value,space.w_basestring))

    def wrap_string(self, obj):
        if self.space:
            return self.space.wrap(obj)
        else:
            return obj

    def wrap_none(self):
        if self.space:
            return self.space.w_None
        else:
            return None


def show_stack(before, after):
    """debugging helper function"""
    size1 = len(before)
    size2 = len(after)
    for i in range(max(size1, size2)):
        if i< size1:
            obj1 = str(before[i])
        else:
            obj1 = "-"
        if i< size2:
            obj2 = str(after[i])
        else:
            obj2 = "-"
        print "% 3d | %30s | %30s" % (i, obj1, obj2)

