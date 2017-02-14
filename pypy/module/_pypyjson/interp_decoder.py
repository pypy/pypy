import sys
from rpython.rlib.rstring import StringBuilder
from rpython.rlib.objectmodel import specialize, always_inline
from rpython.rlib import rfloat, runicode
from rpython.rtyper.lltypesystem import lltype, rffi
from pypy.interpreter.error import oefmt, OperationError
from pypy.interpreter import unicodehelper

OVF_DIGITS = len(str(sys.maxint))

def is_whitespace(ch):
    return ch == ' ' or ch == '\t' or ch == '\r' or ch == '\n'

# precomputing negative powers of 10 is MUCH faster than using e.g. math.pow
# at runtime
NEG_POW_10 = [10.0**-i for i in range(16)]
def neg_pow_10(x, exp):
    if exp >= len(NEG_POW_10):
        return 0.0
    return x * NEG_POW_10[exp]

def strslice2unicode_latin1(s, start, end):
    """
    Convert s[start:end] to unicode. s is supposed to be an RPython string
    encoded in latin-1, which means that the numeric value of each char is the
    same as the corresponding unicode code point.

    Internally it's implemented at the level of low-level helpers, to avoid
    the extra copy we would need if we take the actual slice first.

    No bound checking is done, use carefully.
    """
    from rpython.rtyper.annlowlevel import llstr, hlunicode
    from rpython.rtyper.lltypesystem.rstr import malloc, UNICODE
    from rpython.rtyper.lltypesystem.lltype import cast_primitive, UniChar
    length = end-start
    ll_s = llstr(s)
    ll_res = malloc(UNICODE, length)
    ll_res.hash = 0
    for i in range(length):
        ch = ll_s.chars[start+i]
        ll_res.chars[i] = cast_primitive(UniChar, ch)
    return hlunicode(ll_res)

class DecoderError(Exception):
    def __init__(self, msg, pos):
        self.msg = msg
        self.pos = pos

