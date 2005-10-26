
class SyntaxError(Exception):
    """Base class for exceptions raised by the parser."""

    def __init__(self, msg, lineno=0, offset=0, text=None, filename=None):
        self.msg = msg
        self.lineno = lineno
        self.offset = offset
        self.text = text
        self.filename = filename
        self.print_file_and_line = False

    def wrap_info(self, space, filename):
        return space.newtuple([space.wrap(self.msg),
                               space.newtuple([space.wrap(filename),
                                               space.wrap(self.lineno),
                                               space.wrap(self.offset),
                                               space.wrap(self.text)])])

    def __str__(self):
        return "%s at pos (%d, %d) in %r" % (self.__class__.__name__,
                                             self.lineno,
                                             self.offset,
                                             self.text)


class ASTError(Exception):
    def __init__(self, msg, ast_node ):
        self.msg = msg
        self.ast_node = ast_node


class TokenError(Exception):
    def __init__(self, msg, tokens ):
        self.msg = msg
        self.tokens = tokens
    
