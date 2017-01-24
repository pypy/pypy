from pypy.interpreter.astcompiler import ast, consts
from pypy.interpreter.pyparser import parsestring
from pypy.interpreter import error
from pypy.interpreter import unicodehelper
from rpython.rlib.rstring import UnicodeBuilder


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
                               consts.PyCF_IGNORE_COOKIE,
                               optimize=astbuilder.compile_info.optimize)
    parser = astbuilder.recursive_parser
    parse_tree = parser.parse_source(source, info)
    return ast_from_node(astbuilder.space, parse_tree, info,
                         recursive_parser=parser)


def unexpected_end_of_string(astbuilder, atom_node):
    astbuilder.error("f-string: expecting '}'", atom_node)


def fstring_find_expr(astbuilder, fstr, atom_node, rec):
    # Parse the f-string at fstr.current_index.  We know it starts an
    # expression (so it must be at '{'). Returns the FormattedValue node,
    # which includes the expression, conversion character, and
    # format_spec expression.
    conversion = -1      # the conversion char.  -1 if not specified.
    format_spec = None

    # 0 if we're not in a string, else the quote char we're trying to
    # match (single or double quote).
    quote_char = 0

    # If we're inside a string, 1=normal, 3=triple-quoted.
    string_type = 0

    # Keep track of nesting level for braces/parens/brackets in
    # expressions.
    nested_depth = 0

    # Can only nest one level deep.
    if rec >= 2:
        astbuilder.error("f-string: expressions nested too deeply", atom_node)

    # The first char must be a left brace, or we wouldn't have gotten
    # here. Skip over it.
    u = fstr.unparsed
    i = fstr.current_index
    assert u[i] == u'{'
    i += 1

    expr_start = i
    while i < len(u):

        # Loop invariants.
        assert nested_depth >= 0
        if quote_char:
            assert string_type == 1 or string_type == 3
        else:
            assert string_type == 0

        ch = u[i]
        # Nowhere inside an expression is a backslash allowed.
        if ch == u'\\':
            # Error: can't include a backslash character, inside
            # parens or strings or not.
            astbuilder.error("f-string expression part "
                             "cannot include a backslash", atom_node)

        if quote_char:
            # We're inside a string. See if we're at the end.
            # <a long comment goes here about how we're duplicating
            # some existing logic>
            if ord(ch) == quote_char:
                # Does this match the string_type (single or triple
                # quoted)?
                if string_type == 3:
                    if i + 2 < len(u) and u[i + 1] == u[i + 2] == ch:
                        # We're at the end of a triple quoted string.
                        i += 3
                        string_type = 0
                        quote_char = 0
                        continue
                else:
                    # We're at the end of a normal string.
                    i += 1
                    string_type = 0
                    quote_char = 0
                    continue
        elif ch == u"'" or ch == u'"':
            # Is this a triple quoted string?
            if i + 2 < len(u) and u[i + 1] == u[i + 2] == ch:
                string_type = 3
                i += 2
            else:
                # Start of a normal string.
                string_type = 1
            # Start looking for the end of the string.
            quote_char = ord(ch)
        elif ch in u"[{(":
            nested_depth += 1
        elif nested_depth != 0 and ch in u"]})":
            nested_depth -= 1
        elif ch == u'#':
            # Error: can't include a comment character, inside parens
            # or not.
            astbuilder.error("f-string expression part cannot include '#'",
                             atom_node)
        elif nested_depth == 0 and ch in u"!:}":
            # First, test for the special case of "!=". Since '=' is
            # not an allowed conversion character, nothing is lost in
            # this test.
            if ch == '!' and i + 1 < len(u) and u[i+1] == u'=':
                # This isn't a conversion character, just continue.
                i += 1
                continue
            # Normal way out of this loop.
            break
        #else:
        #   This isn't a conversion character, just continue.
        i += 1

    # If we leave this loop in a string or with mismatched parens, we
    # don't care. We'll get a syntax error when compiling the
    # expression. But, we can produce a better error message, so
    # let's just do that.
    if quote_char:
        astbuilder.error("f-string: unterminated string", atom_node)

    if nested_depth:
        astbuilder.error("f-string: mismatched '(', '{' or '['", atom_node)

    if i >= len(u):
        unexpected_end_of_string(astbuilder, atom_node)

    # Compile the expression as soon as possible, so we show errors
    # related to the expression before errors related to the
    # conversion or format_spec.
    expr = f_string_compile(astbuilder, u[expr_start:i], atom_node)
    assert isinstance(expr, ast.Expression)

    # Check for a conversion char, if present.
    if u[i] == u'!':
        i += 1
        if i >= len(u):
            unexpected_end_of_string(astbuilder, atom_node)

        conversion = ord(u[i])
        i += 1
        if conversion not in (ord('s'), ord('r'), ord('a')):
            astbuilder.error("f-string: invalid conversion character: "
                             "expected 's', 'r', or 'a'", atom_node)

    # Check for the format spec, if present.
    if i >= len(u):
        unexpected_end_of_string(astbuilder, atom_node)
    if u[i] == u':':
        i += 1
        if i >= len(u):
            unexpected_end_of_string(astbuilder, atom_node)
        fstr.current_index = i
        subpieces = []
        parse_f_string(astbuilder, subpieces, fstr, atom_node, rec + 1)
        format_spec = f_string_to_ast_node(astbuilder, subpieces, atom_node)
        i = fstr.current_index

    if i >= len(u) or u[i] != u'}':
        unexpected_end_of_string(astbuilder, atom_node)

    # We're at a right brace. Consume it.
    i += 1
    fstr.current_index = i

    # And now create the FormattedValue node that represents this
    # entire expression with the conversion and format spec.
    return ast.FormattedValue(expr.body, conversion, format_spec,
                              atom_node.get_lineno(),
                              atom_node.get_column())


