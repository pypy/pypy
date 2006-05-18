from pypy.rpython.ootypesystem.ootype import new, oostring, StringBuilder

def const(c):
    return c

def ll_int_str(repr, i):
    return ll_int2dec(i)

def ll_int2dec(i):
    return oostring(i, const(10))

def ll_int2hex(i, addPrefix):
    if not addPrefix:
        return oostring(i, const(16))

    buf = new(StringBuilder)
    if i<0:
        i = -i
        buf.ll_append_char('-')

    buf.ll_append_char('0')
    buf.ll_append_char('x')
    buf.ll_append(oostring(i, const(16)))
    return buf.ll_build()

def ll_int2oct(i, addPrefix):
    if not addPrefix or i==0:
        return oostring(i, const(8))

    buf = new(StringBuilder)
    if i<0:
        i = -i
        buf.ll_append_char('-')

    buf.ll_append_char('0')
    buf.ll_append(oostring(i, const(8)))
    return buf.ll_build()


