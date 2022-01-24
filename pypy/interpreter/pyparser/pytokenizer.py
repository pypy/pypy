from pypy.interpreter.pyparser import automata
from pypy.interpreter.pyparser.parser import Token
from pypy.interpreter.pyparser.pygram import tokens
from pypy.interpreter.pyparser.pytoken import python_opmap
from pypy.interpreter.pyparser.error import TokenError, TokenIndentationError, TabError
from pypy.interpreter.pyparser.pytokenize import tabsize, alttabsize, whiteSpaceDFA, \
    triple_quoted, endDFAs, single_quoted, pseudoDFA
from pypy.interpreter.astcompiler import consts
from rpython.rlib import rutf8

NAMECHARS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_'
NUMCHARS = '0123456789'
ALNUMCHARS = NAMECHARS + NUMCHARS
EXTENDED_ALNUMCHARS = ALNUMCHARS + '-.'
WHITESPACES = ' \t\n\r\v\f'
TYPE_COMMENT_PREFIX = 'type'
TYPE_IGNORE = 'ignore'

def match_encoding_declaration(comment):
    """returns the declared encoding or None

    This function is a replacement for :
    >>> py_encoding = re.compile(r"coding[:=]\s*([-\w.]+)")
    >>> py_encoding.search(comment)
    """
    index = comment.find('coding')
    if index < 0:
        return None
    next_char = comment[index + 6]
    if next_char not in ':=':
        return None
    end_of_decl = comment[index + 7:]
    index = 0
    for char in end_of_decl:
        if char not in WHITESPACES:
            break
        index += 1
    else:
        return None
    encoding = ''
    for char in end_of_decl[index:]:
        if char in EXTENDED_ALNUMCHARS:
            encoding += char
        else:
            break
    if encoding != '':
        return encoding
    return None


def handle_type_comment(token, flags, lnum, start, line):
    sub_tokens = token.split(":", 1)
    if not (
        flags & consts.PyCF_TYPE_COMMENTS
        and len(sub_tokens) == 2
        and sub_tokens[0][1:].strip() == TYPE_COMMENT_PREFIX
    ):
        return None

    # A TYPE_IGNORE is "type: ignore" followed by the end of the token
    # or anything ASCII and non-alphanumeric. */

    # Leading whitespace is ignored
    type_decl = sub_tokens[1].lstrip()
    following_char = type_decl[len(TYPE_IGNORE):]
    if type_decl.startswith(TYPE_IGNORE) and (
        following_char == '' or
        ord(following_char[0]) < 0x80 and not following_char[0].isalnum()
    ):
        tok_type = tokens.TYPE_IGNORE
        type_decl = type_decl[len(TYPE_IGNORE):]
    else:
        tok_type = tokens.TYPE_COMMENT
    return Token(tok_type, type_decl, lnum, start, line)


def verify_utf8(token):
    try:
        rutf8.check_utf8(token, False)
    except rutf8.CheckError:
        return False
    return True

def bad_utf8(location_msg, line, lnum, pos, token_list, flags):
    msg = 'Non-UTF-8 code in %s' % location_msg
    if not (flags & consts.PyCF_FOUND_ENCODING):
        # this extra part of the message is added only if we found no
        # explicit encoding
        msg += (' but no encoding declared; see '
                'http://python.org/dev/peps/pep-0263/ for details')
    return TokenError(msg, line, lnum, pos, token_list)


def verify_identifier(token):
    # 1=ok; 0=not an identifier; -1=bad utf-8
    try:
        rutf8.check_utf8(token, False)
    except rutf8.CheckError:
        return -1
    from pypy.objspace.std.unicodeobject import _isidentifier
    return _isidentifier(token)


DUMMY_DFA = automata.DFA([], [])

