from pypy.interpreter.pyparser import automata
from pypy.interpreter.pyparser.parser import Token
from pypy.interpreter.pyparser.pygram import tokens
from pypy.interpreter.pyparser.pytoken import python_opmap
from pypy.interpreter.pyparser.error import TokenError, TokenIndentationError, TabError
from pypy.interpreter.pyparser.pytokenize import tabsize, alttabsize, whiteSpaceDFA, \
    triple_quoted, endDFAs, single_quoted, pseudoDFA
from pypy.interpreter.astcompiler import consts
from rpython.rlib import rutf8, objectmodel

NAMECHARS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_'
NUMCHARS = '0123456789'
ALNUMCHARS = NAMECHARS + NUMCHARS
EXTENDED_ALNUMCHARS = ALNUMCHARS + '-.'
WHITESPACES = ' \t\n\r\v\f'
TYPE_COMMENT_PREFIX = 'type'
TYPE_IGNORE = 'ignore'

TRIPLE_QUOTE_UNTERMINATED_ERROR = "unterminated triple-quoted string literal"
SINGLE_QUOTE_UNTERMINATED_ERROR = "unterminated string literal"
EOF_MULTI_LINE_STATEMENT_ERROR = "unexpected end of file (EOF) in multi-line statement"

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


def verify_identifier(token, line, lnum, start, token_list, flags):
    # -2=ok; positive=not an identifier; -1=bad utf-8
    from pypy.module.unicodedata.interp_ucd import unicodedb
    try:
        rutf8.check_utf8(token, False)
    except rutf8.CheckError:
        raise bad_utf8("identifier", line, lnum, start + 1,
                       token_list, flags)
    if not token:
        return
    first = token[0]
    it = rutf8.Utf8StringIterator(token)
    code = it.next()
    if not (unicodedb.isxidstart(code) or first == '_'):
        raise_invalid_unicode_char(code, line, lnum, start, token_list)
    pos = it.get_pos()
    for ch in it:
        if not unicodedb.isxidcontinue(ch):
            raise_invalid_unicode_char(ch, line, lnum, start + pos, token_list)
        pos = it.get_pos()

def raise_invalid_unicode_char(code, line, lnum, start, token_list):
    from pypy.module.unicodedata.interp_ucd import unicodedb
    # valid utf-8, but it gives a unicode char that cannot
    # be used in identifiers
    assert code >= 0
    h = hex(code)[2:].upper()
    if len(h) < 4:
        h = "0" * (4 - len(h)) + h
    if not unicodedb.isprintable(code):
        msg = "invalid non-printable character U+%s" % h
    else:
        msg = "invalid character '%s' (U+%s)" % (
            rutf8.unichr_as_utf8(code), h)
    raise TokenError(msg, line, lnum, start + 1, token_list)

def raise_unterminated_string(is_triple_quoted, line, lineno, column, tokens,
        end_lineno, end_offset=0):
    # same arguments as TokenError, ie 1-based offsets
    if is_triple_quoted:
        msg = TRIPLE_QUOTE_UNTERMINATED_ERROR + " (detected at line %s)" % (end_lineno, )
    else:
        msg = SINGLE_QUOTE_UNTERMINATED_ERROR + " (detected at line %s)" % (end_lineno, )
    raise TokenError(msg, line, lineno, column, tokens, end_lineno, end_offset)

def potential_identifier_char(ch):
    return (ch in NAMECHARS or  # ordinary name
            ord(ch) >= 0x80)    # unicode

def raise_unknown_character(line, start, lnum, token_list, flags):
    from pypy.module.unicodedata.interp_ucd import unicodedb
    code = ord(line[start])
    if code < 128:
        try:
            rutf8.check_utf8(line, False, start=start)
        except rutf8.CheckError:
            raise bad_utf8("line", line, lnum, start + 1,
                           token_list, flags)
        code = rutf8.codepoint_at_pos(line, start)
    raise_invalid_unicode_char(code, line, lnum, start, token_list)

DUMMY_DFA = automata.DFA([], [])

class Finish(Exception):
    pass

