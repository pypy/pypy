from pypy.interpreter.error import OperationError
from pypy.interpreter import unicodehelper
from pypy.rlib.rstring import StringBuilder

def parsestr(space, encoding, s, unicode_literal=False):
    """Parses a string or unicode literal, and return a wrapped value.

    If encoding=iso8859-1, the source string is also in this encoding.
    If encoding=None, the source string is ascii only.
    In other cases, the source string is in utf-8 encoding.

    When a bytes string is returned, it will be encoded with the
    original encoding.

    Yes, it's very inefficient.
    Yes, CPython has very similar code.
    """

    # we use ps as "pointer to s"
    # q is the virtual last char index of the string
    ps = 0
    quote = s[ps]
    rawmode = False

    # string decoration handling
    o = ord(quote)
    isalpha = (o>=97 and o<=122) or (o>=65 and o<=90)
    if isalpha or quote == '_':
        if quote == 'b' or quote == 'B':
            ps += 1
            quote = s[ps]
            unicode_literal = False
        elif quote == 'u' or quote == 'U':
            ps += 1
            quote = s[ps]
            unicode_literal = True
        if quote == 'r' or quote == 'R':
            ps += 1
            quote = s[ps]
            rawmode = True
    if quote != "'" and quote != '"':
        raise_app_valueerror(space,
                             'Internal error: parser passed unquoted literal')
    ps += 1
    q = len(s) - 1
    if s[q] != quote:
        raise_app_valueerror(space, 'Internal error: parser passed unmatched '
                                    'quotes in literal')
    if q-ps >= 4 and s[ps] == quote and s[ps+1] == quote:
        # triple quotes
        ps += 2
        if s[q-1] != quote or s[q-2] != quote:
            raise_app_valueerror(space, 'Internal error: parser passed '
                                        'unmatched triple quotes in literal')
        q -= 2

    if unicode_literal: # XXX Py_UnicodeFlag is ignored for now
        if encoding is None or encoding == "iso-8859-1":
            # 'unicode_escape' expects latin-1 bytes, string is ready.
            buf = s
            bufp = ps
            bufq = q
            u = None
        else:
            # String is utf8-encoded, but 'unicode_escape' expects
            # latin-1; So multibyte sequences must be escaped.
            lis = [] # using a list to assemble the value
            end = q
            # Worst case: "\XX" may become "\u005c\uHHLL" (12 bytes)
            while ps < end:
                if s[ps] == '\\':
                    lis.append(s[ps])
                    ps += 1
                    if ord(s[ps]) & 0x80:
                        # A multibyte sequence will follow, it will be
                        # escaped like \u1234. To avoid confusion with
                        # the backslash we just wrote, we emit "\u005c"
                        # instead.
                        lis.append("u005c")
                if ord(s[ps]) & 0x80: # XXX inefficient
                    w, ps = decode_utf8(space, s, ps, end, "utf-16-be")
                    rn = len(w)
                    assert rn % 2 == 0
                    for i in range(0, rn, 2):
                        lis.append('\\u')
                        lis.append(hexbyte(ord(w[i])))
                        lis.append(hexbyte(ord(w[i+1])))
                else:
                    lis.append(s[ps])
                    ps += 1
            buf = ''.join(lis)
            bufp = 0
            bufq = len(buf)
        assert 0 <= bufp <= bufq
        substr = buf[bufp:bufq]
        if rawmode:
            v = unicodehelper.PyUnicode_DecodeRawUnicodeEscape(space, substr)
        else:
            v = unicodehelper.PyUnicode_DecodeUnicodeEscape(space, substr)
        return space.wrap(v)

    need_encoding = (encoding is not None and
                     encoding != "utf-8" and encoding != "iso-8859-1")
    assert 0 <= ps <= q
    substr = s[ps : q]
    if rawmode or '\\' not in s[ps:]:
        if need_encoding:
            w_u = space.wrap(unicodehelper.PyUnicode_DecodeUTF8(space, substr))
            w_v = unicodehelper.PyUnicode_AsEncodedString(space, w_u, space.wrap(encoding))
            return w_v
        else:
            return space.wrap(substr)

    enc = None
    if need_encoding:
         enc = encoding
    v = PyString_DecodeEscape(space, substr, enc)
    return space.wrap(v)

