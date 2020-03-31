
class SyntaxError(Exception):
    """Base class for exceptions raised by the parser."""

    def __init__(self, msg, lineno=0, offset=0, text=None, filename=None,
                 lastlineno=0):
        self.msg = msg
        self.lineno = lineno
        # NB: offset is a 1-based index!
        self.offset = offset
        self.text = text
        self.filename = filename
        self.lastlineno = lastlineno

    def find_sourceline_and_wrap_info(self, space, source=None):
        """ search for the line of input that caused the error and then return
        a wrapped tuple that can be used to construct a wrapped SyntaxError.
        Optionally pass source, to get better error messages for the case where
        this instance was constructed without a source line (.text
        attribute)"""
        text = self.text
        if text is None and source is not None and self.lineno:
            lines = source.splitlines(True)
            text = lines[self.lineno - 1]
        w_filename = space.newtext_or_none(self.filename)
        w_text = space.newtext_or_none(text)
        return space.newtuple([space.newtext(self.msg),
                               space.newtuple([w_filename,
                                               space.newint(self.lineno),
                                               space.newint(self.offset),
                                               w_text,
                                               space.newint(self.lastlineno)])])

    def __str__(self):
        return "%s at pos (%d, %d) in %r" % (self.__class__.__name__,
                                             self.lineno,
                                             self.offset,
                                             self.text)

class IndentationError(SyntaxError):
    pass

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
