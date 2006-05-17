from pypy.rpython.ootypesystem import ootype

def const(c):
    return c

def ll_int2dec(i):
    return ootype.oostring(i, const(10))

# TODO: add support for addPrefix == False
def ll_int2hex(i, addPrefix):
    #assert addPrefix
    return ootype.oostring(i, const(16))

def ll_int2oct(i, addPrefix):
    #assert addPrefix
    return ootype.oostring(i, const(8))

