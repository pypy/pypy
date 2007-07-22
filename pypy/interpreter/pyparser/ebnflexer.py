"""This is a lexer for a Python recursive descent parser
it obeys the TokenSource interface defined for the grammar
analyser in grammar.py
"""

from grammar import TokenSource, Token, AbstractContext
from ebnfgrammar import GRAMMAR_GRAMMAR as G


def match_symbol( input, start, stop ):
    idx = start
    while idx<stop:
        if input[idx] not in "_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
            break
        idx+=1
    return idx


class GrammarSourceContext(AbstractContext):
    def __init__(self, pos, peek):
        self.pos = pos
        self.peek = peek

class GrammarSource(TokenSource):
    """Fully RPython - see targetebnflexer.py
    The grammar tokenizer
    It knows only 5 types of tokens:
    EOF: end of file
    SYMDEF: a symbol definition e.g. "file_input:"
    STRING: a simple string "'xxx'"
    SYMBOL: a rule symbol usually appearing right of a SYMDEF
    tokens: '[', ']', '(' ,')', '*', '+', '|'
    """
    def __init__(self, parser, inpstring):
        # TokenSource.__init__(self)
        self.parser = parser
        self.input = inpstring
        self.pos = 0
        self.begin = 0
        self._peeked = None
        self.current_line = 1

    def context(self):
        """returns an opaque context object, used to backtrack
        to a well known position in the parser"""
        return GrammarSourceContext( self.pos, self._peeked )

    def offset(self, ctx=None):
        """Returns the current parsing position from the start
        of the parsed text"""
        if ctx is None:
            return self.pos
        else:
            assert isinstance(ctx, GrammarSourceContext)
            return ctx.pos

    def restore(self, ctx):
        """restore the context provided by context()"""
        assert isinstance( ctx, GrammarSourceContext )
        self.pos = ctx.pos
        self._peeked = ctx.peek

    def current_linesource(self):
        pos = idx = self.begin
        inp = self.input
        end = len(inp)
        while idx<end:
            chr = inp[idx]
            if chr=="\n":
                break
            idx+=1
        return self.input[pos:idx]

    def current_lineno(self):
        return self.current_line

    def skip_empty_lines(self, input, start, end ):
        idx = start
        # assume beginning of a line
        while idx<end:
            chr = input[idx]
            if chr not in " \t#\n":
                break
            idx += 1
            if chr=="#":
                # skip to end of line
                while idx<end:
                    chr = input[idx]
                    idx+= 1
                    if chr=="\n":
                        self.begin = idx
                        self.current_line+=1
                        break
                continue
            elif chr=="\n":
                self.begin = idx
                self.current_line+=1
        return idx

    def match_string( self, input, start, stop ):
        if input[start]!="'":
            return start
        idx = start + 1
        while idx<stop:
            chr = input[idx]
            idx = idx + 1
            if chr == "'":
                break
            if chr == "\n":
                self.current_line += 1
                self.begin = idx
                break
        return idx


    def RaiseError( self, msg ):
        errmsg = msg + " at line=%d" % self.current_line
        errmsg += " at pos=%d" % (self.pos-self.begin)
        errmsg += " context='" + self.input[self.pos:self.pos+20]
        raise ValueError( errmsg )

    def next(self):
        """returns the next token"""
        # We only support 1-lookahead which
        # means backtracking more than one token
        # will re-tokenize the stream (but this is the
        # grammar lexer so we don't care really!)
        _p = self.parser
        if self._peeked is not None:
            peeked = self._peeked
            self._peeked = None
            return peeked

        pos = self.pos
        inp = self.input
        end = len(self.input)
        pos = self.skip_empty_lines(inp,pos,end)
        if pos==end:
            return Token(_p, _p.EOF, None)

        # at this point nextchar is not a white space nor \n
        nextchr = inp[pos]
        if nextchr=="'":
            npos = self.match_string( inp, pos, end)
            # could get a string terminated by EOF here
            if npos==end and inp[end-1]!="'":
                self.RaiseError("Unterminated string")
            self.pos = npos
            _endpos = npos - 1
            assert _endpos>=0
            return Token(_p, _p.TOK_STRING, inp[pos+1:_endpos])
        else:
            npos = match_symbol( inp, pos, end)
            if npos!=pos:
                self.pos = npos
                if npos!=end and inp[npos]==":":
                    self.pos += 1
                    return Token(_p, _p.TOK_SYMDEF, inp[pos:npos])
                else:
                    return Token(_p, _p.TOK_SYMBOL, inp[pos:npos])

        # we still have pos!=end here
        chr = inp[pos]
        if chr in "[]()*+|":
            self.pos = pos+1
            return Token(_p, _p.tok_values[chr], chr)
        self.RaiseError( "Unknown token" )

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


# a simple target used to annotate/translate the tokenizer
def target_parse_input( txt ):
    lst = []
    src = GrammarSource( txt )
    while 1:
        x = src.next()
        lst.append( x )
        if x.codename == EOF:
            break
    #return lst

if __name__ == "__main__":
    import sys
    f = file(sys.argv[-1])
    lst = target_parse_input( f.read() )
    for i in lst: print i
