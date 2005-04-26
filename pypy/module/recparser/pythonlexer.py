"""This is a lexer for a Python recursive descent parser
it obeys the TokenSource interface defined for the grammar
analyser in grammar.py
"""

from grammar import TokenSource

DEBUG = False
import re

KEYWORDS = [
    'and', 'assert', 'break', 'class', 'continue', 'def', 'del',
    'elif', 'if', 'import', 'in', 'is', 'finally', 'for', 'from',
    'global', 'else', 'except', 'exec', 'lambda', 'not', 'or',
    'pass', 'print', 'raise', 'return', 'try', 'while', 'yield'
    ]

py_keywords = re.compile(r'(%s)$' % ('|'.join(KEYWORDS)), re.M | re.X)

py_punct = re.compile(r"""
<>|!=|==|~|
<=|<<=|<<|<|
>=|>>=|>>|>|
\*=|\*\*=|\*\*|\*|
//=|/=|//|/|
%=|\^=|\|=|\+=|=|&=|-=|
,|\^|&|\+|-|\.|%|\||
\)|\(|;|:|@|\[|\]|`|\{|\}
""", re.M | re.X)

g_symdef = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*:", re.M)
g_string = re.compile(r"'[^']+'", re.M)
py_name = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*", re.M)
py_comment = re.compile(r"#.*$|[ \t\014]*$", re.M)
py_ws = re.compile(r" *", re.M)
py_skip = re.compile(r"[ \t\014]*(#.*$)?", re.M)
py_encoding = re.compile(r"coding[:=]\s*([-\w.]+)")
# py_number = re.compile(r"0x[0-9a-z]+|[0-9]+l|([0-9]+\.[0-9]*|\.[0-9]+|[0-9]+)(e[+-]?[0-9]+)?j?||[0-9]+", re.I)

# 0x[\da-f]+l matches hexadecimal numbers, possibly defined as long
# \d+l matches and only matches long integers
# (\d+\.\d*|\.\d+|\d+)(e[+-]?\d+)?j? matches simple integers,
#   exponential notations and complex
py_number = re.compile(r"""0x[\da-f]+l?|
\d+l|
(\d+\.\d*|\.\d+|\d+)(e[+-]?\d+)?j?
""", re.I | re.X)

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

class PythonSource(TokenSource):
    """The Python tokenizer"""
    def __init__(self, inpstring):
        TokenSource.__init__(self)
        self.input = inpstring
        self.pos = 0
        self.indent = 0
        self.indentstack = [ 0 ]
        self.atbol = True
        self.line = 1
        self._current_line = 1
        self.pendin = 0 # indentation change waiting to be reported
        self.level = 0
        self.linestart = 0
        self.stack = []
        self.stack_pos = 0
        self.comment = ''
        self.encoding = None
        
    def current_line(self):
        return self._current_line

    def context(self):
        return self.stack_pos

    def restore(self, ctx):
        self.stack_pos = ctx

    def offset(self, ctx=None):
        if ctx is None:
            return self.stack_pos
        else:
            assert type(ctx)==int
            return ctx

    def _next(self):
        """returns the next token from source"""
        inp = self.input
        pos = self.pos
        input_length = len(inp)
        if pos >= input_length:
            return self.end_of_file()
        # Beginning of line
        if self.atbol:
            self.linestart = pos
            col = 0
            m = py_ws.match(inp, pos)
            pos = m.end()
            col = pos - self.linestart
            self.atbol = False
            # skip blanklines
            m = py_comment.match(inp, pos)
            if m:
                if not self.comment:
                    self.comment = m.group(0)
                # <HACK> XXX FIXME: encoding management
                if self.line <= 2:
                    # self.comment can be the previous comment, so don't use it
                    comment = m.group(0)[1:]
                    m_enc = py_encoding.search(comment)
                    if m_enc is not None:
                        self.encoding = _normalize_encoding(m_enc.group(1))
                # </HACK>
                self.pos = m.end() + 1
                self.line += 1
                self.atbol = True
                return self._next()
            # the current block is more indented than the previous one
            if col > self.indentstack[-1]:
                self.indentstack.append(col)
                return "INDENT", None
            # the current block is less indented than the previous one
            while col < self.indentstack[-1]:
                self.pendin += 1
                self.indentstack.pop(-1)
            if col != self.indentstack[-1]:
                raise SyntaxError("Indentation Error")
        if self.pendin > 0:
            self.pendin -= 1
            return "DEDENT", None
        m = py_skip.match(inp, pos)
        if m.group(0)[-1:] == '\n':
            self.line += 1
        self.comment = m.group(1) or ''
        pos = m.end() # always match
        if pos >= input_length:
            return self.end_of_file()
        self.pos = pos

        # STRING
        c = inp[pos]
        if c in ('r','R'):
            if pos < input_length-1 and inp[pos+1] in ("'",'"'):
                return self.next_string(raw=1)
        elif c in ('u','U'):
            if pos < input_length-1:
                if inp[pos+1] in ("r",'R'):
                    if pos<input_length-2 and inp[pos+2] in ("'",'"'):
                        return self.next_string( raw = 1, uni = 1 )
                elif inp[pos+1] in ( "'", '"' ):
                    return self.next_string( uni = 1 )
        elif c in ( '"', "'" ):
            return self.next_string()

        # NAME
        m = py_name.match(inp, pos)
        if m:
            self.pos = m.end()
            val = m.group(0)