class Tokenizer(object):
    def __init__(self, flags):
        self.flags = flags

        self.token_list = []
        self.lnum = 0
        self.continued = False
        self.indents = [0]
        self.altindents = [0]
        self.last_comment = ''

        # contains the tokens of the opening parens
        self.parenstack = []
        self.async_hacks = flags & consts.PyCF_ASYNC_HACKS
        self.async_def = False
        self.async_def_nl = False
        self.async_def_indent = 0

        self.line = ''

        # attributes for dealing with contiuations of string literals
        # (triple-quoted or with \\)
        self.string_end_dfa = None # for matching the end of the string
        self.contstrs = []
        self.need_line_cont = False
        self.strstart_linenumber = 0
        self.strstart_offset = 0
        self.strstart_starting_line = ""
        self.strstart_is_triple_quoted = False

        self.cont_line_col = 0

    def tokenize_lines(self, lines):
        self.lines = lines
        lines.append("")
        for lines_index, line in enumerate(lines):
            self.lines_index = lines_index
            try:
                self.tokenize_line(line)
            except Finish:
                break
        else:
            if not objectmodel.we_are_translated():
                import pdb;pdb.set_trace()
            assert 0
        return self.finish()

    def tokenize_line(self, line):
        self.lnum += 1
        line = universal_newline(line)
        self.line = line
        self.pos, self.max = 0, len(line)
        self.switch_indents = 0
        if self.string_end_dfa:
            done = self._tokenize_string_continuation(line)
            if done:
                return
        elif not self.parenstack and not self.continued:  # new statement
            done = self._tokenize_new_statement(line)
            if done:
                return
        else:                                  # continued statement
            self._tokenize_continued_statement(line)
        self._tokenize_regular(line)

    def finish(self):
        line = self.line
        self.lnum -= 1
        if not (self.flags & consts.PyCF_DONT_IMPLY_DEDENT):
            if self.token_list and self.token_list[-1].token_type != tokens.NEWLINE:
                self._add_token(tokens.NEWLINE, '', self.lnum, 0, '\n')
            for indent in self.indents[1:]:                # pop remaining indent levels
                self._add_token(tokens.DEDENT, '', self.lnum, self.pos, line)
        self._add_token(tokens.NEWLINE, '', self.lnum, 0, '\n')
        self._add_token(tokens.ENDMARKER, '', self.lnum, self.pos, line)
        return self.token_list

    def _add_token(self, token_type, value, lineno, column, line, end_lineno=-1, end_column=-1, level_adjustment=0):
        tok = Token(token_type, value, lineno, column, line, end_lineno, end_column, len(self.parenstack) + level_adjustment)
        self.token_list.append(tok)
        return tok

    def _raise_token_error(self, msg, line, lineno, column, end_lineno=0, end_offset=0):
        raise TokenError(msg, line, lineno, column, self.token_list, end_lineno, end_offset)

    def _contstr_start(self, string_end_dfa, offset, starting_line, is_triple_quoted, strstart):
        assert self.string_end_dfa is None
        self.string_end_dfa = string_end_dfa
        self.strstart_linenumber = self.lnum
        self.strstart_offset = offset
        self.strstart_starting_line = starting_line
        self.strstart_is_triple_quoted = is_triple_quoted
        self.contstrs = [strstart]
        self.need_line_cont = not is_triple_quoted

    def _contstr_finish(self, rest):
        self.contstrs.append(rest)
        res = "".join(self.contstrs)
        self.string_end_dfa = None
        self.contstrs = []
        self.need_line_cont = False
        return res

    def _tokenize_string_continuation(self, line):
        if not line:
            raise_unterminated_string(self.strstart_is_triple_quoted, self.strstart_starting_line, self.strstart_linenumber,
                                      self.strstart_offset + 1, self.token_list,
                                      self.lnum - 1, len(line))
        endmatch = self.string_end_dfa.recognize(line)
        if endmatch >= 0:
            self.pos = end = endmatch
            content = self._contstr_finish(line[:end])
            self._add_token(tokens.STRING, content, self.strstart_linenumber,
                   self.strstart_offset, line, self.lnum, end)
            self.last_comment = ''
        elif (self.need_line_cont and not line.endswith('\\\n') and
                           not line.endswith('\\\r\n')):
            raise_unterminated_string(self.strstart_is_triple_quoted, self.strstart_starting_line, self.strstart_linenumber,
                                      self.strstart_offset + 1, self.token_list,
                                      self.lnum, len(line))
            assert 0, 'unreachable'
        else:
            self.contstrs.append(line)
            return True # done with this line
        return False

    def _tokenize_new_statement(self, line):
        if not line:
            raise Finish
        column = self.cont_line_col
        altcolumn = self.cont_line_col
        while self.pos < self.max:                   # measure leading whitespace
            if line[self.pos] == ' ':
                column = column + 1
                altcolumn = altcolumn + 1
            elif line[self.pos] == '\t':
                column = (column/tabsize + 1)*tabsize
                altcolumn = (altcolumn/alttabsize + 1)*alttabsize
            elif line[self.pos] == '\f':
                column = 0
            else:
                break
            self.pos += 1
        if self.pos == self.max:
            raise Finish

        if line[self.pos] in '#\r\n':
            # skip blank lines
            if line[self.pos] == '#':
                # skip full-line comment, but still check that it is valid utf-8
                if not verify_utf8(line):
                    raise bad_utf8("comment",
                                   line, self.lnum, self.pos, self.token_list, self.flags)
                type_comment_tok = handle_type_comment(line.lstrip(),
                                                      self.flags, self.lnum, self.pos, line)
                if type_comment_tok is None:
                    return True
                else:
                    self.switch_indents += 1
            else:
                return True
        if line[self.pos] == '\\' and line[self.pos + 1] in '\r\n':
            # first non-whitespace char and last char in line is \
            if self.lines[self.lines_index + 1] not in ("\r\n", "\n", "\x0C\n"):
                # continuation marker after spaces increase the
                # indentation level if column > 0
                if column == 0:
                    pass
                elif self.pos != self.cont_line_col:
                    self.indents.append(self.pos)
                    self.altindents.append(self.pos)
                    self._add_token(tokens.INDENT, line[:self.pos], self.lnum, 0, line[:self.pos] + self.lines[self.lines_index + 1], self.lnum, self.pos)
                    self.cont_line_col = self.pos
                    self.continued = True
                    return True
            if self.lines[self.lines_index + 1] != "":
                # skip lines that are only a line continuation char
                # followed by an empty line (not last line)
                return True
        else:
            self.cont_line_col = 0
        if column == self.indents[-1]:
            if altcolumn != self.altindents[-1]:
                raise TabError(self.lnum, self.pos, line)
        elif column > self.indents[-1]:           # count indents or dedents
            if altcolumn <= self.altindents[-1]:
                raise TabError(self.lnum, self.pos, line)
            self.indents.append(column)
            self.altindents.append(altcolumn)
            self._add_token(tokens.INDENT, line[:self.pos], self.lnum, 0, line, self.lnum, self.pos)
            self.last_comment = ''
        else:
            while column < self.indents[-1]:
                self.indents.pop()
                self.altindents.pop()
                self._add_token(tokens.DEDENT, '', self.lnum, self.pos, line)
                self.last_comment = ''
            if column != self.indents[-1]:
                err = "unindent does not match any outer indentation level"
                raise TokenIndentationError(err, line, self.lnum, column+1, self.token_list)
            if altcolumn != self.altindents[-1]:
                raise TabError(self.lnum, self.pos, line)
        if self.async_def_nl and self.async_def_indent >= self.indents[-1]:
            self.async_def = False
            self.async_def_nl = False
            self.async_def_indent = 0
        return False

    def _tokenize_continued_statement(self, line):
        if not line:
            if self.parenstack:
                openparen = self.parenstack[0]
                parenkind = openparen.value[0]
                lnum1 = openparen.lineno
                start1 = openparen.column
                line1 = openparen.line
                self._raise_token_error("'%s' was never closed" % (parenkind, ), line1,
                                 lnum1, start1 + 1, self.lnum)
            prevline = self.lines[self.lines_index - 1]
            self._raise_token_error(EOF_MULTI_LINE_STATEMENT_ERROR , prevline,
                             self.lnum - 1, len(prevline) - 1) # XXX why is the offset 0 here?
        self.continued = False

    def _tokenize_regular(self, line):
        while self.pos < self.max:
            pseudomatch = pseudoDFA.recognize(line, self.pos)
            start = whiteSpaceDFA.recognize(line, self.pos)
            if pseudomatch >= 0:                            # scan for tokens
                done = self._classify_token(line, start, pseudomatch)
                if done:
                    return
            else:
                if start < 0:
                    start = self.pos
                if start<self.max and line[start] in single_quoted:
                    raise_unterminated_string(False, line, self.lnum, start+1,
                                              self.token_list, self.lnum, len(line))
                if line[self.pos] == "0":
                    self._raise_token_error("leading zeros in decimal integer literals are not permitted; use an 0o prefix for octal integers",
                            line, self.lnum, self.pos+1)
                self._add_token(tokens.ERRORTOKEN, line[self.pos], self.lnum, self.pos, line)
                self.last_comment = ''
                self.pos += 1

    def _classify_token(self, line, start, pseudomatch):
        if start < 0:
            start = self.pos
        end = pseudomatch

        if start == end:
            if line[start] == "\\":
                self._raise_token_error("unexpected character after line continuation character", line,
                                 self.lnum, start + 2)

            raise_unknown_character(line, start, self.lnum, self.token_list, self.flags)

        self.pos = end
        token, initial = line[start:end], line[start]
        if (initial in NUMCHARS or \
           (initial == '.' and token != '.' and token != '...')):
            # ordinary number
            self._add_token(tokens.NUMBER, token, self.lnum, start, line, self.lnum, end)
            _maybe_raise_number_error(token, line, self.lnum, start, end, self.token_list)
            self.last_comment = ''
        elif initial in '\r\n':
            if not self.parenstack:
                if self.async_def:
                    self.async_def_nl = True
                self._add_token(tokens.NEWLINE, self.last_comment, self.lnum, start, line)

                # Shift the indent token to the next line
                # when it is followed by a type_comment.
                if (
                    self.switch_indents == 2
                    and len(self.token_list) >= 3
                    and self.token_list[-3].token_type == tokens.INDENT
                ):
                    indent = self.token_list.pop(-3)
                    self.token_list.append(indent)
                self.switch_indents = 0
            self.last_comment = ''
        elif initial == '#':
            # skip comment, but still check that it is valid utf-8
            if not verify_utf8(token):
                raise bad_utf8("comment",
                               line, self.lnum, start, self.token_list, self.flags)
            type_comment_tok = handle_type_comment(token, self.flags, self.lnum, start, line)
            if type_comment_tok is not None:
                self.switch_indents += 1
                self.token_list.append(type_comment_tok)
            else:
                self.last_comment = token
        elif token in triple_quoted:
            string_end_dfa = endDFAs[token]
            endmatch = string_end_dfa.recognize(line, self.pos)
            if endmatch >= 0:                     # all on one line
                self.pos = endmatch
                token = line[start:self.pos]
                self._add_token(tokens.STRING, token, self.lnum, start, line, self.lnum, self.pos)
                self.last_comment = ''
            else:
                self._contstr_start(string_end_dfa, start, line, True, line[start:])
                return True
        elif initial in single_quoted or \
            token[:2] in single_quoted or \
            token[:3] in single_quoted:
            if token[-1] == '\n':                  # continued string
                string_end_dfa = (endDFAs[initial] or endDFAs[token[1]] or
                           endDFAs[token[2]])
                self._contstr_start(string_end_dfa, start, line, False, line[start:])
                return True
            else:                                  # ordinary string
                self._add_token(tokens.STRING, token, self.lnum, start, line, self.lnum, self.pos)
                self.last_comment = ''
        elif potential_identifier_char(initial): # unicode identifier
            verify_identifier(token, line, self.lnum, start, self.token_list, self.flags)
            # inside 'async def' function or no async_hacks
            # so recognize them unconditionally.
            if not self.async_hacks or self.async_def:
                if token == 'async':
                    self._add_token(tokens.ASYNC, token, self.lnum, start, line, self.lnum, end)
                elif token == 'await':
                    self._add_token(tokens.AWAIT, token, self.lnum, start, line, self.lnum, end)
                else:
                    self._add_token(tokens.NAME, token, self.lnum, start, line, self.lnum, end)
            elif token == 'async':                 # async token, look ahead
                #ahead token
                if self.pos < self.max:
                    async_end = pseudoDFA.recognize(line, self.pos)
                    assert async_end >= 3
                    async_start = async_end - 3
                    assert async_start >= 0
                    ahead_token = line[async_start:async_end]
                    if ahead_token == 'def':
                        self.async_def = True
                        self.async_def_indent = self.indents[-1]
                        self._add_token(tokens.ASYNC, token, self.lnum, start, line, self.lnum, end)
                    else:
                        self._add_token(tokens.NAME, token, self.lnum, start, line, self.lnum, end)
                else:
                    self._add_token(tokens.NAME, token, self.lnum, start, line, self.lnum, end)
            else:
                self._add_token(tokens.NAME, token, self.lnum, start, line, self.lnum, end)
            self.last_comment = ''
        elif initial == '\\':                      # continued stmt
            self.continued = True
        elif initial == '$':
            self._add_token(tokens.REVDBMETAVAR, token,
                               self.lnum, start, line, self.lnum, self.pos)
            self.last_comment = ''
        else:
            if token in python_opmap:
                punct = python_opmap[token]
            else:
                punct = tokens.OP

            level_adjustment = 0
            if initial in '([{':
                level_adjustment = 1
            elif initial in ')]}':
                level_adjustment = -1

            tok = self._add_token(punct, token, self.lnum, start, line, self.lnum, end, level_adjustment=level_adjustment)
            if level_adjustment == 1:
                self.parenstack.append(tok)
            if level_adjustment == -1:
                if not self.parenstack:
                    self._raise_token_error("unmatched '%s'" % initial, line,
                                     self.lnum, start + 1)
                openparen = self.parenstack.pop()
                opening = openparen.value[0]
                lnum1 = openparen.lineno
                start1 = openparen.column
                line1 = openparen.line

                if not ((opening == "(" and initial == ")") or
                        (opening == "[" and initial == "]") or
                        (opening == "{" and initial == "}")):
                    msg = "closing parenthesis '%s' does not match opening parenthesis '%s'" % (
                                initial, opening)

                    if lnum1 != self.lnum:
                        msg += " on line " + str(lnum1)
                    self._raise_token_error(
                            msg, line, self.lnum, start + 1)
            self.last_comment = ''
        return False


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
    orig_lines = lines

    token_list = []
    lnum = 0
    continued = False
    numchars = NUMCHARS
    contstrs, needcont = [], False
    indents = [0]
    altindents = [0]
    last_comment = ''
    # contains the tokens of the opening parens
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
    strstart = (0, 0, "", False) # linenumber, offset, starting_line, is_triple_quoted
    cont_line_col = 0
    for lines_index, line in enumerate(lines):
        lnum = lnum + 1
        line = universal_newline(line)
        pos, max = 0, len(line)
        switch_indents = 0

        if contstrs:
            if not line:
                raise_unterminated_string(strstart[3], strstart[2], strstart[0],
                                          strstart[1] + 1, token_list,
                                          lnum - 1, len(line))
            endmatch = endDFA.recognize(line)
            if endmatch >= 0:
                pos = end = endmatch
                contstrs.append(line[:end])
                tok = Token(tokens.STRING, "".join(contstrs), strstart[0],
                       strstart[1], line, lnum, end, level=len(parenstack))
                token_list.append(tok)
                last_comment = ''
                contstrs, needcont = [], False
            elif (needcont and not line.endswith('\\\n') and
                               not line.endswith('\\\r\n')):
                contstrs.append(line)
                raise_unterminated_string(strstart[3], strstart[2], strstart[0],
                                          strstart[1] + 1, token_list,
                                          lnum, len(line))
                continue
            else:
                contstrs.append(line)
                continue

        elif not parenstack and not continued:  # new statement
            if not line: break
            column = cont_line_col
            altcolumn = cont_line_col
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

            if line[pos] in '#\r\n':
                # skip blank lines
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
                else:
                    continue
            if line[pos] == '\\' and line[pos + 1] in '\r\n':
                # first non-whitespace char and last char in line is \
                if lines[lines_index + 1] not in ("\r\n", "\n", "\x0C\n"):
                    # continuation marker after spaces increase the
                    # indentation level if column > 0
                    if column == 0:
                        pass
                    elif pos != cont_line_col:
                        indents.append(pos)
                        altindents.append(pos)
                        token_list.append(Token(tokens.INDENT, line[:pos], lnum, 0, line[:pos] + lines[lines_index + 1], lnum, pos, level=len(parenstack)))
                        cont_line_col = pos
                        continued = True
                        continue
                if lines[lines_index + 1] != "":
                    # skip lines that are only a line continuation char
                    # followed by an empty line (not last line)
                    continue
            else:
                cont_line_col = 0
            if column == indents[-1]:
                if altcolumn != altindents[-1]:
                    raise TabError(lnum, pos, line)
            elif column > indents[-1]:           # count indents or dedents
                if altcolumn <= altindents[-1]:
                    raise TabError(lnum, pos, line)
                indents.append(column)
                altindents.append(altcolumn)
                token_list.append(Token(tokens.INDENT, line[:pos], lnum, 0, line, lnum, pos, level=len(parenstack)))
                last_comment = ''
            else:
                while column < indents[-1]:
                    indents.pop()
                    altindents.pop()
                    token_list.append(Token(tokens.DEDENT, '', lnum, pos, line, level=len(parenstack)))
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
                    openparen = parenstack[0]
                    parenkind = openparen.value[0]
                    lnum1 = openparen.lineno
                    start1 = openparen.column
                    line1 = openparen.line
                    raise TokenError("'%s' was never closed" % (parenkind, ), line1,
                                     lnum1, start1 + 1, token_list, lnum)
                prevline = lines[lines_index - 1]
                raise TokenError(EOF_MULTI_LINE_STATEMENT_ERROR , prevline,
                                 lnum - 1, len(prevline) - 1, token_list) # XXX why is the offset 0 here?
            continued = False

        while pos < max:
            pseudomatch = pseudoDFA.recognize(line, pos)
            start = whiteSpaceDFA.recognize(line, pos)
            if pseudomatch >= 0:                            # scan for tokens
                if start < 0:
                    start = pos
                end = pseudomatch

                if start == end:
                    if line[start] == "\\":
                        raise TokenError("unexpected character after line continuation character", line,
                                         lnum, start + 2, token_list)

                    raise_unknown_character(line, start, lnum, token_list, flags)

                pos = end
                token, initial = line[start:end], line[start]
                if (initial in numchars or \
                   (initial == '.' and token != '.' and token != '...')):
                    # ordinary number
                    token_list.append(Token(tokens.NUMBER, token, lnum, start, line, lnum, end, level=len(parenstack)))
                    _maybe_raise_number_error(token, line, lnum, start, end, token_list)
                    last_comment = ''
                elif initial in '\r\n':
                    if not parenstack:
                        if async_def:
                            async_def_nl = True
                        tok = Token(tokens.NEWLINE, last_comment, lnum, start, line, level=len(parenstack))
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
                        tok = Token(tokens.STRING, token, lnum, start, line, lnum, pos, level=len(parenstack))
                        token_list.append(tok)
                        last_comment = ''
                    else:
                        strstart = (lnum, start, line, True)
                        contstrs = [line[start:]]
                        break
                elif initial in single_quoted or \
                    token[:2] in single_quoted or \
                    token[:3] in single_quoted:
                    if token[-1] == '\n':                  # continued string
                        strstart = (lnum, start, line, False)
                        endDFA = (endDFAs[initial] or endDFAs[token[1]] or
                                   endDFAs[token[2]])
                        contstrs, needcont = [line[start:]], True
                        break
                    else:                                  # ordinary string
                        tok = Token(tokens.STRING, token, lnum, start, line, lnum, pos, level=len(parenstack))
                        token_list.append(tok)
                        last_comment = ''
                elif potential_identifier_char(initial): # unicode identifier
                    verify_identifier(token, line, lnum, start, token_list, flags)
                    # inside 'async def' function or no async_hacks
                    # so recognize them unconditionally.
                    if not async_hacks or async_def:
                        if token == 'async':
                            token_list.append(Token(tokens.ASYNC, token, lnum, start, line, lnum, end, level=len(parenstack)))
                        elif token == 'await':
                            token_list.append(Token(tokens.AWAIT, token, lnum, start, line, lnum, end, level=len(parenstack)))
                        else:
                            token_list.append(Token(tokens.NAME, token, lnum, start, line, lnum, end, level=len(parenstack)))
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
                                token_list.append(Token(tokens.ASYNC, token, lnum, start, line, lnum, end, level=len(parenstack)))
                            else:
                                token_list.append(Token(tokens.NAME, token, lnum, start, line, lnum, end, level=len(parenstack)))
                        else:
                            token_list.append(Token(tokens.NAME, token, lnum, start, line, lnum, end, level=len(parenstack)))
                    else:
                        token_list.append(Token(tokens.NAME, token, lnum, start, line, lnum, end, level=len(parenstack)))
                    last_comment = ''
                elif initial == '\\':                      # continued stmt
                    continued = True
                elif initial == '$':
                    token_list.append(Token(tokens.REVDBMETAVAR, token,
                                       lnum, start, line, lnum, pos, level=len(parenstack)))
                    last_comment = ''
                else:
                    if token in python_opmap:
                        punct = python_opmap[token]
                    else:
                        punct = tokens.OP

                    level_adjustment = 0
                    if initial in '([{':
                        level_adjustment = 1
                    elif initial in ')]}':
                        level_adjustment = -1

                    tok = Token(punct, token, lnum, start, line, lnum, end, level=len(parenstack) + level_adjustment)
                    if level_adjustment == 1:
                        parenstack.append(tok)
                    if level_adjustment == -1:
                        if not parenstack:
                            raise TokenError("unmatched '%s'" % initial, line,
                                             lnum, start + 1, token_list)
                        openparen = parenstack.pop()
                        opening = openparen.value[0]
                        lnum1 = openparen.lineno
                        start1 = openparen.column
                        line1 = openparen.line

                        if not ((opening == "(" and initial == ")") or
                                (opening == "[" and initial == "]") or
                                (opening == "{" and initial == "}")):
                            msg = "closing parenthesis '%s' does not match opening parenthesis '%s'" % (
                                        initial, opening)

                            if lnum1 != lnum:
                                msg += " on line " + str(lnum1)
                            raise TokenError(
                                    msg, line, lnum, start + 1, token_list)
                    token_list.append(tok)
                    last_comment = ''
            else:
                if start < 0:
                    start = pos
                if start<max and line[start] in single_quoted:
                    raise_unterminated_string(False, line, lnum, start+1,
                                              token_list, lnum, len(line))
                if line[pos] == "0":
                    raise TokenError("leading zeros in decimal integer literals are not permitted; use an 0o prefix for octal integers",
                            line, lnum, pos+1, token_list)
                tok = Token(tokens.ERRORTOKEN, line[pos], lnum, pos, line, level=len(parenstack))
                token_list.append(tok)
                last_comment = ''
                pos = pos + 1
    lnum -= 1
    if not (flags & consts.PyCF_DONT_IMPLY_DEDENT):
        if token_list and token_list[-1].token_type != tokens.NEWLINE:
            tok = Token(tokens.NEWLINE, '', lnum, 0, '\n', level=len(parenstack))
            token_list.append(tok)
        for indent in indents[1:]:                # pop remaining indent levels
            token_list.append(Token(tokens.DEDENT, '', lnum, pos, line, level=len(parenstack)))
    tok = Token(tokens.NEWLINE, '', lnum, 0, '\n', level=len(parenstack))
    token_list.append(tok)

    token_list.append(Token(tokens.ENDMARKER, '', lnum, pos, line, level=len(parenstack)))

    t = Tokenizer(flags)
    token_list2 = t.tokenize_lines(orig_lines[:])
    #assert len(token_list) == len(token_list2)
    if not objectmodel.we_are_translated():
        for index, tok1, tok2 in zip(range(len(token_list)), token_list, token_list2):
            assert tok1 == tok2
    return token_list2