def fstring_find_literal(astbuilder, fstr, atom_node, rec):
    # Return the next literal part.  Updates the current index inside 'fstr'.
    # Differs from CPython: this version handles double-braces on its own.
    u = fstr.unparsed
    literal_start = fstr.current_index
    in_named_escape = False

    # Get any literal string. It ends when we hit an un-doubled left
    # brace (which isn't part of a unicode name escape such as
    # "\N{EULER CONSTANT}"), or the end of the string.
    i = literal_start
    builder = UnicodeBuilder()
    while i < len(u):
        ch = u[i]
        if (not in_named_escape and ch == u'{' and i - literal_start >= 2
                and u[i - 2] == u'\\' and u[i - 1] == u'N'):
            in_named_escape = True
        elif in_named_escape and ch == u'}':
            in_named_escape = False
        elif ch == u'{' or ch == u'}':
            # Check for doubled braces, but only at the top level. If
            # we checked at every level, then f'{0:{3}}' would fail
            # with the two closing braces.
            if rec == 0 and i + 1 < len(u) and u[i + 1] == ch:
                i += 1   # skip over the second brace
            elif rec == 0 and ch == u'}':
                # Where a single '{' is the start of a new expression, a
                # single '}' is not allowed.
                astbuilder.error("f-string: single '}' is not allowed",
                                 atom_node)
            else:
                # We're either at a '{', which means we're starting another
                # expression; or a '}', which means we're at the end of this
                # f-string (for a nested format_spec).
                break
        builder.append(ch)
        i += 1

    fstr.current_index = i
    literal = builder.build()
    if not fstr.raw_mode and u'\\' in literal:
        # xxx messy
        space = astbuilder.space
        literal = literal.encode('utf-8')
        literal = parsestring.decode_unicode_utf8(space, literal, 0,
                                                  len(literal))
        literal = unicodehelper.decode_unicode_escape(space, literal)
    return literal


def fstring_find_literal_and_expr(astbuilder, fstr, atom_node, rec):
    # Return a tuple with the next literal part, and optionally the
    # following expression node.  Updates the current index inside 'fstr'.
    literal = fstring_find_literal(astbuilder, fstr, atom_node, rec)

    u = fstr.unparsed
    i = fstr.current_index
    if i >= len(u) or u[i] == u'}':
        # We're at the end of the string or the end of a nested
        # f-string: no expression.
        expr = None
    else:
        # We must now be the start of an expression, on a '{'.
        assert u[i] == u'{'
        expr = fstring_find_expr(astbuilder, fstr, atom_node, rec)
    return literal, expr


def parse_f_string(astbuilder, joined_pieces, fstr, atom_node, rec=0):
    # In our case, parse_f_string() and fstring_find_literal_and_expr()
    # could be merged into a single function with a clearer logic.  It's
    # done this way to follow CPython's source code more closely.

    space = astbuilder.space
    if not space.config.objspace.fstrings:
        raise oefmt(space.w_SystemError,
                    "f-strings have been disabled in this version of pypy "
                    "with the translation option --no-objspace-fstrings.  "
                    "The PyPy team (and CPython) thinks f-strings don't "
                    "add any security risks, but we leave it to you to "
                    "convince whoever translated this pypy that it is "
                    "really the case")

    while True:
        literal, expr = fstring_find_literal_and_expr(astbuilder, fstr,
                                                      atom_node, rec)

        # add the literal part
        f_constant_string(astbuilder, joined_pieces, literal, atom_node)

        if expr is None:
            break         # We're done with this f-string.

        joined_pieces.append(expr)

    # If recurse_lvl is zero, then we must be at the end of the
    # string. Otherwise, we must be at a right brace.
    if rec == 0 and fstr.current_index < len(fstr.unparsed) - 1:
        astbuilder.error("f-string: unexpected end of string", atom_node)

    if rec != 0 and (fstr.current_index >= len(fstr.unparsed) or
                     fstr.unparsed[fstr.current_index] != u'}'):
        astbuilder.error("f-string: expecting '}'", atom_node)


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
    try:
        for i in range(atom_node.num_children()):
            w_next = parsestring.parsestr(
                    space, encoding, atom_node.get_child(i).get_value())
            if not isinstance(w_next, parsestring.W_FString):
                add_constant_string(astbuilder, joined_pieces, w_next,
                                    atom_node)
            else:
                parse_f_string(astbuilder, joined_pieces, w_next, atom_node)

    except error.OperationError as e:
        if e.match(space, space.w_UnicodeError):
            kind = 'unicode error'
        elif e.match(space, space.w_ValueError):
            kind = 'value error'
        else:
            raise
        # Unicode/ValueError in literal: turn into SyntaxError
        e.normalize_exception(space)
        errmsg = space.str_w(space.str(e.get_w_value(space)))
        raise astbuilder.error('(%s) %s' % (kind, errmsg), atom_node)

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
