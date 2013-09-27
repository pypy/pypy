class ParseError(Exception): pass
class ConversionError(Exception): pass

class PrologError(Exception):
    def __init__(self, message, term):
        Exception.__init__(self, message)
        self.message = message
        self.term = term
