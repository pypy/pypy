from pypy.interpreter.typedef import TypeDef, GetSetProperty, interp_attrproperty
from pypy.interpreter.astcompiler import ast, consts
from pypy.interpreter.pyparser.error import SyntaxError


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


def parse_dotted_names(tokens, builder):
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
        if token.name != builder.parser.tokens['DOT']:
            break
        token = tokens[index+1]
        assert isinstance(token, TokenObject)
        name += '.'
        value = token.get_value()
        name += value
    return (index, name)

def parse_argument(tokens, builder):
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
        elif cur_token.name == builder.parser.tokens['COMMA']:
            index += 1
            continue
        elif cur_token.name == builder.parser.tokens['EQUAL']:
            index += 1
            building_kw = True
            continue
        elif cur_token.name == builder.parser.tokens['STAR'] or cur_token.name == builder.parser.tokens['DOUBLESTAR']:
            index += 1
            if cur_token.name == builder.parser.tokens['STAR']:
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


def parse_fpdef(tokens, index, builder):
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
        if token.name == builder.parser.tokens['LPAR']:       # nested item
            index, node = parse_fpdef(tokens, index, builder)
        elif token.name == builder.parser.tokens['RPAR']:     # end of current nesting
            break
        else:                            # name
            val = token.get_value()
            node = ast.AssName(val, consts.OP_ASSIGN, token.lineno)
        nodes.append(node)

        token = tokens[index]
        index += 1
        assert isinstance(token, TokenObject)
        if token.name == builder.parser.tokens['COMMA']:
            comma = True
        else:
            assert token.name == builder.parser.tokens['RPAR']
            break
    if len(nodes) == 1 and not comma:
        node = nodes[0]
    else:
        node = ast.AssTuple(nodes, token.lineno)
    return index, node

def parse_arglist(tokens, builder):
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
        elif cur_token.name == builder.parser.tokens['COMMA']:
            # We could skip test COMMA by incrementing index cleverly
            # but we might do some experiment on the grammar at some point
            continue
        elif cur_token.name == builder.parser.tokens['LPAR']:
            index, node = parse_fpdef(tokens, index, builder)
            names.append(node)
        elif cur_token.name == builder.parser.tokens['STAR'] or cur_token.name == builder.parser.tokens['DOUBLESTAR']:
            if cur_token.name == builder.parser.tokens['STAR']:
                cur_token = tokens[index]
                assert isinstance(cur_token, TokenObject)
                index += 1
                if cur_token.name == builder.parser.tokens['NAME']:
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
            if cur_token.name != builder.parser.tokens['DOUBLESTAR']:
                raise SyntaxError("Unexpected token", cur_token.lineno,
                                  cur_token.col)
            cur_token = tokens[index]
            index += 1
            assert isinstance(cur_token, TokenObject)
            if cur_token.name == builder.parser.tokens['NAME']:
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
        elif cur_token.name == builder.parser.tokens['NAME']:
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


def parse_listcomp(tokens, builder):
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
                if tok2.name != builder.parser.tokens['COMMA']:
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


def peek_atoms(builder, nb):
    atoms = []

    i = nb
    current = len(builder.rule_stack) - 1
    while i > 0:
        assert current >= 0
        obj = builder.rule_stack[current]
        if isinstance(obj, BaseRuleObject):
            i += obj.count
        else:
            atoms.append( obj )
        i -= 1
        current -= 1

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

def parse_attraccess(tokens, builder):
    """parses token list like ['a', '.', 'b', '.', 'c', ...]

    and returns an ast node : ast.Getattr(Getattr(Name('a'), 'b'), 'c' ...)

    Well, no, that's lying.  In reality this is also parsing everything
    that goes in the grammar 'trailer' rule.
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
        if isinstance(token, TokenObject) and token.name == builder.parser.tokens['DOT']:
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



## Stack elements definitions ###################################

class BaseRuleObject(ast.Node):
    """Base class for unnamed rules"""
    def __init__(self, count, lineno):
        self.count = count
        self.lineno = lineno # src.getline()
        self.col = 0  # src.getcol()


class RuleObject(BaseRuleObject):
    """A simple object used to wrap a rule or token"""
    def __init__(self, name, count, lineno, parser):
        BaseRuleObject.__init__(self, count, lineno)
        self.rulename = name
        self.parser = parser

    def __str__(self):
        return "<Rule: %s/%d>" % ( self.parser.symbol_repr(self.rulename), self.count)

    def __repr__(self):
        return "<Rule: %s/%d>" % ( self.parser.symbol_repr(self.rulename), self.count)


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

    def __init__(self, name, value, lineno, parser):
        self.name = name
        self.value = value
        self.count = 0
        # self.line = 0 # src.getline()
        self.col = 0  # src.getcol()
        self.lineno = lineno
        self.parser = parser

    def get_name(self):
        tokname = self.parser.tok_name.get(self.name, str(self.name))
        return self.parser.tok_rvalues.get(self.name, tokname)

    def get_value(self):
        value = self.value
        if value is None:
            value = ''
        return value

    def descr_fget_value(space, self):
        value = self.get_value()
        return space.wrap(value)

    def __str__(self):
        return "<Token: (%s,%s)>" % (self.get_name(), self.value)

    def __repr__(self):
        return "<Token: (%r,%s)>" % (self.get_name(), self.value)

TokenObject.typedef = TypeDef('BuildToken',
                              name=interp_attrproperty('name', cls=TokenObject),
                              lineno=interp_attrproperty('lineno', cls=TokenObject),
                              value=GetSetProperty(TokenObject.descr_fget_value))

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
        return repr(self)

    def __repr__(self):
        return "<ArgList: (%s, %s, %s)>" % (self.arguments,
                                            self.stararg,
                                            self.dstararg)

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