def generate_tokens(lines, flags):
    """
    This is a rewrite of pypy.module.parser.pytokenize.generate_tokens since
    the original function is not RPYTHON (uses yield)
    It was also slightly modified to generate Token instances instead
    of the original 5-tuples -- it's now a 4-tuple of

    * the Token instance
    * the whole line as a string
    * the line number (the real one, counting continuation lines)
    * the position on the line of the end of the token.

    Original docstring ::

        The generate_tokens() generator requires one argment, readline, which
        must be a callable object which provides the same interface as the
        readline() method of built-in file objects. Each call to the function
        should return one line of input as a string.

        The generator produces 5-tuples with these members: the token type; the
        token string; a 2-tuple (srow, scol) of ints specifying the row and
        column where the token begins in the source; a 2-tuple (erow, ecol) of
        ints specifying the row and column where the token ends in the source;
        and the line on which the token was found. The line passed is the
        logical line; continuation lines are included.
    """

    token_list = []
    lnum = continued = 0
    namechars = NAMECHARS
    numchars = NUMCHARS
    contstrs, needcont = [], False
    indents = [0]
    altindents = [0]
    last_comment = ''
    parenstack = []
    async_hacks = flags & consts.PyCF_ASYNC_HACKS
    async_def = False
    async_def_nl = False
    async_def_indent = 0

    # make the annotator happy
    endDFA = DUMMY_DFA
    # make the annotator happy
    line = ''
    pos = 0
    lines.append("")
    strstart = (0, 0, "")
    for line in lines:
        lnum = lnum + 1
        line = universal_newline(line)
        pos, max = 0, len(line)
        switch_indents = 0

        if contstrs:
            if not line:
                raise TokenError(
                    "end of file (EOF) while scanning triple-quoted string literal",
                    strstart[2], strstart[0], strstart[1]+1,
                    token_list, lnum-1)
            endmatch = endDFA.recognize(line)
            if endmatch >= 0:
                pos = end = endmatch
                contstrs.append(line[:end])
                tok = Token(tokens.STRING, "".join(contstrs), strstart[0],
                       strstart[1], line, lnum, end)
                token_list.append(tok)
                last_comment = ''
                contstrs, needcont = [], False
            elif (needcont and not line.endswith('\\\n') and
                               not line.endswith('\\\r\n')):
                contstrs.append(line)
                tok = Token(tokens.ERRORTOKEN, "".join(contstrs), strstart[0],
                       strstart[1], line)
                token_list.append(tok)
                last_comment = ''
                contstrs = []
                continue
            else:
                contstrs.append(line)
                continue

        elif not parenstack and not continued:  # new statement
            if not line: break
            column = 0
            altcolumn = 0
            while pos < max:                   # measure leading whitespace
                if line[pos] == ' ':
                    column = column + 1
                    altcolumn = altcolumn + 1
                elif line[pos] == '\t':
                    column = (column/tabsize + 1)*tabsize
                    altcolumn = (altcolumn/alttabsize + 1)*alttabsize
                elif line[pos] == '\f':
                    column = 0
                else:
                    break
                pos = pos + 1
            if pos == max: break

            if line[pos] in '\r\n':
                # skip blank lines
                continue
            if line[pos] == '#':
                # skip full-line comment, but still check that it is valid utf-8
                if not verify_utf8(line):
                    raise bad_utf8("comment",
                                   line, lnum, pos, token_list, flags)
                type_comment_tok = handle_type_comment(line.lstrip(),
                                                      flags, lnum, pos, line)
                if type_comment_tok is None:
                    continue
                else:
                    switch_indents += 1

            if column == indents[-1]:
                if altcolumn != altindents[-1]:
                    raise TabError(lnum, pos, line)
            elif column > indents[-1]:           # count indents or dedents
                if altcolumn <= altindents[-1]:
                    raise TabError(lnum, pos, line)
                indents.append(column)
                altindents.append(altcolumn)
                token_list.append(Token(tokens.INDENT, line[:pos], lnum, 0, line, lnum, pos))
                last_comment = ''
            else:
                while column < indents[-1]:
                    indents.pop()
                    altindents.pop()
                    token_list.append(Token(tokens.DEDENT, '', lnum, pos, line))
                    last_comment = ''
                if column != indents[-1]:
                    err = "unindent does not match any outer indentation level"
                    raise TokenIndentationError(err, line, lnum, column+1, token_list)
                if altcolumn != altindents[-1]:
                    raise TabError(lnum, pos, line)
            if async_def_nl and async_def_indent >= indents[-1]:
                async_def = False
                async_def_nl = False
                async_def_indent = 0

        else:                                  # continued statement
            if not line:
                if parenstack:
                    _, lnum1, start1, line1 = parenstack[0]
                    raise TokenError("parenthesis is never closed", line1,
                                     lnum1, start1 + 1, token_list, lnum)
                raise TokenError("end of file (EOF) in multi-line statement", line,
                                 lnum, 0, token_list) # XXX why is the offset 0 here?
            continued = 0

        while pos < max:
            pseudomatch = pseudoDFA.recognize(line, pos)
            start = whiteSpaceDFA.recognize(line, pos)
            if pseudomatch >= 0:                            # scan for tokens
                # JDR: Modified
                if start < 0:
                    start = pos
                end = pseudomatch

                if start == end:
                    raise TokenError("Unknown character", line,
                                     lnum, start + 1, token_list)

                pos = end
                token, initial = line[start:end], line[start]
                if (initial in numchars or \
                   (initial == '.' and token != '.' and token != '...')):
                    # ordinary number
                    token_list.append(Token(tokens.NUMBER, token, lnum, start, line, lnum, end))
                    last_comment = ''
                elif initial in '\r\n':
                    if not parenstack:
                        if async_def:
                            async_def_nl = True
                        tok = Token(tokens.NEWLINE, last_comment, lnum, start, line)
                        token_list.append(tok)

                        # Shift the indent token to the next line
                        # when it is followed by a type_comment.
                        if (
                            switch_indents == 2
                            and len(token_list) >= 3
                            and token_list[-3].token_type == tokens.INDENT
                        ):
                            indent = token_list.pop(-3)
                            token_list.append(indent)
                        switch_indents = 0
                    last_comment = ''
                elif initial == '#':
                    # skip comment, but still check that it is valid utf-8
                    if not verify_utf8(token):
                        raise bad_utf8("comment",
                                       line, lnum, start, token_list, flags)
                    type_comment_tok = handle_type_comment(token, flags, lnum, start, line)
                    if type_comment_tok is not None:
                        switch_indents += 1
                        token_list.append(type_comment_tok)
                    else:
                        last_comment = token
                elif token in triple_quoted:
                    endDFA = endDFAs[token]
                    endmatch = endDFA.recognize(line, pos)
                    if endmatch >= 0:                     # all on one line
                        pos = endmatch
                        token = line[start:pos]
                        tok = Token(tokens.STRING, token, lnum, start, line, lnum, pos)
                        token_list.append(tok)
                        last_comment = ''
                    else:
                        strstart = (lnum, start, line)
                        contstrs = [line[start:]]
                        break
                elif initial in single_quoted or \
                    token[:2] in single_quoted or \
                    token[:3] in single_quoted:
                    if token[-1] == '\n':                  # continued string
                        strstart = (lnum, start, line)
                        endDFA = (endDFAs[initial] or endDFAs[token[1]] or
                                   endDFAs[token[2]])
                        contstrs, needcont = [line[start:]], True
                        break
                    else:                                  # ordinary string
                        tok = Token(tokens.STRING, token, lnum, start, line, lnum, pos)
                        token_list.append(tok)
                        last_comment = ''
                elif (initial in namechars or              # ordinary name
                      ord(initial) >= 0x80):               # unicode identifier
                    valid = verify_identifier(token)
                    if valid <= 0:
                        if valid == -1:
                            raise bad_utf8("identifier", line, lnum, start + 1,
                                           token_list, flags)
                        # valid utf-8, but it gives a unicode char that cannot
                        # be used in identifiers
                        raise TokenError("invalid character in identifier",
                                         line, lnum, start + 1, token_list)
                    # inside 'async def' function or no async_hacks
                    # so recognize them unconditionally.
                    if not async_hacks or async_def:
                        if token == 'async':
                            token_list.append(Token(tokens.ASYNC, token, lnum, start, line, lnum, end))
                        elif token == 'await':
                            token_list.append(Token(tokens.AWAIT, token, lnum, start, line, lnum, end))
                        else:
                            token_list.append(Token(tokens.NAME, token, lnum, start, line, lnum, end))
                    elif token == 'async':                 # async token, look ahead
                        #ahead token
                        if pos < max:
                            async_end = pseudoDFA.recognize(line, pos)
                            assert async_end >= 3
                            async_start = async_end - 3
                            assert async_start >= 0
                            ahead_token = line[async_start:async_end]
                            if ahead_token == 'def':
                                async_def = True
                                async_def_indent = indents[-1]
                                token_list.append(Token(tokens.ASYNC, token, lnum, start, line, lnum, end))
                            else:
                                token_list.append(Token(tokens.NAME, token, lnum, start, line, lnum, end))
                        else:
                            token_list.append(Token(tokens.NAME, token, lnum, start, line, lnum, end))
                    else:
                        token_list.append(Token(tokens.NAME, token, lnum, start, line, lnum, end))
                    last_comment = ''
                elif initial == '\\':                      # continued stmt
                    continued = 1
                elif initial == '$':
                    token_list.append(Token(tokens.REVDBMETAVAR, token,
                                       lnum, start, line, lnum, pos))
                    last_comment = ''
                else:
                    if initial in '([{':
                        parenstack.append((initial, lnum, start, line))
                    elif initial in ')]}':
                        if not parenstack:
                            raise TokenError("unmatched '%s'" % initial, line,
                                             lnum, start + 1, token_list)
                        opening, lnum1, start1, line1 = parenstack.pop()
                        if not ((opening == "(" and initial == ")") or
                                (opening == "[" and initial == "]") or
                                (opening == "{" and initial == "}")):
                            msg = "closing parenthesis '%s' does not match opening parenthesis '%s'" % (
                                        initial, opening)

                            if lnum1 != lnum:
                                msg += " on line " + str(lnum1)
                            raise TokenError(
                                    msg, line, lnum, start + 1, token_list)
                    if token in python_opmap:
                        punct = python_opmap[token]
                    else:
                        punct = tokens.OP
                    token_list.append(Token(punct, token, lnum, start, line, lnum, end))
                    last_comment = ''
            else:
                if start < 0:
                    start = pos
                if start<max and line[start] in single_quoted:
                    raise TokenError("end of line (EOL) while scanning string literal",
                             line, lnum, start+1, token_list)
                tok = Token(tokens.ERRORTOKEN, line[pos], lnum, pos, line)
                token_list.append(tok)
                last_comment = ''
                pos = pos + 1

    lnum -= 1
    if not (flags & consts.PyCF_DONT_IMPLY_DEDENT):
        if token_list and token_list[-1].token_type != tokens.NEWLINE:
            tok = Token(tokens.NEWLINE, '', lnum, 0, '\n')
            token_list.append(tok)
        for indent in indents[1:]:                # pop remaining indent levels
            token_list.append(Token(tokens.DEDENT, '', lnum, pos, line))
    tok = Token(tokens.NEWLINE, '', lnum, 0, '\n')
    token_list.append(tok)

    token_list.append(Token(tokens.ENDMARKER, '', lnum, pos, line))
    return token_list


def universal_newline(line):
    # show annotator that indexes below are non-negative
    line_len_m2 = len(line) - 2
    if line_len_m2 >= 0 and line[-2] == '\r' and line[-1] == '\n':
        return line[:line_len_m2] + '\n'
    line_len_m1 = len(line) - 1
    if line_len_m1 >= 0 and line[-1] == '\r':
        return line[:line_len_m1] + '\n'
    return line
