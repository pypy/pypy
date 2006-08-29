from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype
from pypy.rpython import extfunctable
from pypy.rpython.lltypesystem.lltype import \
     GcStruct, Signed, Array, Char, Ptr, malloc

# utility conversion functions

class LLSupport:
    _mixin_ = True
    
    def to_rstr(s):
        from pypy.rpython.lltypesystem.rstr import STR, mallocstr
        if s is None:
            return lltype.nullptr(STR)
        p = mallocstr(len(s))
        for i in range(len(s)):
            p.chars[i] = s[i]
        return p
    to_rstr = staticmethod(to_rstr)    

    def from_rstr(rs):
        if not rs:   # null pointer
            return None
        else:
            return ''.join([rs.chars[i] for i in range(len(rs.chars))])
    from_rstr = staticmethod(from_rstr)


class OOSupport:
    _mixin_ = True

    def to_rstr(s):
        return ootype.oostring(s, -1)
    to_rstr = staticmethod(to_rstr)
    
    def from_rstr(rs):
        if not rs:   # null pointer
            return None
        else:
            return "".join([rs.ll_stritem_nonneg(i) for i in range(rs.ll_strlen())])
    from_rstr = staticmethod(from_rstr)        


def ll_strcpy(dst_s, src_s, n):
    dstchars = dst_s.chars
    srcchars = src_s.chars
    i = 0
    while i < n:
        dstchars[i] = srcchars[i]
        i += 1

def _ll_strfill(dst_s, srcchars, n):
    dstchars = dst_s.chars
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

def to_opaque_object(value):
    "NOT_RPYTHON"
    exttypeinfo = extfunctable.typetable[value.__class__]
    return lltype.opaqueptr(exttypeinfo.get_lltype(), 'opaque',
                            externalobj=value)
to_opaque_object._annspecialcase_ = "override:to_opaque_object"
