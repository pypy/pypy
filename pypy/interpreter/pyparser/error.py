
class SyntaxError(Exception):
    """Base class for exceptions raised by the parser."""

    def __init__(self, msg, lineno=0, offset=0, text=None, filename=None,
                 lastlineno=0):
        self.msg = msg
        self.lineno = lineno
        self.offset = offset
        self.text = text
        self.filename = filename
        self.lastlineno = lastlineno

    def wrap_info(self, space):
        w_text = w_filename = space.w_None
        offset = self.offset
        if self.text is not None:
            from rpython.rlib.runicode import str_decode_utf_8
            # self.text may not be UTF-8 in case of decoding errors.
            # adjust the encoded text offset to a decoded offset
            # XXX do the right thing about continuation lines, which
            # XXX are their own fun, sometimes giving offset >
            # XXX len(self.text) for example (right now, avoid crashing)
            if offset > len(self.text):
                offset = len(self.text)
            text, _ = str_decode_utf_8(self.text, offset, 'replace')
            offset = len(text)
            if len(self.text) != offset:
                text, _ = str_decode_utf_8(self.text, len(self.text),
                                           'replace')
            w_text = space.newunicode(text)
        if self.filename is not None:
            w_filename = space.newfilename(self.filename)
        return space.newtuple([space.newtext(self.msg),
                               space.newtuple([w_filename,
                                               space.newint(self.lineno),
                                               space.newint(offset),
                                               w_text,
                                               space.newint(self.lastlineno)])])

    def __str__(self):
        return "%s at pos (%d, %d) in %r" % (self.__class__.__name__,
                                             self.lineno,
                                             self.offset,
                                             self.text)

class IndentationError(SyntaxError):
    pass

class TabError(IndentationError):
    def __init__(self, lineno=0, offset=0, text=None, filename=None,
                 lastlineno=0):
        msg = "inconsistent use of tabs and spaces in indentation"
        IndentationError.__init__(self, msg, lineno, offset, text, filename, lastlineno)

class ASTError(Exception):
    def __init__(self, msg, ast_node ):
        self.msg = msg
        self.ast_node = ast_node


class TokenError(SyntaxError):

    def __init__(self, msg, line, lineno, column, tokens, lastlineno=0):
        SyntaxError.__init__(self, msg, lineno, column, line,
                             lastlineno=lastlineno)
        self.tokens = tokens

class TokenIndentationError(IndentationError):

    def __init__(self, msg, line, lineno, column, tokens):
        SyntaxError.__init__(self, msg, lineno, column, line)
        self.tokens = tokens
