"""This is a lexer for a Python recursive descent parser
it obeys the TokenSource interface defined for the grammar
analyser in grammar.py
"""

import re
from grammar import TokenSource

DEBUG = False

## Lexer for Python's grammar ########################################
g_symdef = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*:",re.M)
g_symbol = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*",re.M)
g_string = re.compile(r"'[^']+'",re.M)
g_tok = re.compile(r"\[|\]|\(|\)|\*|\+|\|",re.M)
g_skip = re.compile(r"\s*(#.*$)?",re.M)

class GrammarSource(TokenSource):
    """The grammar tokenizer"""
    def __init__(self, inpstring ):
        TokenSource.__init__(self)
        self.input = inpstring
        self.pos = 0

    def context(self):
        return self.pos

    def restore(self, ctx ):
        self.pos = ctx

    def next(self):
        pos = self.pos
        inp = self.input
        m = g_skip.match(inp, pos)
        while m and pos!=m.end():
            pos = m.end()
            if pos==len(inp):
                self.pos = pos
                return None, None
            m = g_skip.match(inp, pos)
        m = g_symdef.match(inp,pos)
        if m:
            tk = m.group(0)
            self.pos = m.end()
            return 'SYMDEF',tk[:-1]
        m = g_tok.match(inp,pos)
        if m:
            tk = m.group(0)
            self.pos = m.end()
            return tk,tk
        m = g_string.match(inp,pos)
        if m:
            tk = m.group(0)
            self.pos = m.end()
            return 'STRING',tk[1:-1]
        m = g_symbol.match(inp,pos)
        if m:
            tk = m.group(0)
            self.pos = m.end()
            return 'SYMBOL',tk
        raise ValueError("Unknown token at pos=%d context='%s'" % (pos,inp[pos:pos+20]) )

    def debug(self):
        return self.input[self.pos:self.pos+20]
