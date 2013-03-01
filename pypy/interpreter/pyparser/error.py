
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
        if self.filename is None:
            w_filename = space.w_None
        else:
            w_filename = space.fsdecode(space.wrapbytes(self.filename))
        return space.newtuple([space.wrap(self.msg),
                               space.newtuple([w_filename,
                                               space.wrap(self.lineno),
                                               space.wrap(self.offset),
                                               space.wrap(self.text),
                                               space.wrap(self.lastlineno)])])

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