#            if py_keywords.match(val):
#                return val, None
            return "NAME", val

        # NUMBER
        m = py_number.match(inp, pos)
        if m:
            self.pos = m.end()
            return "NUMBER", m.group(0)

        # NEWLINE
        if c == '\n':
            self.pos += 1
            self.line += 1
            if self.level > 0:
                return self._next()
            else:
                self.atbol = True
                comment = self.comment
                self.comment = ''
                return "NEWLINE", comment

        if c == '\\':
            if pos < input_length-1 and inp[pos+1] == '\n':
                self.pos += 2
                return self._next()
        
        m = py_punct.match(inp, pos)
        if m:
            punct = m.group(0)
            if punct in ( '(', '{', '[' ):
                self.level += 1
            if punct in ( ')', '}', ']' ):
                self.level -= 1
            self.pos = m.end()
            return punct, None
        raise SyntaxError("Unrecognized token '%s'" % inp[pos:pos+20] )

    def next(self):
        if self.stack_pos >= len(self.stack):
            tok, val = self._next()
            self.stack.append( (tok, val, self.line) )
            self._current_line = self.line
        else:
            tok,val,line = self.stack[self.stack_pos]
            self._current_line = line
        self.stack_pos += 1
        if DEBUG:
            print "%d/%d: %s, %s" % (self.stack_pos, len(self.stack), tok, val)
        return (tok, val)
            
    def end_of_file(self):
        """return DEDENT and ENDMARKER"""
        if len(self.indentstack) == 1:
            self.indentstack.pop(-1)
            return "NEWLINE", '' #self.comment
        elif len(self.indentstack) > 1:
            self.indentstack.pop(-1)
            return "DEDENT", None
        return "ENDMARKER", None


    def next_string(self, raw=0, uni=0):
        pos = self.pos + raw + uni
        inp = self.input
        quote = inp[pos]
        qsize = 1
        if inp[pos:pos+3] == 3*quote:
            pos += 3
            quote = 3*quote
            qsize = 3
        else:
            pos += 1
        while True:
            if inp[pos:pos+qsize] == quote:
                s = inp[self.pos:pos+qsize]
                self.pos = pos+qsize
                return "STRING", s
            # FIXME : shouldn't it be inp[pos] == os.linesep ?
            if inp[pos:pos+2] == "\n" and qsize == 1:
                return None, None
            if inp[pos] == "\\":
                pos += 1
            pos += 1

    def debug(self):
        """return context for debug information"""
        if not hasattr(self, '_lines'):
            # split lines only once
            self._lines = self.input.splitlines()
        return 'line %s : %s' % (self.line, self._lines[self.line-1])

    ## ONLY refactor ideas ###########################################
