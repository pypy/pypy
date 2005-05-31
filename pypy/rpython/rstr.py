from pypy.annotation.pairtype import pair, pairtype
from pypy.annotation.model import SomeString, SomeChar, SomeInteger, SomeObject
from pypy.rpython.lltype import *

# ____________________________________________________________
#
#  Concrete implementation of RPython strings:
#
#    struct str {
#        hash: Signed
#        chars: array {
#            item {
#                Char ch
#            }
#        }
#    }

STR = GcStruct('str', ('hash',  Signed),
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

    def rtype_ord(_, hop):
        v_str, = hop.inputargs(SomeString())
        c_zero = inputconst(Signed, 0)
        v_chr = hop.gendirectcall(ll_stritem_nonneg, v_str, c_zero)
        return hop.genop('cast_char_to_int', [v_chr], resulttype=Signed)

    def rtype_hash(_, hop):
        v_str, = hop.inputargs(SomeString())
        return hop.gendirectcall(ll_strhash, v_str)


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

    def rtype_ord(_, hop):
        vlist = hop.inputargs(Char)
        return hop.genop('cast_char_to_int', vlist, resulttype=Signed)


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

def ll_strhash(s):
    # unlike CPython, there is no reason to avoid to return -1
    # but our malloc initializes the memory to zero, so we use zero as the
    # special non-computed-yet value.
    x = s.hash
    if x == 0:
        length = len(s.chars)
        if length == 0:
            x = -1
        else:
            x = ord(s.chars[0].ch) << 7
            i = 1
            while i < length:
                x = (1000003*x) ^ ord(s.chars[i].ch)
                i += 1
            x ^= length
            if x == 0:
                x = -1
        s.hash = x
    return x
