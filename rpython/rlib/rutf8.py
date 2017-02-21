
from rpython.rlib.rstring import StringBuilder

def unichr_as_utf8(code):
    """ Encode code (numeric value) as utf8 encoded string
    """
    if code < 0:
        raise ValueError
    if code < 0x80:
        # Encode ASCII
        return chr(code)
    if code < 0x0800:
        # Encode Latin-1
        return chr((0xc0 | (code >> 6))) + chr((0x80 | (code & 0x3f)))
    if code < 0x10000:
        return (chr((0xe0 | (code >> 12))) +
                chr((0x80 | ((code >> 6) & 0x3f))) +
                chr((0x80 | (code & 0x3f))))
    if code < 0x10ffff:
        return (chr((0xf0 | (code >> 18))) +
                chr((0x80 | ((code >> 12) & 0x3f))) +
                chr((0x80 | ((code >> 6) & 0x3f))) +
                chr((0x80 | (code & 0x3f))))
    raise ValueError

class AsciiCheckError(Exception):
    def __init__(self, pos):
        self.pos = pos

def check_ascii(s):
    for i in range(0, len(s)):
        if ord(s[i]) & 0x80:
            raise AsciiCheckError(i)

def str_decode_raw_utf8_escape(s, size, errors, final=False,
                               errorhandler=None):
    lgt = 0
    if errorhandler is None:
        errorhandler = None # default_unicode_error_decode
    if size == 0:
        return '', 0, 0
    result = StringBuilder(size)
    pos = 0
    while pos < size:
        ch = s[pos]

        # Non-escape characters are interpreted as Unicode ordinals
        if ch != '\\':
            result.append(ch)
            pos += 1
            lgt += 1
            continue

        # \u-escapes are only interpreted iff the number of leading
        # backslashes is odd
        bs = pos
        while pos < size:
            pos += 1
            if pos == size or s[pos] != '\\':
                break
            lgt += 1
            result.append('\\')

        # we have a backslash at the end of the string, stop here
        if pos >= size:
            lgt += 1
            result.append('\\')
            break

        if ((pos - bs) & 1 == 0 or
            pos >= size or
            (s[pos] != 'u' and s[pos] != 'U')):
            result.append('\\')
            result.append(s[pos])
            lgt += 2
            pos += 1
            continue

        digits = 4 if s[pos] == 'u' else 8
        message = "truncated \\uXXXX"
        pos += 1
        xxx # change hexescape to deal with utf8
        pos = hexescape(result, s, pos, digits,
                        "rawunicodeescape", errorhandler, message, errors)

    return result.build(), pos, lgt

def str_decode_utf8_escape(s, size, errors, final=False,
                              errorhandler=None,
                              unicodedata_handler=None):
    if errorhandler is None:
        errorhandler = default_unicode_error_decode

    if size == 0:
        return '', 0

    lgt = 0
    builder = StringBuilder(size)
    pos = 0
    while pos < size:
        ch = s[pos]

        # Non-escape characters are interpreted as Unicode ordinals
        if ch != '\\':
            builder.append(ch)
            pos += 1
            lgt += 1
            continue

        # - Escapes
        pos += 1
        if pos >= size:
            message = "\\ at end of string"
            res, pos = errorhandler(errors, "unicodeescape",
                                    message, s, pos-1, size)
            builder.append(res)
            lgt += 1
            continue

        ch = s[pos]
        pos += 1
        # \x escapes
        if ch == '\n': pass
        elif ch == '\\': builder.append('\\'); lgt += 1
        elif ch == '\'': builder.append('\''); lgt += 1
        elif ch == '\"': builder.append('\"'); lgt += 1
        elif ch == 'b' : builder.append('\b'); lgt += 1
        elif ch == 'f' : builder.append('\f'); lgt += 1
        elif ch == 't' : builder.append('\t'); lgt += 1
        elif ch == 'n' : builder.append('\n'); lgt += 1
        elif ch == 'r' : builder.append('\r'); lgt += 1
        elif ch == 'v' : builder.append('\v'); lgt += 1
        elif ch == 'a' : builder.append('\a'); lgt += 1
        elif '0' <= ch <= '7':
            xxx
            x = ord(ch) - ord('0')
            if pos < size:
                ch = s[pos]
                if '0' <= ch <= '7':
                    pos += 1
                    x = (x<<3) + ord(ch) - ord('0')
                    if pos < size:
                        ch = s[pos]
                        if '0' <= ch <= '7':
                            pos += 1
                            x = (x<<3) + ord(ch) - ord('0')
            builder.append(unichr(x))
        # hex escapes
        # \xXX
        elif ch == 'x':
            xxx
            digits = 2
            message = "truncated \\xXX escape"
            pos = hexescape(builder, s, pos, digits,
                            "unicodeescape", errorhandler, message, errors)

        # \uXXXX
        elif ch == 'u':
            xxx
            digits = 4
            message = "truncated \\uXXXX escape"
            pos = hexescape(builder, s, pos, digits,
                            "unicodeescape", errorhandler, message, errors)

        #  \UXXXXXXXX
        elif ch == 'U':
            xxx
            digits = 8
            message = "truncated \\UXXXXXXXX escape"
            pos = hexescape(builder, s, pos, digits,
                            "unicodeescape", errorhandler, message, errors)

        # \N{name}
        elif ch == 'N' and unicodedata_handler is not None:
            xxx
            message = "malformed \\N character escape"
            look = pos

            if look < size and s[look] == '{':
                # look for the closing brace
                while look < size and s[look] != '}':
                    look += 1
                if look < size and s[look] == '}':
                    # found a name.  look it up in the unicode database
                    message = "unknown Unicode character name"
                    name = s[pos+1:look]
                    code = unicodedata_handler.call(name)
                    if code < 0:
                        res, pos = errorhandler(errors, "unicodeescape",
                                                message, s, pos-1, look+1)
                        builder.append(res)
                        continue
                    pos = look + 1
                    if code <= MAXUNICODE:
                        builder.append(UNICHR(code))
                    else:
                        code -= 0x10000L
                        builder.append(unichr(0xD800 + (code >> 10)))
                        builder.append(unichr(0xDC00 + (code & 0x03FF)))
                else:
                    res, pos = errorhandler(errors, "unicodeescape",
                                            message, s, pos-1, look+1)
                    builder.append(res)
            else:
                res, pos = errorhandler(errors, "unicodeescape",
                                        message, s, pos-1, look+1)
                builder.append(res)
        else:
            builder.append('\\')
            builder.append(ch)
            lgt += 2

    return builder.build(), pos, lgt
