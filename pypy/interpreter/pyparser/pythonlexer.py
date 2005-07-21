"""This is a lexer for a Python recursive descent parser
it obeys the TokenSource interface defined for the grammar
analyser in grammar.py
"""
import sys
from codeop import PyCF_DONT_IMPLY_DEDENT

from pypy.interpreter.pyparser.grammar import TokenSource, Token
from pypy.interpreter.pyparser.error import ParseError
import pytoken
from pytoken import NEWLINE

# Don't import string for that ...
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
    if index == -1:
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
    
def _normalize_encoding(encoding):
    """returns normalized name for <encoding>

    see dist/src/Parser/tokenizer.c 'get_normal_name()'
    for implementation details / reference

    NOTE: for now, parser.suite() raises a MemoryError when
          a bad encoding is used. (SF bug #979739)
    """
    # lower() + '_' / '-' conversion
    encoding = encoding.replace('_', '-').lower()
    if encoding.startswith('utf-8'):
        return 'utf-8'
    for variant in ('latin-1', 'iso-latin-1', 'iso-8859-1'):
        if encoding.startswith(variant):
            return 'iso-8859-1'
    return encoding

################################################################################
from pypy.interpreter.pyparser import pytoken
from pytokenize import tabsize, whiteSpaceDFA, triple_quoted, endDFAs, \
     single_quoted, pseudoDFA 
import automata


class TokenError(ParseError):
    """Raised for lexer errors, e.g. when EOF is found prematurely"""
    def __init__(self, msg, line, strstart, token_stack):
        lineno, offset = strstart
        ParseError.__init__(self, msg, lineno, offset, line)
        self.token_stack = token_stack