TYPE_UNKNOWN = 0
TYPE_STRING = 1
class JSONDecoder(object):
    def __init__(self, space, s):
        self.space = space
        self.s = s
        # we put our string in a raw buffer so:
        # 1) we automatically get the '\0' sentinel at the end of the string,
        #    which means that we never have to check for the "end of string"
        # 2) we can pass the buffer directly to strtod
        self.ll_chars = rffi.str2charp(s)
        self.end_ptr = lltype.malloc(rffi.CCHARPP.TO, 1, flavor='raw')
        self.pos = 0
        self.last_type = TYPE_UNKNOWN
        self.memo = {}

    def close(self):
        rffi.free_charp(self.ll_chars)
        lltype.free(self.end_ptr, flavor='raw')

    def getslice(self, start, end):
        assert start >= 0
        assert end >= 0
        return self.s[start:end]

    def skip_whitespace(self, i):
        while True:
            ch = self.ll_chars[i]
            if is_whitespace(ch):
                i+=1
            else:
                break
        return i

    def decode_any(self, i):
        i = self.skip_whitespace(i)
        ch = self.ll_chars[i]
        if ch == '"':
            return self.decode_string(i+1)
        elif ch == '[':
            return self.decode_array(i+1)
        elif ch == '{':
            return self.decode_object(i+1)
        elif ch == 'n':
            return self.decode_null(i+1)
        elif ch == 't':
            return self.decode_true(i+1)
        elif ch == 'f':
            return self.decode_false(i+1)
        elif ch == 'I':
            return self.decode_infinity(i+1)
        elif ch == 'N':
            return self.decode_nan(i+1)
        elif ch == '-':
            if self.ll_chars[i+1] == 'I':
                return self.decode_infinity(i+2, sign=-1)
            return self.decode_numeric(i)
        elif ch.isdigit():
            return self.decode_numeric(i)
        else:
            raise DecoderError("Unexpected '%s' at" % ch, i)

    def decode_null(self, i):
        if (self.ll_chars[i]   == 'u' and
            self.ll_chars[i+1] == 'l' and
            self.ll_chars[i+2] == 'l'):
            self.pos = i+3
            return self.space.w_None
        raise DecoderError("Error when decoding null at", i)

    def decode_true(self, i):
        if (self.ll_chars[i]   == 'r' and
            self.ll_chars[i+1] == 'u' and
            self.ll_chars[i+2] == 'e'):
            self.pos = i+3
            return self.space.w_True
        raise DecoderError("Error when decoding true at", i)

    def decode_false(self, i):
        if (self.ll_chars[i]   == 'a' and
            self.ll_chars[i+1] == 'l' and
            self.ll_chars[i+2] == 's' and
            self.ll_chars[i+3] == 'e'):
            self.pos = i+4
            return self.space.w_False
        raise DecoderError("Error when decoding false at", i)

    def decode_infinity(self, i, sign=1):
        if (self.ll_chars[i]   == 'n' and
            self.ll_chars[i+1] == 'f' and
            self.ll_chars[i+2] == 'i' and
            self.ll_chars[i+3] == 'n' and
            self.ll_chars[i+4] == 'i' and
            self.ll_chars[i+5] == 't' and
            self.ll_chars[i+6] == 'y'):
            self.pos = i+7
            return self.space.newfloat(rfloat.INFINITY * sign)
        raise DecoderError("Error when decoding Infinity at", i)

    def decode_nan(self, i):
        if (self.ll_chars[i]   == 'a' and
            self.ll_chars[i+1] == 'N'):
            self.pos = i+2
            return self.space.newfloat(rfloat.NAN)
        raise DecoderError("Error when decoding NaN at", i)

    def decode_numeric(self, i):
        start = i
        i, ovf_maybe, intval = self.parse_integer(i)
        #
        # check for the optional fractional part
        ch = self.ll_chars[i]
        if ch == '.':
            if not self.ll_chars[i+1].isdigit():
                raise DecoderError("Expected digit at", i+1)
            return self.decode_float(start)
        elif ch == 'e' or ch == 'E':
            return self.decode_float(start)
        elif ovf_maybe:
            return self.decode_int_slow(start)

        self.pos = i
        return self.space.newint(intval)

    def decode_float(self, i):
        from rpython.rlib import rdtoa
        start = rffi.ptradd(self.ll_chars, i)
        floatval = rdtoa.dg_strtod(start, self.end_ptr)
        diff = rffi.cast(rffi.LONG, self.end_ptr[0]) - rffi.cast(rffi.LONG, start)
        self.pos = i + diff
        return self.space.newfloat(floatval)

    def decode_int_slow(self, i):
        start = i
        if self.ll_chars[i] == '-':
            i += 1
        while self.ll_chars[i].isdigit():
            i += 1
        s = self.getslice(start, i)
        self.pos = i
        return self.space.call_function(self.space.w_int, self.space.newtext(s))

    @always_inline
    def parse_integer(self, i):
        "Parse a decimal number with an optional minus sign"
        sign = 1
        # parse the sign
        if self.ll_chars[i] == '-':
            sign = -1
            i += 1
        elif self.ll_chars[i] == '+':
            i += 1
        #
        if self.ll_chars[i] == '0':
            i += 1
            return i, False, 0

        intval = 0
        start = i
        while True:
            ch = self.ll_chars[i]
            if ch.isdigit():
                intval = intval*10 + ord(ch)-ord('0')
                i += 1
            else:
                break
        count = i - start
        if count == 0:
            raise DecoderError("Expected digit at", i)
        # if the number has more digits than OVF_DIGITS, it might have
        # overflowed
        ovf_maybe = (count >= OVF_DIGITS)
        return i, ovf_maybe, sign * intval

    def decode_array(self, i):
        w_list = self.space.newlist([])
        start = i
        i = self.skip_whitespace(start)
        if self.ll_chars[i] == ']':
            self.pos = i+1
            return w_list
        #
        while True:
            w_item = self.decode_any(i)
            i = self.pos
            self.space.call_method(w_list, 'append', w_item)
            i = self.skip_whitespace(i)
            ch = self.ll_chars[i]
            i += 1
            if ch == ']':
                self.pos = i
                return w_list
            elif ch == ',':
                pass
            elif ch == '\0':
                raise DecoderError("Unterminated array starting at", start)
            else:
                raise DecoderError("Unexpected '%s' when decoding array" % ch,
                                   i-1)

    def decode_object(self, i):
        start = i
        w_dict = self.space.newdict()
        #
        i = self.skip_whitespace(i)
        if self.ll_chars[i] == '}':
            self.pos = i+1
            return w_dict
        #
        while True:
            # parse a key: value
            self.last_type = TYPE_UNKNOWN
            w_name = self.decode_any(i)
            if self.last_type != TYPE_STRING:
                raise DecoderError("Key name must be string for object starting at", start)
            w_name = self.memo.setdefault(self.space.unicode_w(w_name), w_name)

            i = self.skip_whitespace(self.pos)
            ch = self.ll_chars[i]
            if ch != ':':
                raise DecoderError("No ':' found at", i)
            i += 1
            i = self.skip_whitespace(i)
            #
            w_value = self.decode_any(i)
            self.space.setitem(w_dict, w_name, w_value)
            i = self.skip_whitespace(self.pos)
            ch = self.ll_chars[i]
            i += 1
            if ch == '}':
                self.pos = i
                return w_dict
            elif ch == ',':
                pass
            elif ch == '\0':
                raise DecoderError("Unterminated object starting at", start)
            else:
                raise DecoderError("Unexpected '%s' when decoding object" % ch,
                                   i-1)


    def decode_string(self, i):
        start = i
        bits = 0
        while True:
            # this loop is a fast path for strings which do not contain escape
            # characters
            ch = self.ll_chars[i]
            i += 1
            bits |= ord(ch)
            if ch == '"':
                if bits & 0x80:
                    # the 8th bit is set, it's an utf8 strnig
                    content_utf8 = self.getslice(start, i-1)
                    content_unicode = unicodehelper.decode_utf8(self.space, content_utf8)
                else:
                    # ascii only, fast path (ascii is a strict subset of
                    # latin1, and we already checked that all the chars are <
                    # 128)
                    content_unicode = strslice2unicode_latin1(self.s, start, i-1)
                self.last_type = TYPE_STRING
                self.pos = i
                return self.space.newunicode(content_unicode)
            elif ch == '\\' or ch < '\x20':
                self.pos = i-1
                return self.decode_string_escaped(start)


    def decode_string_escaped(self, start):
        i = self.pos
        builder = StringBuilder((i - start) * 2) # just an estimate
        assert start >= 0
        assert i >= 0
        builder.append_slice(self.s, start, i)
        while True:
            ch = self.ll_chars[i]
            i += 1
            if ch == '"':
                content_utf8 = builder.build()
                content_unicode = unicodehelper.decode_utf8(
                    self.space, content_utf8, allow_surrogates=True)
                self.last_type = TYPE_STRING
                self.pos = i
                return self.space.newunicode(content_unicode)
            elif ch == '\\':
                i = self.decode_escape_sequence(i, builder)
            elif ch < '\x20':
                if ch == '\0':
                    raise DecoderError("Unterminated string starting at",
                                       start - 1)
                else:
                    raise DecoderError("Invalid control character at", i-1)
            else:
                builder.append(ch)

    def decode_escape_sequence(self, i, builder):
        ch = self.ll_chars[i]
        i += 1
        put = builder.append
        if ch == '\\':  put('\\')
        elif ch == '"': put('"' )
        elif ch == '/': put('/' )
        elif ch == 'b': put('\b')
        elif ch == 'f': put('\f')
        elif ch == 'n': put('\n')
        elif ch == 'r': put('\r')
        elif ch == 't': put('\t')
        elif ch == 'u':
            return self.decode_escape_sequence_unicode(i, builder)
        else:
            raise DecoderError("Invalid \\escape: %s" % ch, i-1)
        return i

    def decode_escape_sequence_unicode(self, i, builder):
        # at this point we are just after the 'u' of the \u1234 sequence.
        start = i
        i += 4
        hexdigits = self.getslice(start, i)
        try:
            val = int(hexdigits, 16)
            if sys.maxunicode > 65535 and 0xd800 <= val <= 0xdfff:
                # surrogate pair
                if self.ll_chars[i] == '\\' and self.ll_chars[i+1] == 'u':
                    val = self.decode_surrogate_pair(i, val)
                    i += 6
        except ValueError:
            raise DecoderError("Invalid \\uXXXX escape", i-1)
        #
        uchr = runicode.code_to_unichr(val)     # may be a surrogate pair again
        utf8_ch = unicodehelper.encode_utf8(
            self.space, uchr, allow_surrogates=True)
        builder.append(utf8_ch)
        return i

    def decode_surrogate_pair(self, i, highsurr):
        """ uppon enter the following must hold:
              chars[i] == "\\" and chars[i+1] == "u"
        """
        i += 2
        hexdigits = self.getslice(i, i+4)
        lowsurr = int(hexdigits, 16) # the possible ValueError is caugth by the caller
        return 0x10000 + (((highsurr - 0xd800) << 10) | (lowsurr - 0xdc00))

def loads(space, w_s, w_errorcls=None):
    if space.isinstance_w(w_s, space.w_bytes):
        raise oefmt(space.w_TypeError, "Expected string, got %T", w_s)
    s = space.str_w(w_s)
    decoder = JSONDecoder(space, s)
    try:
        w_res = decoder.decode_any(0)
        i = decoder.skip_whitespace(decoder.pos)
        if i < len(s):
            start = i
            raise DecoderError('Extra data', start)
        return w_res
    except DecoderError as e:
        if w_errorcls is None:
            w_errorcls = space.w_ValueError
        w_e = space.call_function(w_errorcls, space.wrap(e.msg), w_s,
                                  space.wrap(e.pos))
        raise OperationError(w_errorcls, w_e)
    finally:
        decoder.close()
