from pypy.annotation.pairtype import pair, pairtype
from pypy.annotation.model import SomeString, SomeChar, SomeInteger, SomeObject
from pypy.rpython.lltype import *

# ____________________________________________________________
#
#  Concrete implementation of RPython strings:
#
#    struct str {
#        hash: Unsigned
#        chars: array {
#            item {
#                Char ch
#            }
#        }
#    }

STR = GcStruct('str', ('hash',  Unsigned),
                      ('chars', Array(('ch', Char))))
STRPTR = GcPtr(STR)


class __extend__(SomeString):

    def lowleveltype(self):
        return STRPTR

    def rtype_len(_, hop):
        v_str, = hop.inputargs(SomeString())
        return hop.gendirectcall(ll_strlen, v_str)

    def rtype_is_true(s_str, hop):
        if s_str.can_be_None:
            v_str, = hop.inputargs(SomeString())
            return hop.gendirectcall(ll_str_is_true, v_str)
        else:
            # defaults to checking the length
            return SomeObject.rtype_is_true(s_str, hop)


class __extend__(pairtype(SomeString, SomeInteger)):

    def rtype_getitem((_, s_int), hop):
        v_str, v_index = hop.inputargs(SomeString(), Signed)
        if s_int.nonneg:
            llfn = ll_stritem_nonneg
        else:
            llfn = ll_stritem
        return hop.gendirectcall(llfn, v_str, v_index)


class __extend__(SomeChar):

    def lowleveltype(self):
        return Char

    def rtype_len(_, hop):
        return hop.inputconst(Signed, 1)

    def rtype_is_true(s_chr, hop):
        assert not s_chr.can_be_None
        return hop.inputconst(Bool, True)


class __extend__(pairtype(SomeChar, SomeString)):

    def rtype_convert_from_to((s_chr, s_str), v, llops):
        return hop.gendirectcall(ll_chr2str, v)


class __extend__(pairtype(SomeString, SomeString)):

    def rtype_convert_from_to((s_str1, s_str2), v, llops):
        # converting between SomeString(can_be_None=False)
        #                and SomeString(can_be_None=True)
        assert s_str1.__class__ is s_str2.__class__ is SomeString
        return v


# ____________________________________________________________
#
#  Low-level methods.  These can be run for testing, but are meant to
#  be direct_call'ed from rtyped flow graphs, which means that they will
#  get flowed and annotated, mostly with SomePtr.

def ll_strlen(s):
    return len(s.chars)

def ll_stritem_nonneg(s, i):
    return s.chars[i].ch

def ll_stritem(s, i):
    if i<0:
        i += len(s.chars)
    return s.chars[i].ch

def ll_str_is_true(s):
    # check if a string is True, allowing for None
    return bool(s) and len(s.chars) != 0

def ll_chr2str(ch):
    s = malloc(STR, 1)
    s.chars[0].ch = ch
    return s
