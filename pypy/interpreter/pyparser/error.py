from pypy.interpreter.error import OperationError


class ParseError(Exception):
    """Base class for exceptions raised by the parser."""

    def __init__(self, msg, lineno, offset, text):
        self.msg = msg
        self.lineno = lineno
        self.offset = offset
        self.text = text

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


class SyntaxError(Exception):
    """Base class for exceptions raised by the parser."""

    def __init__(self, msg, lineno=0, offset=0, text=0):
        self.msg = msg
        self.lineno = lineno
        self.offset = offset
        self.text = text
        self.filename = ""
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
