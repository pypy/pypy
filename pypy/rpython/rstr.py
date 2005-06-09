from weakref import WeakValueDictionary
from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.rpython.lltype import *
from pypy.rpython.rmodel import Repr, TyperError, IntegerRepr
from pypy.rpython.rmodel import StringRepr, CharRepr, inputconst
from pypy.rpython.rarithmetic import intmask

# ____________________________________________________________
#
#  Concrete implementation of RPython strings:
#
#    struct str {
#        hash: Signed
#        chars: array {
#            Char ch
#        }
#    }

STR = GcStruct('str', ('hash',  Signed),
                      ('chars', Array(('ch', Char))))


class __extend__(annmodel.SomeString):
    def rtyper_makerepr(self, rtyper):
        return string_repr
    def rtyper_makekey(self):
        return None

class __extend__(annmodel.SomeChar):
    def rtyper_makerepr(self, rtyper):
        return char_repr
    def rtyper_makekey(self):
        return None


CONST_STR_CACHE = WeakValueDictionary()

class __extend__(StringRepr):
    lowleveltype = Ptr(STR)

    def convert_const(self, value):
        if value is None:
            return nullptr(STR)
        if not isinstance(value, str):
            raise TyperError("not a str: %r" % (value,))
        try:
            return CONST_STR_CACHE[value]
        except KeyError:
            p = malloc(STR, len(value))
            for i in range(len(value)):
                p.chars[i].ch = value[i]
            ll_strhash(p)   # precompute the hash
            CONST_STR_CACHE[value] = p
            return p

    def rtype_len(_, hop):
        v_str, = hop.inputargs(string_repr)
        return hop.gendirectcall(ll_strlen, v_str)

    def rtype_is_true(self, hop):
        s_str = hop.args_s[0]
        if s_str.can_be_None:
            v_str, = hop.inputargs(string_repr)
            return hop.gendirectcall(ll_str_is_true, v_str)
        else:
            # defaults to checking the length
            return super(StringRepr, self).rtype_is_true(hop)

    def rtype_ord(_, hop):
        v_str, = hop.inputargs(string_repr)
        c_zero = inputconst(Signed, 0)
        v_chr = hop.gendirectcall(ll_stritem_nonneg, v_str, c_zero)
        return hop.genop('cast_char_to_int', [v_chr], resulttype=Signed)

    def rtype_hash(_, hop):
        v_str, = hop.inputargs(string_repr)
        return hop.gendirectcall(ll_strhash, v_str)


class __extend__(pairtype(StringRepr, IntegerRepr)):
    def rtype_getitem(_, hop):
        v_str, v_index = hop.inputargs(string_repr, Signed)
        if hop.args_s[1].nonneg:
            llfn = ll_stritem_nonneg
        else:
            llfn = ll_stritem
        return hop.gendirectcall(llfn, v_str, v_index)


class __extend__(pairtype(StringRepr, StringRepr)):
    def rtype_add(_, hop):
        v_str1, v_str2 = hop.inputargs(string_repr, string_repr)
        return hop.gendirectcall(ll_strconcat, v_str1, v_str2)

class __extend__(CharRepr):

    def rtype_len(_, hop):
        return hop.inputconst(Signed, 1)

    def rtype_is_true(_, hop):
        assert not hop.args_s[0].can_be_None
        return hop.inputconst(Bool, True)

    def rtype_ord(_, hop):
        vlist = hop.inputargs(char_repr)
        return hop.genop('cast_char_to_int', vlist, resulttype=Signed)


class __extend__(pairtype(CharRepr, StringRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        if r_from == char_repr and r_to == string_repr:
            return llops.gendirectcall(ll_chr2str, v)
        return NotImplemented

class __extend__(pairtype(StringRepr, CharRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        if r_from == string_repr and r_to == char_repr:
            c_zero = inputconst(Signed, 0)
            return llops.gendirectcall(ll_stritem_nonneg, v, c_zero)
        return NotImplemented


string_repr = StringRepr()
char_repr   = CharRepr()

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
        s.hash = intmask(x)
    return x

def ll_strconcat(s1, s2):
    len1 = len(s1.chars)
    len2 = len(s2.chars)
    newstr = malloc(STR, len1 + len2)
    j = 0
    while j < len1:
        newstr.chars[j].ch = s1.chars[j].ch
        j += 1
    i = 0
    while i < len2:
        newstr.chars[j].ch = s2.chars[i].ch
        i += 1
        j += 1
    return newstr

    
