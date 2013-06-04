from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter import unicodehelper

def is_whitespace(ch):
    return ch == ' ' or ch == '\t' or ch == '\r' or ch == '\n'

TYPE_INVALID = 0
TYPE_STRING = 0

class JSONDecoder(object):
    def __init__(self, space, s):
        self.space = space
        self.s = s
        self.i = 0
        self.last_type = TYPE_INVALID

    def eof(self):
        return self.i == len(self.s)

    def peek(self):
        return self.s[self.i]

    def next(self):
        ch = self.peek()
        self.i += 1
        return ch

    def skip_whitespace(self):
        while not self.eof():
            ch = self.peek()
            if is_whitespace(ch):
                self.next()
            else:
                break

    def decode_any(self):
        self.skip_whitespace()
        ch = self.peek()
        if ch == '"':
            return self.decode_string()
        else:
            assert False, 'Unkown char: %s' % ch

    def decode_string(self):
        self.next()
        start = self.i
        while True:
            ch = self.next()
            if ch == '"':
                end = self.i-1
                assert end > 0
                content = self.s[start:end]
                self.last_type = TYPE_STRING
                return self.space.wrap(unicodehelper.decode_utf8(self.space, content))
            elif ch == '\\':
                raise Exception("escaped strings not supported yet")


@unwrap_spec(s=str)
def loads(space, s):
    decoder = JSONDecoder(space, s)
    w_res = decoder.decode_any()
    decoder.skip_whitespace()
    if not decoder.eof():
        start = decoder.i
        end = len(decoder.s)
        raise operationerrfmt(space.w_ValueError, "Extra data: char %d - %d", start, end)
    return w_res
