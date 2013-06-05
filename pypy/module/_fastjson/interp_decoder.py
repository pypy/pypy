from rpython.rlib.rstring import StringBuilder
from rpython.rlib.objectmodel import specialize
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter import unicodehelper

def is_whitespace(ch):
    return ch == ' ' or ch == '\t' or ch == '\r' or ch == '\n'

TYPE_UNKNOWN = 0
TYPE_STRING = 1

class JSONDecoder(object):
    def __init__(self, space, s):
        self.space = space
        self.s = s
        self.i = 0
        self.last_type = TYPE_UNKNOWN

    def eof(self):
        return self.i == len(self.s)

    def peek(self):
        return self.s[self.i]

    def next(self):
        ch = self.peek()
        self.i += 1
        return ch

    def unget(self):
        i2 = self.i - 1
        assert i2 > 0 # so that we can use self.i as slice start
        self.i = i2

    def getslice(self, start, end):
        assert end > 0
        return self.s[start:end]

    def skip_whitespace(self):
        while not self.eof():
            ch = self.peek()
            if is_whitespace(ch):
                self.next()
            else:
                break

    @specialize.arg(1)
    def _raise(self, msg, *args):
        raise operationerrfmt(self.space.w_ValueError, msg, *args)

    def decode_any(self):
        self.skip_whitespace()
        ch = self.peek()
        if ch == '"':
            self.next()
            return self.decode_string()
        elif ch.isdigit() or ch == '-':
            return self.decode_numeric(ch)
        elif ch == '{':
            self.next()
            return self.decode_object()
        else:
            assert False, 'Unkown char: %s' % ch

    def decode_numeric(self, ch):
        intval = 0
        sign = 1
        if ch == '-':
            sign = -1
            self.next()

        while not self.eof():
            ch = self.peek()
            if ch.isdigit():
                intval = intval*10 + ord(ch)-ord('0')
                self.next()
            else:
                break
        #
        intval = intval*sign
        return self.space.wrap(intval)

    def decode_object(self):
        start = self.i
        w_dict = self.space.newdict()
        while not self.eof():
            ch = self.peek()
            if ch == '}':
                self.next()
                return w_dict
            #
            # parse a key: value
            self.last_type = TYPE_UNKNOWN
            w_name = self.decode_any()
            if self.last_type != TYPE_STRING:
                self._raise("Key name must be string for object starting at char %d", start)
            self.skip_whitespace()
            ch = self.next()
            if ch != ':':
                self._raise("No ':' found at char %d", self.i)
            self.skip_whitespace()
            #
            w_value = self.decode_any()
            self.space.setitem(w_dict, w_name, w_value)
            self.skip_whitespace()
            ch = self.next()
            if ch == '}':
                return w_dict
            elif ch == ',':
                pass
            else:
                self._raise("Unexpected '%s' when decoding object (char %d)",
                            ch, self.i)
        self._raise("Unterminated object starting at char %d", start)



    def decode_string(self):
        start = self.i
        bits = 0
        while not self.eof():
            # this loop is a fast path for strings which do not contain escape
            # characters
            ch = self.next()
            bits |= ord(ch)
            if ch == '"':
                content_utf8 = self.getslice(start, self.i-1)
                if bits & 0x80:
                    # the 8th bit is set, it's an utf8 strnig
                    content_unicode = content_utf8.decode('utf-8')
                else:
                    # ascii only, faster to decode
                    content_unicode = content_utf8.decode('ascii')
                self.last_type = TYPE_STRING
                return self.space.wrap(content_unicode)
            elif ch == '\\':
                content_so_far = self.getslice(start, self.i-1)
                self.unget()
                return self.decode_string_escaped(start, content_so_far)
        self._raise("Unterminated string starting at char %d", start)


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
                self.decode_escape_sequence(builder)
            else:
                builder.append_multiple_char(ch, 1) # we should implement append_char
        #
        self._raise("Unterminated string starting at char %d", start)

    def decode_escape_sequence(self, builder):
        put = builder.append_multiple_char
        ch = self.next()
        if ch == '\\':  put('\\', 1)
        elif ch == '"': put('"' , 1)
        elif ch == '/': put('/' , 1)
        elif ch == 'b': put('\b', 1)
        elif ch == 'f': put('\f', 1)
        elif ch == 'n': put('\n', 1)
        elif ch == 'r': put('\r', 1)
        elif ch == 't': put('\t', 1)
        elif ch == 'u':
            return self.decode_escape_sequence_unicode(builder)
        else:
            self._raise("Invalid \\escape: %s (char %d)", ch, self.i-1)

    def decode_escape_sequence_unicode(self, builder):
        # at this point we are just after the 'u' of the \u1234 sequence.
        hexdigits = self.getslice(self.i, self.i+4)
        self.i += 4
        try:
            uchr = unichr(int(hexdigits, 16))
        except ValueError:
            self._raise("Invalid \uXXXX escape (char %d)", self.i-1)
        #
        utf8_ch = unicodehelper.encode_utf8(self.space, uchr)
        builder.append(utf8_ch)



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
