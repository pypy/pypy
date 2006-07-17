# some code has been stolen from genc
def string_literal(s):
    def char_repr(c):
        if c in '\\"': return '\\' + c
        if ' ' <= c < '\x7F': return c
        if c == '\n': return '\\n'
        if c == '\t': return '\\t'
        return '\\%03o' % ord(c)
    def line_repr(s):
        return ''.join([char_repr(c) for c in s])

    return '"%s"' % line_repr(s)

