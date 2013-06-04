from rpython.rlib.rstring import StringBuilder
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

    def unget(self):
        self.i -= 1

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

    def getslice(self, start, end):
        assert end > 0
        return self.s[start:end]

    def decode_string(self):
        self.next()
        start = self.i
        while not self.eof():
            # this loop is a fast path for strings which do not contain escape
            # characters
            ch = self.next()
            if ch == '"':
                content_utf8 = self.getslice(start, self.i-1)
                content_unicode = unicodehelper.decode_utf8(self.space, content_utf8)
                self.last_type = TYPE_STRING
                return self.space.wrap(content_unicode)
            elif ch == '\\':
                content_so_far = self.getslice(start, self.i-1)
                self.unget()
                return self.decode_string_escaped(start, content_so_far)
        raise operationerrfmt(self.space.w_ValueError,
                              "Unterminated string starting at char %d", start)


    def decode_string_escaped(self, start, content_so_far):
        builder = StringBuilder(len(content_so_far)*2) # just an estimate
        builder.append(content_so_far)
        while not self.eof():
            ch = self.next()
            if ch == '"':
                content_utf8 = builder.build()
                content_unicode = unicodehelper.decode_utf8(self.space, content_utf8)
                self.last_type = TYPE_STRING
                return self.space.wrap(content_unicode)
            elif ch == '\\':
                newchar = self.decode_escape_sequence()
                builder.append_multiple_char(newchar, 1) # we should implement append_char
            else:
                builder.append_multiple_char(newchar, 1)
            
        raise operationerrfmt(self.space.w_ValueError,
                              "Unterminated string starting at char %d", start)

    def decode_escape_sequence(self):
        ch = self.next()
        if ch == '\\':  return '\\'
        elif ch == '"': return '"'
        elif ch == '/': return '/'
        elif ch == 'b': return '\b'
        elif ch == 'f': return '\f'
        elif ch == 'n': return '\n'
        elif ch == 'r': return '\r'
        elif ch == 't': return '\t'
        elif ch == 'u':
            assert False, 'not implemented yet'
        else:
            raise operationerrfmt(self.space.w_ValueError,
                                  "Invalid \\escape: %s (char %d)", ch, self.i-1)

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
