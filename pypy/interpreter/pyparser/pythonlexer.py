"""This is a lexer for a Python recursive descent parser
it obeys the TokenSource interface defined for the grammar
analyser in grammar.py
"""
import sys
from codeop import PyCF_DONT_IMPLY_DEDENT

from pypy.interpreter.pyparser.grammar import TokenSource, Token, AbstractContext, Parser
from pypy.interpreter.pyparser.error import SyntaxError

import pytoken

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

################################################################################
from pypy.interpreter.pyparser import pytoken
from pytokenize import tabsize, whiteSpaceDFA, triple_quoted, endDFAs, \
     single_quoted, pseudoDFA
import automata


class TokenError(SyntaxError):
    """Raised for lexer errors, e.g. when EOF is found prematurely"""
    def __init__(self, msg, line, strstart, token_stack):
        lineno, offset = strstart
        SyntaxError.__init__(self, msg, lineno, offset, line)
        self.token_stack = token_stack

def generate_tokens( parser, lines, flags, keywords):
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
    #for line in lines:
    #    print repr(line)
    #print '------------------- flags=%s ---->' % flags
    assert isinstance( parser, Parser )
    token_list = []
    lnum = parenlev = continued = 0
    namechars = NAMECHARS
    numchars = NUMCHARS
    contstr, needcont = '', 0
    contline = None
    indents = [0]
    last_comment = ''
    # make the annotator happy
    pos = -1
    lines.append('') # XXX HACK probably not needed

    # look for the bom (byte-order marker) for utf-8

    # make the annotator happy
    endDFA = automata.DFA([], [])
    # make the annotator happy
    line = ''
    for line in lines:
        lnum = lnum + 1
        pos, max = 0, len(line)

        if contstr:                            # continued string
            if not line:
                raise TokenError("EOF while scanning triple-quoted string", line,
                                 (lnum-1, 0), token_list)
            endmatch = endDFA.recognize(line)
            if endmatch >= 0:
                pos = end = endmatch
                tok = Token(parser, parser.tokens['STRING'], contstr + line[:end])
                token_list.append((tok, line, lnum, pos))
                last_comment = ''
                # token_list.append((STRING, contstr + line[:end],
                #                    strstart, (lnum, end), contline + line))
                contstr, needcont = '', 0
                contline = None
            elif (needcont and not line.endswith('\\\n') and
                               not line.endswith('\\\r\n')):
                tok = Token(parser, parser.tokens['ERRORTOKEN'], contstr + line)
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

            if line[pos] in '#\r\n':
                # skip comments or blank lines
                continue

            if column > indents[-1]:           # count indents or dedents
                indents.append(column)
                tok = Token(parser, parser.tokens['INDENT'], line[:pos])
                token_list.append((tok, line, lnum, pos))
                last_comment = ''
            while column < indents[-1]:
                indents = indents[:-1]
                tok = Token(parser, parser.tokens['DEDENT'], '')
                token_list.append((tok, line, lnum, pos))
                last_comment = ''
        else:                                  # continued statement
            if not line:
                raise TokenError("EOF in multi-line statement", line,
                                 (lnum, 0), token_list)
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
                    # Nothing matched!!!
                    raise TokenError("Unknown character", line,
                                 (lnum, start), token_list)

                pos = end
                token, initial = line[start:end], line[start]
                if initial in numchars or \
                   (initial == '.' and token != '.'):      # ordinary number
                    tok = Token(parser, parser.tokens['NUMBER'], token)
                    token_list.append((tok, line, lnum, pos))
                    last_comment = ''
                elif initial in '\r\n':
                    if parenlev <= 0:
                        tok = Token(parser, parser.tokens['NEWLINE'], token)
                        # XXX YUCK !
                        tok.value = last_comment
                        token_list.append((tok, line, lnum, pos))
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
                        tok = Token(parser, parser.tokens['STRING'], token)
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
                        tok = Token(parser, parser.tokens['STRING'], token)
                        token_list.append((tok, line, lnum, pos))
                        last_comment = ''
                elif initial in namechars:                 # ordinary name
                    tok = Token(parser, parser.tokens['NAME'], token)
                    if token not in keywords:
                        tok.isKeyword = False
                    token_list.append((tok, line, lnum, pos))
                    last_comment = ''
                elif initial == '\\':                      # continued stmt
                    continued = 1
                    # lnum -= 1  disabled: count continuation lines separately
                else:
                    if initial in '([{':
                        parenlev = parenlev + 1
                    elif initial in ')]}':
                        parenlev = parenlev - 1
                        if parenlev < 0:
                            raise TokenError("unmatched '%s'" % initial, line,
                                             (lnum-1, 0), token_list)
                    if token in parser.tok_values:
                        punct = parser.tok_values[token]
                        tok = Token(parser, punct, None)
                    else:
                        tok = Token(parser, parser.tokens['OP'], token)
                    token_list.append((tok, line, lnum, pos)) 
                    last_comment = ''
            else:
                start = whiteSpaceDFA.recognize(line, pos)
                if start < 0:
                    start = pos
                if start<max and line[start] in single_quoted:
                    raise TokenError("EOL while scanning single-quoted string", line,
                             (lnum, start), token_list)
                tok = Token(parser, parser.tokens['ERRORTOKEN'], line[pos])
                token_list.append((tok, line, lnum, pos))
                last_comment = ''
                pos = pos + 1

    lnum -= 1
    if not (flags & PyCF_DONT_IMPLY_DEDENT):
        if token_list and token_list[-1][0].codename != parser.tokens['NEWLINE']:
            token_list.append((Token(parser, parser.tokens['NEWLINE'], ''), '\n', lnum, 0))
        for indent in indents[1:]:                # pop remaining indent levels
            tok = Token(parser, parser.tokens['DEDENT'], '')
            token_list.append((tok, line, lnum, pos))
    #if token_list and token_list[-1][0].codename != pytoken.NEWLINE:
    token_list.append((Token(parser, parser.tokens['NEWLINE'], ''), '\n', lnum, 0))

    tok = Token(parser, parser.tokens['ENDMARKER'], '',)
    token_list.append((tok, line, lnum, pos))
    #for t in token_list:
    #    print '%20s  %-25s %d' % (pytoken.tok_name.get(t[0].codename, '?'), t[0], t[-2])
    #print '----------------------------------------- pyparser/pythonlexer.py'
    return token_list


