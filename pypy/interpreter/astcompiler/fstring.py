from pypy.interpreter.astcompiler import ast, consts
from pypy.interpreter.pyparser import parsestring
from pypy.interpreter import error


def add_constant_string(astbuilder, joined_pieces, w_string, atom_node):
    space = astbuilder.space
    is_unicode = space.isinstance_w(w_string, space.w_unicode)
    # Implement implicit string concatenation.
    if joined_pieces:
        prev = joined_pieces[-1]
        if is_unicode and isinstance(prev, ast.Str):
            w_string = space.add(prev.s, w_string)
            del joined_pieces[-1]
        elif not is_unicode and isinstance(prev, ast.Bytes):
            w_string = space.add(prev.s, w_string)
            del joined_pieces[-1]
    node = ast.Str if is_unicode else ast.Bytes
    joined_pieces.append(node(w_string, atom_node.get_lineno(),
                                        atom_node.get_column()))

def f_constant_string(astbuilder, joined_pieces, u, atom_node):
    space = astbuilder.space
    add_constant_string(astbuilder, joined_pieces, space.newunicode(u),
                        atom_node)

def f_string_compile(astbuilder, source, atom_node):
    # Note: a f-string is kept as a single literal up to here.
    # At this point only, we recursively call the AST compiler
    # on all the '{expr}' parts.  The 'expr' part is not parsed
    # or even tokenized together with the rest of the source code!
    from pypy.interpreter.pyparser import pyparse
    from pypy.interpreter.astcompiler.astbuilder import ast_from_node

    # complain if 'source' is only whitespace or an empty string
    for c in source:
        if c not in ' \t\n\r\v\f':
            break
    else:
        astbuilder.error("f-string: empty expression not allowed", atom_node)

    if astbuilder.recursive_parser is None:
        astbuilder.error("internal error: parser not available for parsing "
                   "the expressions inside the f-string", atom_node)
    source = '(%s)' % source.encode('utf-8')

    info = pyparse.CompileInfo("<fstring>", "eval",
                               consts.PyCF_SOURCE_IS_UTF8 |
                               consts.PyCF_IGNORE_COOKIE |
                               consts.PyCF_REFUSE_COMMENTS,
                               optimize=astbuilder.compile_info.optimize)
    parse_tree = astbuilder.recursive_parser.parse_source(source, info)
    return ast_from_node(astbuilder.space, parse_tree, info)

def f_string_expr(astbuilder, joined_pieces, u, start, atom_node, rec=0):
    conversion = -1     # the conversion char.  -1 if not specified.
    format_spec = None
    nested_depth = 0    # nesting level for braces/parens/brackets in exprs
    p = start
    while p < len(u):
        ch = u[p]
        p += 1
        if ch in u'[{(':
            nested_depth += 1
        elif nested_depth > 0 and ch in u']})':
            nested_depth -= 1
        elif nested_depth == 0 and ch in u'!:}':
            # special-case '!='
            if ch == u'!' and p < len(u) and u[p] == u'=':
                continue
            break     # normal way out of this loop
    else:
        ch = u'\x00'
    #
    if nested_depth > 0:
        astbuilder.error("f-string: mismatched '(', '{' or '['", atom_node)
    end_expression = p - 1
    if ch == u'!':
        if p + 1 < len(u):
            conversion = ord(u[p])
            ch = u[p + 1]
            p += 2
        if conversion not in (ord('s'), ord('r'), ord('a')):
            astbuilder.error("f-string: invalid conversion character: "
                             "expected 's', 'r', or 'a'", atom_node)
    if ch == u':':
        if rec >= 2:
            astbuilder.error("f-string: expressions nested too deeply",
                             atom_node)
        subpieces = []
        p = parse_f_string(astbuilder, subpieces, u, p, atom_node, rec + 1)
        format_spec = f_string_to_ast_node(astbuilder, subpieces, atom_node)
        ch = u[p] if p >= 0 else u'\x00'
        p += 1

    if ch != u'}':
        astbuilder.error("f-string: expecting '}'", atom_node)
    end_f_string = p
    assert end_expression >= start
    expr = f_string_compile(astbuilder, u[start:end_expression], atom_node)
    assert isinstance(expr, ast.Expression)
    fval = ast.FormattedValue(expr.body, conversion, format_spec,
                              atom_node.get_lineno(),
                              atom_node.get_column())
    joined_pieces.append(fval)
    return end_f_string

def parse_f_string(astbuilder, joined_pieces, u, start, atom_node, rec=0):
    space = astbuilder.space
    p1 = u.find(u'{', start)
    prestart = start
    while True:
        if p1 < 0:
            p1 = len(u)
        p2 = u.find(u'}', start, p1)
        if p2 >= 0:
            f_constant_string(astbuilder, joined_pieces, u[prestart:p2],
                              atom_node)
            pn = p2 + 1
            if pn < len(u) and u[pn] == u'}':    # '}}' => single '}'
                start = pn + 1
                prestart = pn
                continue
            return p2     # found a single '}', stop here
        f_constant_string(astbuilder, joined_pieces, u[prestart:p1], atom_node)
        if p1 == len(u):
            return -1     # no more '{' or '}' left
        pn = p1 + 1
        if pn < len(u) and u[pn] == u'{':    # '{{' => single '{'
            start = pn + 1
            prestart = pn
        else:
            assert u[p1] == u'{'
            start = f_string_expr(astbuilder, joined_pieces, u, pn,
                                  atom_node, rec)
            assert u[start - 1] == u'}'
            prestart = start
        p1 = u.find(u'{', start)

def f_string_to_ast_node(astbuilder, joined_pieces, atom_node):
    # remove empty Strs
    values = [node for node in joined_pieces
                   if not (isinstance(node, ast.Str) and not node.s)]
    if len(values) > 1:
        return ast.JoinedStr(values, atom_node.get_lineno(),
                                     atom_node.get_column())
    elif len(values) == 1:
        return values[0]
    else:
        assert len(joined_pieces) > 0    # they are all empty strings
        return joined_pieces[0]

def string_parse_literal(astbuilder, atom_node):
    space = astbuilder.space
    encoding = astbuilder.compile_info.encoding
    joined_pieces = []
    for i in range(atom_node.num_children()):
        try:
            w_next, saw_f = parsestring.parsestr(
                    space, encoding, atom_node.get_child(i).get_value())
        except error.OperationError as e:
            if not (e.match(space, space.w_UnicodeError) or
                    e.match(space, space.w_ValueError)):
                raise
            # Unicode/ValueError in literal: turn into SyntaxError
            raise astbuilder.error(e.errorstr(space), atom_node)
        if not saw_f:
            add_constant_string(astbuilder, joined_pieces, w_next, atom_node)
        else:
            p = parse_f_string(astbuilder, joined_pieces,
                                     space.unicode_w(w_next), 0,
                                     atom_node)
            if p != -1:
                astbuilder.error("f-string: single '}' is not allowed",
                                 atom_node)
    if len(joined_pieces) == 1:   # <= the common path
        return joined_pieces[0]   # ast.Str, Bytes or FormattedValue
    # with more than one piece, it is a combination of Str and
    # FormattedValue pieces---if there is a Bytes, then we got
    # an invalid mixture of bytes and unicode literals
    for node in joined_pieces:
        if isinstance(node, ast.Bytes):
            astbuilder.error("cannot mix bytes and nonbytes literals",
                             atom_node)
    return f_string_to_ast_node(astbuilder, joined_pieces, atom_node)
