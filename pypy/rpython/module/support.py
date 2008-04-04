from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype
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

    def to_runicode(s):
        from pypy.rpython.lltypesystem.rstr import UNICODE, mallocunicode
        if s is None:
            return lltype.nullptr(UNICODE)
        p = mallocunicode(len(s))
        for i in range(len(s)):
            p.chars[i] = s[i]
        return p
    to_runicode = staticmethod(to_runicode)    

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
        if s is None:
            return ootype.null(ootype.String)
        return ootype.oostring(s, -1)
    to_rstr = staticmethod(to_rstr)

    def to_runicode(u):
        return ootype.oounicode(u, -1)
    to_runicode = staticmethod(to_runicode)
    
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