##     def _mynext(self):
##         """returns the next token from source"""
##         inp = self.input
##         pos = self.pos
##         input_length = len(inp)
##         if pos >= input_length:
##             return self.end_of_file()
##         # Beginning of line
##         if self.atbol:
##             self.linestart = pos
##             col = 0
##             m = py_ws.match(inp, pos)
##             pos = m.end()
##             col = pos - self.linestart
##             self.atbol = False
##             # skip blanklines
##             m = py_comment.match(inp, pos)
##             if m:
##                 self.pos = m.end() + 1
##                 self.line += 1
##                 self.atbol = True
##                 return self._next()
##             # the current block is more indented than the previous one
##             if col > self.indentstack[-1]:
##                 self.indentstack.append(col)
##                 return "INDENT", None
##             # the current block is less indented than the previous one
##             while col < self.indentstack[-1]:
##                 self.pendin += 1
##                 self.indentstack.pop(-1)
##             if col != self.indentstack[-1]:
##                 raise SyntaxError("Indentation Error")
##         if self.pendin > 0:
##             self.pendin -= 1
##             return "DEDENT", None
##         m = py_skip.match(inp, pos)
##         if m.group(0)[-1:] == '\n':
##             self.line += 1
##         pos = m.end() # always match
##         if pos >= input_length:
##             return self.end_of_file()
##         self.pos = pos

##         c = inp[pos]
##         chain = (self._check_string, self._check_name, self._check_number,
##                  self._check_newline, self._check_backslash, self._check_punct)
##         for check_meth in chain:
##             token_val_pair = check_meth(c, pos)
##             if token_val_pair is not None:
##                 return token_val_pair
        

##     def _check_string(self, c, pos):
##         inp = self.input
##         input_length = len(inp)
##         # STRING
##         if c in ('r', 'R'):
##             if pos < input_length-1 and inp[pos+1] in ("'",'"'):
##                 return self.next_string(raw=1)
##         elif c in ('u','U'):
##             if pos < input_length - 1:
##                 if inp[pos+1] in ("r", 'R'):
##                     if pos<input_length-2 and inp[pos+2] in ("'",'"'):
##                         return self.next_string(raw = 1, uni = 1)
##                 elif inp[pos+1] in ( "'", '"' ):
##                     return self.next_string(uni = 1)
##         elif c in ( '"', "'" ):
##             return self.next_string()
##         return None

##     def _check_name(self, c, pos):
##         inp = self.input
##         # NAME
##         m = py_name.match(inp, pos)
##         if m:
##             self.pos = m.end()
##             val = m.group(0)
##             if py_keywords.match(val):
##                 return val, None
##             return "NAME", val
##         return None

##     def _check_number(self, c, pos):
##         inp = self.input
##         # NUMBER
##         m = py_number.match(inp, pos)
##         if m:
##             self.pos = m.end()
##             return "NUMBER", m.group(0)
##         return None

##     def _check_newline(self, c, pos):
##         # NEWLINE
##         if c == '\n':
##             self.pos += 1
##             self.line += 1
##             if self.level > 0:
##                 return self._next()
##             else:
##                 self.atbol = True
##                 return "NEWLINE", None
##         return None
            
##     def _check_backslash(self, c, pos):
##         inp = self.input
##         input_length = len(inp)
##         if c == '\\':
##             if pos < input_length-1 and inp[pos+1] == '\n':
##                 self.pos += 2
##                 return self._next()
##         return None

##     def _check_punct(self, c, pos):
##         inp = self.input
##         input_length = len(inp)
##         m = py_punct.match(inp, pos)
##         if m:
##             punct = m.group(0)
##             if punct in ( '(', '{' ):
##                 self.level += 1
##             if punct in ( ')', '}' ):
##                 self.level -= 1
##             self.pos = m.end()
##             return punct, None
##         raise SyntaxError("Unrecognized token '%s'" % inp[pos:pos+20] )



def tokenize_file(filename):
    f = file(filename).read()
    src = PythonSource(f)
    token = src.next()
    while token!=("ENDMARKER",None) and token!=(None,None):
        print token
        token = src.next()

if __name__ == '__main__':
    import sys
    tokenize_file(sys.argv[1])
