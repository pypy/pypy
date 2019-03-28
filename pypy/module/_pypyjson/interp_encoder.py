from rpython.rlib.rstring import StringBuilder
from rpython.rlib import rutf8
from pypy.interpreter import unicodehelper


HEX = '0123456789abcdef'

ESCAPE_DICT = {
    '\b': '\\b',
    '\f': '\\f',
    '\n': '\\n',
    '\r': '\\r',
    '\t': '\\t',
}
ESCAPE_BEFORE_SPACE = [ESCAPE_DICT.get(chr(_i), '\\u%04x' % _i)
                       for _i in range(32)]


def raw_encode_basestring_ascii(space, w_string):
    if space.isinstance_w(w_string, space.w_bytes):
        s = space.bytes_w(w_string)
        for i in range(len(s)):
            c = s[i]
            if c >= ' ' and c <= '~' and c != '"' and c != '\\':
                pass
            else:
                first = i
                break
        else:
            # the input is a string with only non-special ascii chars
            return w_string

        unicodehelper.check_utf8_or_raise(space, s)
        sb = StringBuilder(len(s))
        sb.append_slice(s, 0, first)
    else:
        # We used to check if 'u' contains only safe characters, and return
        # 'w_string' directly.  But this requires an extra pass over all
        # characters, and the expected use case of this function, from
        # json.encoder, will anyway re-encode a unicode result back to
        # a string (with the ascii encoding).  This requires two passes
        # over the characters.  So we may as well directly turn it into a
        # string here --- only one pass.
        s = space.utf8_w(w_string)
        sb = StringBuilder(len(s))
        first = 0

    it = rutf8.Utf8StringIterator(s)
    for i in range(first):
        it.next()
    for c in it:
        if c <= ord('~'):
            if c == ord('"') or c == ord('\\'):
                sb.append('\\')
            elif c < ord(' '):
                sb.append(ESCAPE_BEFORE_SPACE[c])
                continue
            sb.append(chr(c))
        else:
            if c <= ord(u'\uffff'):
                sb.append('\\u')
                sb.append(HEX[c >> 12])
                sb.append(HEX[(c >> 8) & 0x0f])
                sb.append(HEX[(c >> 4) & 0x0f])
                sb.append(HEX[c & 0x0f])
            else:
                # surrogate pair
                n = c - 0x10000
                s1 = 0xd800 | ((n >> 10) & 0x3ff)
                sb.append('\\ud')
                sb.append(HEX[(s1 >> 8) & 0x0f])
                sb.append(HEX[(s1 >> 4) & 0x0f])
                sb.append(HEX[s1 & 0x0f])
                s2 = 0xdc00 | (n & 0x3ff)
                sb.append('\\ud')
                sb.append(HEX[(s2 >> 8) & 0x0f])
                sb.append(HEX[(s2 >> 4) & 0x0f])
                sb.append(HEX[s2 & 0x0f])

    res = sb.build()
    return space.newtext(res)
