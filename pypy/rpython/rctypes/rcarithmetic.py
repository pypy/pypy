from pypy.rpython import rarithmetic
from pypy.rpython.lltypesystem import lltype
import ctypes

def c_type_size(c_type):
    bits = 0
    while c_type(1<<bits).value != 0:
        bits += 1
    sign = c_type(-1).value < 0
    return sign, bits

def setup():
    for _name in 'byte short int long longlong'.split():
        for name in (_name, 'u' + _name):
            c_type = getattr(ctypes, 'c_' + name)
            sign, bits = c_type_size(c_type)
            inttype = rarithmetic.build_int('rc' + name, sign, bits)
            globals()['rc'+name] = inttype 
            if name[0] == 'u':
                llname = 'CU' + name[1:].title()
            else:
                llname = 'C' + name.title()
            globals()[llname] = lltype.build_number(llname, inttype)
setup()
del setup