def _maybe_raise_number_error(token, line, lnum, start, end, token_list):
    ch = _get_next_or_nul(line, end)
    if end == start + 1 and token[0] == "0":
        if ch == "b":
            token = "0b"
            end += 1
            ch = _get_next_or_nul(line, end)
            if not ch.isdigit():
                raise TokenError("invalid binary literal",
                        line, lnum, end, token_list)
        elif ch == "o":
            token = "0o"
            end += 1
            ch = _get_next_or_nul(line, end)
            if not ch.isdigit():
                raise TokenError("invalid octal literal",
                        line, lnum, end, token_list)
        elif ch == "x":
            token = "0x"
            end += 1
            ch = _get_next_or_nul(line, end)
            if not ch.isdigit():
                raise TokenError("invalid hexadecimal literal",
                        line, lnum, end, token_list)
    if token.startswith("0b"):
        kind = "binary"
        nextch = _skip_underscore(ch, line, end)
        if nextch.isdigit():
            raise TokenError("invalid digit '%s' in binary literal" % (nextch, ),
                    line, lnum, end + 1, token_list)
        elif ch == "_":
            raise TokenError("invalid binary literal",
                    line, lnum, end, token_list)

    elif token.startswith("0o"):
        kind = "octal"
        nextch = _skip_underscore(ch, line, end)
        if nextch.isdigit():
            raise TokenError("invalid digit '%s' in octal literal" % (nextch, ),
                    line, lnum, end + 1, token_list)
        elif ch == "_":
            raise TokenError("invalid octal literal",
                    line, lnum, end, token_list)

    elif token.startswith("0x"):
        kind = "hexadecimal"
        if ch == "_":
            raise TokenError("invalid hexadecimal literal",
                    line, lnum, end + 1, token_list)

    else:
        kind = "decimal"
        if ch == "_":
            raise TokenError("invalid decimal literal",
                    line, lnum, end + 1, token_list)

    # now that we've covered the actual error cases, let's see whether we need
    # to insert a WARNING token

    # we only need to do that in the cases of *valid* syntax, ie it's a
    # number followed by one of the keywords that starts with [a-f]
    warn = False
    if ch == 'a':
        warn = _lookahead(line, end + 1, "nd")
    elif ch == 'e':
        warn = _lookahead(line, end + 1, "lse")
    elif ch == 'f':
        warn = _lookahead(line, end + 1, "or")
    elif ch == 'i':
        ch = _get_next_or_nul(line, end + 1)
        warn = ch == 'f' or ch == 'n' or ch == 's'
    elif ch == 'n':
        warn = _lookahead(line, end + 1, "ot")
    elif ch == 'o':
        ch = _get_next_or_nul(line, end + 1)
        warn = ch == 'r'

    if warn:
        # need a warning token
        token_list.append(Token(tokens.WARNING, "invalid %s literal" % kind,
                                lnum, start, line, -1, -1))
    elif potential_identifier_char(ch):
        # raise an error right here
        raise TokenError("invalid %s literal" % kind,
                         line, lnum, start + 1, token_list, lnum, end + 2)


def _get_next_or_nul(line, end):
    if end < len(line):
        return line[end]
    return chr(0)

def _lookahead(line, pos, s):
    if not (pos + len(s) <= len(line)):
        return False
    for char in s:
        if line[pos] != char:
            return False
        pos += 1
    return True

def _skip_underscore(ch, line, end):
    if ch == "_":
        return _get_next_or_nul(line, end + 1)
    return ch

def universal_newline(line):
    # show annotator that indexes below are non-negative
    line_len_m2 = len(line) - 2
    if line_len_m2 >= 0 and line[-2] == '\r' and line[-1] == '\n':
        return line[:line_len_m2] + '\n'
    line_len_m1 = len(line) - 1
    if line_len_m1 >= 0 and line[-1] == '\r':
        return line[:line_len_m1] + '\n'
    return line