def hexbyte(val):
    result = "%x" % val
    if len(result) == 1:
        result = "0" + result
    return result

def PyString_DecodeEscape(space, s, recode_encoding):
    """
    Unescape a backslash-escaped string. If recode_encoding is non-zero,
    the string is UTF-8 encoded and should be re-encoded in the
    specified encoding.
    """
    builder = StringBuilder(len(s))
    ps = 0
    end = len(s)
    while 1:
        ps2 = ps
        while ps < end and s[ps] != '\\':
            if recode_encoding and ord(s[ps]) & 0x80:
                w, ps = decode_utf8(space, s, ps, end, recode_encoding)
                builder.append(w)
                ps2 = ps
            else:
                ps += 1
        if ps > ps2:
            builder.append_slice(s, ps2, ps)
        if ps == end:
            break

        ps += 1
        if ps == end:
            raise_app_valueerror(space, 'Trailing \\ in string')
        prevps = ps
        ch = s[ps]
        ps += 1
        # XXX This assumes ASCII!
        if ch == '\n':
            pass
        elif ch == '\\':
            builder.append('\\')
        elif ch == "'":
            builder.append("'")
        elif ch == '"':
            builder.append('"')
        elif ch == 'b':
            builder.append("\010")
        elif ch == 'f':
            builder.append('\014') # FF
        elif ch == 't':
            builder.append('\t')
        elif ch == 'n':
            builder.append('\n')
        elif ch == 'r':
            builder.append('\r')
        elif ch == 'v':
            builder.append('\013') # VT
        elif ch == 'a':
            builder.append('\007') # BEL, not classic C
        elif ch in '01234567':
            # Look for up to two more octal digits
            span = ps
            span += (span < end) and (s[span] in '01234567')
            span += (span < end) and (s[span] in '01234567')
            octal = s[prevps : span]
            # emulate a strange wrap-around behavior of CPython:
            # \400 is the same as \000 because 0400 == 256
            num = int(octal, 8) & 0xFF
            builder.append(chr(num))
            ps = span
        elif ch == 'x':
            if ps+2 <= end and isxdigit(s[ps]) and isxdigit(s[ps + 1]):
                hexa = s[ps : ps + 2]
                num = int(hexa, 16)
                builder.append(chr(num))
                ps += 2
            else:
                raise_app_valueerror(space, 'invalid \\x escape')
            # ignored replace and ignore for now

        else:
            # this was not an escape, so the backslash
            # has to be added, and we start over in
            # non-escape mode.
            builder.append('\\')
            ps -= 1
            assert ps >= 0
            continue
            # an arbitry number of unescaped UTF-8 bytes may follow.

    buf = builder.build()
    return buf


def isxdigit(ch):
    return (ch >= '0' and ch <= '9' or
            ch >= 'a' and ch <= 'f' or
            ch >= 'A' and ch <= 'F')


def decode_utf8(space, s, ps, end, encoding):
    assert ps >= 0
    pt = ps
    # while (s < end && *s != '\\') s++; */ /* inefficient for u".."
    while ps < end and ord(s[ps]) & 0x80:
        ps += 1
    w_u = space.wrap(unicodehelper.PyUnicode_DecodeUTF8(space, s[pt:ps]))
    w_v = unicodehelper.PyUnicode_AsEncodedString(space, w_u, space.wrap(encoding))
    v = space.str_w(w_v)
    return v, ps

def raise_app_valueerror(space, msg):
    raise OperationError(space.w_ValueError, space.wrap(msg))
