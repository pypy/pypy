from pypy.rpython import lltype
from pypy.rpython import extfunctable
from pypy.rpython.rstr import STR
from pypy.rpython.lltype import GcStruct, Signed, Array, Char, Ptr, malloc


# utility conversion functions
def to_rstr(s):
    p = malloc(STR, len(s))
    for i in range(len(s)):
        p.chars[i] = s[i]
    return p

def from_rstr(rs):
    return ''.join([rs.chars[i] for i in range(len(rs.chars))])

def ll_strcpy(dstchars, srcchars, n):
    i = 0
    while i < n:
        dstchars[i] = srcchars[i]
        i += 1

def init_opaque_object(opaqueptr, value):
    "NOT_RPYTHON"
    opaqueptr._obj.externalobj = value
init_opaque_object._annspecialcase_ = "override:init_opaque_object"

def from_opaque_object(opaqueptr):
    "NOT_RPYTHON"
    return opaqueptr._obj.externalobj
from_opaque_object._annspecialcase_ = "override:from_opaque_object"
