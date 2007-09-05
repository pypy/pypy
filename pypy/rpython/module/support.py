from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype
from pypy.rpython import extfunctable
from pypy.rpython.lltypesystem.lltype import \
     GcStruct, Signed, Array, Char, Ptr, malloc, GcArray
from pypy.rpython.rlist import ll_append
from pypy.rpython.lltypesystem.rlist import ll_newlist, ListRepr,\
    ll_getitem_fast
from pypy.rpython.lltypesystem.rstr import string_repr
from pypy.rpython.lltypesystem.rdict import ll_newdict, DictRepr, dum_items,\
    ll_kvi, dum_keys, ll_dict_getitem, ll_dict_setitem
from pypy.rpython.lltypesystem.rstr import StringRepr
from pypy.rpython.lltypesystem.rtuple import TupleRepr
from pypy.annotation.dictdef import DictKey, DictValue
from pypy.annotation.model import SomeString
import os

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

    def from_rstr_nonnull(rs):
        assert rs
        return ''.join([rs.chars[i] for i in range(len(rs.chars))])
    from_rstr_nonnull = staticmethod(from_rstr_nonnull)

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

    def from_rstr_nonnull(rs):
        assert rs
        return "".join([rs.ll_stritem_nonneg(i) for i in range(rs.ll_strlen())])
    from_rstr_nonnull = staticmethod(from_rstr_nonnull)


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
