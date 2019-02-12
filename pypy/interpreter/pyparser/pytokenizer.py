from pypy.interpreter.pyparser import automata
from pypy.interpreter.pyparser.parser import Token
from pypy.interpreter.pyparser.pygram import tokens
from pypy.interpreter.pyparser.pytoken import python_opmap
from pypy.interpreter.pyparser.error import TokenError, TokenIndentationError
from pypy.interpreter.pyparser.pytokenize import tabsize, whiteSpaceDFA, \
    triple_quoted, endDFAs, single_quoted, pseudoDFA
from pypy.interpreter.astcompiler import consts

NAMECHARS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_'
NUMCHARS = '0123456789'
ALNUMCHARS = NAMECHARS + NUMCHARS
EXTENDED_ALNUMCHARS = ALNUMCHARS + '-.'
WHITESPACES = ' \t\n\r\v\f'

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
    contstr, needcont = '', 0
    contline = None
    indents = [0]
    last_comment = ''
    parenstack = []

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

        if contstr:
            if not line:
                raise TokenError(
                    "end of file (EOF) while scanning triple-quoted string literal",
                    strstart[2], strstart[0], strstart[1]+1,
                    token_list, lnum-1)
            endmatch = endDFA.recognize(line)
            if endmatch >= 0:
                pos = end = endmatch
                tok = Token(tokens.STRING, contstr + line[:end], strstart[0],
                       strstart[1], line)
                token_list.append(tok)
                last_comment = ''
                contstr, needcont = '', 0
                contline = None
            elif (needcont and not line.endswith('\\\n') and
                               not line.endswith('\\\r\n')):
                tok = Token(tokens.ERRORTOKEN, contstr + line, strstart[0],
                       strstart[1], line)
                token_list.append(tok)
                last_comment = ''
                contstr = ''
                contline = None
                continue
            else:
                contstr = contstr + line
                contline = contline + line
                continue

        elif not parenstack and not continued:  # new statement
            if not line: break
            column = 0
            while pos < max:                   # measure leading whitespace
                if line[pos] == ' ': column = column + 1
                elif line[pos] == '\t': column = (column/tabsize + 1)*tabsize
                elif line[pos] == '\f': column = 0
                else: break
                pos = pos + 1
            if pos == max: break

            if line[pos] in '#\r\n':
                # skip comments or blank lines
                continue

            if column > indents[-1]:           # count indents or dedents
                indents.append(column)
                token_list.append(Token(tokens.INDENT, line[:pos], lnum, 0, line))
                last_comment = ''
            while column < indents[-1]:
                indents.pop()
                token_list.append(Token(tokens.DEDENT, '', lnum, pos, line))
                last_comment = ''
            if column != indents[-1]:
                err = "unindent does not match any outer indentation level"
                raise TokenIndentationError(err, line, lnum, column+1, token_list)

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
            if pseudomatch >= 0:                            # scan for tokens
                # JDR: Modified
                start = whiteSpaceDFA.recognize(line, pos)
                if start < 0:
                    start = pos
                end = pseudomatch

                if start == end:
                    raise TokenError("Unknown character", line,
                                     lnum, start + 1, token_list)

                pos = end
                token, initial = line[start:end], line[start]
                if initial in numchars or \
                   (initial == '.' and token != '.'):      # ordinary number
                    token_list.append(Token(tokens.NUMBER, token, lnum, start, line))
                    last_comment = ''
                elif initial in '\r\n':
                    if not parenstack:
                        tok = Token(tokens.NEWLINE, last_comment, lnum, start, line)
                        token_list.append(tok)
                    last_comment = ''
                elif initial == '#':
                    # skip comment
                    last_comment = token
                elif token in triple_quoted:
                    endDFA = endDFAs[token]
                    endmatch = endDFA.recognize(line, pos)
                    if endmatch >= 0:                     # all on one line
                        pos = endmatch
                        token = line[start:pos]
                        tok = Token(tokens.STRING, token, lnum, start, line)
                        token_list.append(tok)
                        last_comment = ''
                    else:
                        strstart = (lnum, start, line)
                        contstr = line[start:]
                        contline = line
                        break
                elif initial in single_quoted or \
                    token[:2] in single_quoted or \
                    token[:3] in single_quoted:
                    if token[-1] == '\n':                  # continued string
                        strstart = (lnum, start, line)
                        endDFA = (endDFAs[initial] or endDFAs[token[1]] or
                                   endDFAs[token[2]])
                        contstr, needcont = line[start:], 1
                        contline = line
                        break
                    else:                                  # ordinary string
                        tok = Token(tokens.STRING, token, lnum, start, line)
                        token_list.append(tok)
                        last_comment = ''
                elif initial in namechars:                 # ordinary name
                    token_list.append(Token(tokens.NAME, token, lnum, start, line))
                    last_comment = ''
                elif initial == '\\':                      # continued stmt
                    continued = 1
                elif initial == '$':
                    token_list.append(Token(tokens.REVDBMETAVAR, token,
                                       lnum, start, line))
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
                    token_list.append(Token(punct, token, lnum, start, line))
                    last_comment = ''
            else:
                start = whiteSpaceDFA.recognize(line, pos)
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