class PythonSourceContext(AbstractContext):
    def __init__(self, pos ):
        self.pos = pos

class PythonSource(TokenSource):
    """This source uses Jonathan's tokenizer"""
    def __init__(self, parser, strings, keywords, flags=0):
        # TokenSource.__init__(self)
        #self.parser = parser
        
        self.input = strings
        tokens = generate_tokens( parser, strings, flags, keywords)
        self.token_stack = tokens
        self._current_line = '' # the current line (as a string)
        self._lineno = -1
        self._token_lnum = 0
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
        self._token_lnum = lnum
        self._offset = pos
        return tok

    def current_linesource(self):
        """Returns the current line being parsed"""
        return self._current_line

    def current_lineno(self):
        """Returns the current lineno"""
        return self._lineno

    def context(self):
        """Returns an opaque context object for later restore"""
        return PythonSourceContext(self.stack_pos)

    def restore(self, ctx):
        """Restores a context"""
        assert isinstance(ctx, PythonSourceContext)
        self.stack_pos = ctx.pos

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
        return self.stack_pos

    def get_source_text(self, p0, p1):
        "We get passed two token stack positions."
        return "XXX this got left behind in a refactoring. Stack positions are %d and %d" % (p0, p1)
        
    def debug(self):
        """return context for debug information"""
        return (self._current_line, self._lineno)

Source = PythonSource

