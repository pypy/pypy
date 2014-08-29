from rpython.rlib.rstring import StringBuilder


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
    if space.isinstance_w(w_string, space.w_str):
        s = space.str_w(w_string)
        for c in s:
            if c >= ' ' and c <= '~' and c != '"' and c != '\\':
                pass
            else:
                break
        else:
            # the input is a string with only non-special ascii chars
            return w_string

        w_string = space.call_method(w_string, 'decode', space.wrap('utf-8'))

    u = space.unicode_w(w_string)
    sb = StringBuilder()
    for c in u:
        if c <= u'~':
            if c == u'"' or c == u'\\':
                sb.append('\\')
            elif c < u' ':
                sb.append(ESCAPE_BEFORE_SPACE[ord(c)])
                continue
            sb.append(chr(ord(c)))
        else:
            if c <= u'\uffff':
                sb.append('\\u')
                sb.append(HEX[ord(c) >> 12])
                sb.append(HEX[(ord(c) >> 8) & 0x0f])
                sb.append(HEX[(ord(c) >> 4) & 0x0f])
                sb.append(HEX[ord(c) & 0x0f])
            else:
                # surrogate pair
                n = ord(c) - 0x10000
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
    return space.wrap(res)
