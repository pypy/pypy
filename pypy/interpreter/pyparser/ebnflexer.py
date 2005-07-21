"""This is a lexer for a Python recursive descent parser
it obeys the TokenSource interface defined for the grammar
analyser in grammar.py
"""

import re
from grammar import TokenSource, Token

## Lexer for Python's grammar ########################################
g_symdef = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*:",re.M)
g_symbol = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*",re.M)
g_string = re.compile(r"'[^']+'",re.M)
g_tok = re.compile(r"\[|\]|\(|\)|\*|\+|\|",re.M)
g_skip = re.compile(r"\s*(#.*$)?",re.M)

class GrammarSource(TokenSource):
    """The grammar tokenizer
    It knows only 5 types of tokens:
    EOF: end of file
    SYMDEF: a symbol definition e.g. "file_input:"
    STRING: a simple string "'xxx'"
    SYMBOL: a rule symbol usually appeary right of a SYMDEF
    tokens: '[', ']', '(' ,')', '*', '+', '|'
    """
    def __init__(self, inpstring, tokenmap ):
        TokenSource.__init__(self)
        self.input = inpstring
        self.pos = 0
        self._peeked = None
        self.tokmap = tokenmap

    def context(self):
        """returns an opaque context object, used to backtrack
        to a well known position in the parser"""
        return self.pos, self._peeked

    def offset(self, ctx=None):
        """Returns the current parsing position from the start
        of the parsed text"""
        if ctx is None:
            return self.pos
        else:
            assert type(ctx)==int
            return ctx

    def restore(self, ctx):
        """restore the context provided by context()"""
        self.pos, self._peeked = ctx

    def next(self):
        """returns the next token"""
        # We only support 1-lookahead which
        # means backtracking more than one token
        # will re-tokenize the stream (but this is the
        # grammar lexer so we don't care really!)
        T = self.tokmap
        if self._peeked is not None:
            peeked = self._peeked
            self._peeked = None
            return peeked
        
        pos = self.pos
        inp = self.input
        m = g_skip.match(inp, pos)
        while m and pos!=m.end():
            pos = m.end()
            if pos==len(inp):
                self.pos = pos
                return Token(T["EOF"], None)
            m = g_skip.match(inp, pos)
        m = g_symdef.match(inp,pos)
        if m:
            tk = m.group(0)
            self.pos = m.end()
            return Token(T['SYMDEF'],tk[:-1])
        m = g_tok.match(inp,pos)
        if m:
            tk = m.group(0)
            self.pos = m.end()
            return Token(T[tk],tk)
        m = g_string.match(inp,pos)
        if m:
            tk = m.group(0)
            self.pos = m.end()
            return Token(T['STRING'],tk[1:-1])
        m = g_symbol.match(inp,pos)
        if m:
            tk = m.group(0)
            self.pos = m.end()
            return Token(T['SYMBOL'],tk)
        raise ValueError("Unknown token at pos=%d context='%s'" %
                         (pos,inp[pos:pos+20]) )

    def peek(self):
        """take a peek at the next token"""
        if self._peeked is not None:
            return self._peeked
        self._peeked = self.next()
        return self._peeked

    def debug(self, N=20):
        """A simple helper function returning the stream at the last
        parsed position"""
        return self.input[self.pos:self.pos+N]