def generate_tokens(lines, flags):
    """
    This is a rewrite of pypy.module.parser.pytokenize.generate_tokens since
    the original function is not RPYTHON (uses yield)
    It was also slightly modified to generate Token instances instead
    of the original 5-tuples

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
    lnum = parenlev = continued = 0
    namechars = NAMECHARS
    numchars = NUMCHARS
    contstr, needcont = '', 0
    contline = None
    indents = [0]
    last_comment = ''
    encoding = None
    # make the annotator happy
    pos = -1
    lines.append('') # XXX HACK probably not needed
    # make the annotator happy
    endDFA = automata.DFA([], [])
    # make the annotator happy
    line = ''
    for line in lines:
        lnum = lnum + 1
        pos, max = 0, len(line)

        if contstr:                            # continued string
            if not line:
                raise TokenError("EOF in multi-line string", line,
                                 (lnum, 0), token_list)
            endmatch = endDFA.recognize(line)
            if -1 != endmatch:
                pos = end = endmatch
                tok = Token(pytoken.STRING, contstr + line[:end])
                token_list.append((tok, line, lnum, pos))
                last_comment = ''
                # token_list.append((STRING, contstr + line[:end],
                #                    strstart, (lnum, end), contline + line))
                contstr, needcont = '', 0
                contline = None
            elif needcont and line[-2:] != '\\\n' and line[-3:] != '\\\r\n':
                tok = Token(pytoken.ERRORTOKEN, contstr + line)
                token_list.append((tok, line, lnum, pos))
                last_comment = ''
                # token_list.append((ERRORTOKEN, contstr + line,
                #                    strstart, (lnum, len(line)), contline))
                contstr = ''
                contline = None
                continue
            else:
                contstr = contstr + line
                contline = contline + line
                continue

        elif parenlev == 0 and not continued:  # new statement
            if not line: break
            column = 0
            while pos < max:                   # measure leading whitespace
                if line[pos] == ' ': column = column + 1
                elif line[pos] == '\t': column = (column/tabsize + 1)*tabsize
                elif line[pos] == '\f': column = 0
                else: break
                pos = pos + 1
            if pos == max: break

            if line[pos] in '#\r\n':           # skip comments or blank lines
                if line[pos] == '#':
                    tok = Token(pytoken.COMMENT, line[pos:])
                    last_comment = line[pos:]
                    if lnum <= 2 and encoding is None:
                        encoding = match_encoding_declaration(last_comment)
                        if encoding is not None:
                            encoding = _normalize_encoding(encoding)
                else:
                    tok = Token(pytoken.NL, line[pos:])
                    last_comment = ''
                # XXX Skip NL and COMMENT Tokens
                # token_list.append((tok, line, lnum, pos))
                continue

            if column > indents[-1]:           # count indents or dedents
                indents.append(column)
                tok = Token(pytoken.INDENT, line[:pos])
                token_list.append((tok, line, lnum, pos))
                last_comment = ''
            while column < indents[-1]:
                indents = indents[:-1]
                tok = Token(pytoken.DEDENT, '')
                token_list.append((tok, line, lnum, pos))
                last_comment = ''
        else:                                  # continued statement
            if not line:
                raise TokenError("EOF in multi-line statement", line,
                                 (lnum, 0), token_list)
            continued = 0

        while pos < max:
            pseudomatch = pseudoDFA.recognize(line, pos)
            if -1 != pseudomatch:                            # scan for tokens
                # JDR: Modified
                start = whiteSpaceDFA.recognize(line, pos)
                if -1 == start:
                    start = pos
                end = pseudomatch

                if start == end:
                    # Nothing matched!!!
                    raise TokenError("Unknown character", line,
                                 (lnum, start), token_list)

                spos, epos, pos = (lnum, start), (lnum, end), end
                token, initial = line[start:end], line[start]
                if initial in numchars or \
                   (initial == '.' and token != '.'):      # ordinary number
                    tok = Token(pytoken.NUMBER, token)
                    token_list.append((tok, line, lnum, pos))
                    last_comment = ''
                elif initial in '\r\n':
                    if parenlev > 0:
                        tok = Token(pytoken.NL, token)
                        last_comment = ''
                        # XXX Skip NL
                    else:
                        tok = Token(pytoken.NEWLINE, token)
                        # XXX YUCK !
                        tok.value = last_comment
                        token_list.append((tok, line, lnum, pos))
                        last_comment = ''
                elif initial == '#':
                    tok = Token(pytoken.COMMENT, token)
                    last_comment = token
                    if lnum <= 2 and encoding is None:
                        encoding = match_encoding_declaration(last_comment)
                        if encoding is not None:
                            encoding = _normalize_encoding(encoding)
                    # XXX Skip # token_list.append((tok, line, lnum, pos))
                    # token_list.append((COMMENT, token, spos, epos, line))
                elif token in triple_quoted:
                    endDFA = endDFAs[token]
                    endmatch = endDFA.recognize(line, pos)
                    if -1 != endmatch:                     # all on one line
                        pos = endmatch
                        token = line[start:pos]
                        tok = Token(pytoken.STRING, token)
                        token_list.append((tok, line, lnum, pos))
                        last_comment = ''
                    else:
                        contstr = line[start:]
                        contline = line
                        break
                elif initial in single_quoted or \
                    token[:2] in single_quoted or \
                    token[:3] in single_quoted:
                    if token[-1] == '\n':                  # continued string
                        endDFA = (endDFAs[initial] or endDFAs[token[1]] or
                                   endDFAs[token[2]])
                        contstr, needcont = line[start:], 1
                        contline = line
                        break
                    else:                                  # ordinary string
                        tok = Token(pytoken.STRING, token)
                        token_list.append((tok, line, lnum, pos))
                        last_comment = ''
                        # token_list.append((STRING, token, spos, epos, line))
                elif initial in namechars:                 # ordinary name
                    tok = Token(pytoken.NAME, token)
                    token_list.append((tok, line, lnum, pos))
                    last_comment = ''
                elif initial == '\\':                      # continued stmt
                    continued = 1
                else:
                    if initial in '([{':
                        parenlev = parenlev + 1
                    elif initial in ')]}':
                        parenlev = parenlev - 1
                    if token in pytoken.tok_punct:
                        tok = Token(pytoken.tok_punct[token])
                    else:
                        tok = Token(pytoken.OP, token)
                    token_list.append((tok, line, lnum, pos)) 
                    last_comment = ''
            else:
                tok = Token(pytoken.ERRORTOKEN, line[pos])
                token_list.append((tok, line, lnum, pos))
                last_comment = ''
                pos = pos + 1

    lnum -= 1
    if not (flags & PyCF_DONT_IMPLY_DEDENT):
        if token_list and token_list[-1][0].codename != pytoken.NEWLINE:
            token_list.append((Token(pytoken.NEWLINE, ''), '\n', lnum, 0))
        for indent in indents[1:]:                 # pop remaining indent levels
            tok = Token(pytoken.DEDENT, '')
            token_list.append((tok, line, lnum, pos))
    if token_list and token_list[-1][0].codename != pytoken.NEWLINE:
        token_list.append((Token(pytoken.NEWLINE, ''), '\n', lnum, 0))

    tok = Token(pytoken.ENDMARKER, '',)
    token_list.append((tok, line, lnum, pos))
    return token_list, encoding

class PythonSource(TokenSource):
    """This source uses Jonathan's tokenizer"""
    def __init__(self, strings, flags=0):
        # TokenSource.__init__(self)
        tokens, encoding = generate_tokens(strings, flags)
        self.token_stack = tokens
        self.encoding = encoding
        self._current_line = '' # the current line (as a string)
        self._lineno = -1
        self._offset = 0
        self.stack_pos = 0

    def next(self):
        """Returns the next parsed token"""
        if self.stack_pos >= len(self.token_stack):
            raise StopIteration
        tok, line, lnum, pos = self.token_stack[self.stack_pos]
        self.stack_pos += 1
        self._current_line = line
        self._lineno = max(self._lineno, lnum)
        self._offset = pos
        return tok

    def current_line(self):
        """Returns the current line being parsed"""
        return self._current_line

    def current_lineno(self):
        """Returns the current lineno"""
        return self._lineno

    def context(self):
        """Returns an opaque context object for later restore"""
        return self.stack_pos

    def restore(self, ctx):
        """Restores a context"""
        self.stack_pos = ctx

    def peek(self):
        """returns next token without consuming it"""
        ctx = self.context()
        token = self.next()
        self.restore(ctx)
        return token

    #### methods below have to be translated 
    def offset(self, ctx=None):
        if ctx is None:
            return self.stack_pos
        else:
            assert type(ctx) == int
            return ctx

    def get_pos(self):
        if self.stack_pos >= len(self.stack):
            return self.pos
        else:
            token, line, lnum, pos = self.stack[self.stack_pos]
            return lnum, pos

    def get_source_text(self, pos0, pos1):
        return self.input[pos0:pos1]
        
    def debug(self):
        """return context for debug information"""
        return (self._current_line, self._lineno)
        # return 'line %s : %s' % ('XXX', self._current_line)

NONE_LIST = [pytoken.ENDMARKER, pytoken.INDENT, pytoken.DEDENT]
NAMED_LIST = [pytoken.OP]

Source = PythonSource

def tokenize_file(filename):
    f = file(filename).read()
    src = Source(f)
    token = src.next()
    while token != ("ENDMARKER", None) and token != (None, None):
        print token
        token = src.next()

if __name__ == '__main__':
    import sys
    tokenize_file(sys.argv[1])
