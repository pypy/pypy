import sys
from pypy.rpython.ootypesystem.ootype import new, oostring, StringBuilder
from pypy.rpython.ootypesystem.ootype import make_string

def ll_int_str(repr, i):
    return ll_int2dec(i)

def ll_int2dec(i):
    return oostring(i, 10)

SPECIAL_VALUE     = -sys.maxint-1
SPECIAL_VALUE_HEX = make_string(
    '-' + hex(sys.maxint+1).replace('L', '').replace('l', ''))
SPECIAL_VALUE_OCT = make_string(
    '-' + oct(sys.maxint+1).replace('L', '').replace('l', ''))

def ll_int2hex(i, addPrefix):
    if not addPrefix:
        return oostring(i, 16)

    buf = new(StringBuilder)
    if i<0:
        if i == SPECIAL_VALUE:
            return SPECIAL_VALUE_HEX
        i = -i
        buf.ll_append_char('-')

    buf.ll_append_char('0')
    buf.ll_append_char('x')
    buf.ll_append(oostring(i, 16))
    return buf.ll_build()

def ll_int2oct(i, addPrefix):
    if not addPrefix or i==0:
        return oostring(i, 8)

    buf = new(StringBuilder)
    if i<0:
        if i == SPECIAL_VALUE:
            return SPECIAL_VALUE_OCT
        i = -i
        buf.ll_append_char('-')

    buf.ll_append_char('0')
    buf.ll_append(oostring(i, 8))
    return buf.ll_build()

def ll_float_str(repr, f):
    return oostring(f, -1)
