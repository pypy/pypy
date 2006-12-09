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

# This whole mess is just to make annotator happy...
list_repr = ListRepr(None, string_repr)
list_repr.setup()
LIST = list_repr.lowleveltype.TO
tuple_repr = TupleRepr(None, [string_repr, string_repr])
tuple_repr.setup()
tuple_list_repr = ListRepr(None, tuple_repr)
tuple_list_repr.setup()
LIST_TUPLE = tuple_list_repr.lowleveltype.TO

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

def from_rdict(rs):
    ritems = ll_kvi(rs, LIST_TUPLE, dum_items)
    res = ll_newlist(LIST, 0)
    index = 0
    while index < ritems.ll_length():
        ritem = ll_getitem_fast(ritems, index)
        ll_append(res, LLSupport.to_rstr("%s=%s" % (LLSupport.from_rstr(ritem.item0),
            LLSupport.from_rstr(ritem.item1))))
        index += 1
    return res
    
def to_rdict(rs):
    d = {}
    index = 0
    while index < rs.ll_length():
        item = LLSupport.from_rstr(ll_getitem_fast(rs, index))
        key, value = item.split("=")
        d[key] = value
        index += 1
    return d

def ll_execve(cmd, args, env_list):
    env = to_rdict(env_list)
    os.execve(cmd, args, env)
ll_execve.suggested_primitive = True

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
