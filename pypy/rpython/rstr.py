from pypy.tool.staticmethods import StaticMethods
from pypy.tool.pairtype import pairtype, pair
from pypy.annotation import model as annmodel
from pypy.rpython.error import TyperError
from pypy.rpython.rmodel import IntegerRepr, IteratorRepr
from pypy.rpython.rmodel import inputconst, Repr
from pypy.rpython.rtuple import AbstractTupleRepr
from pypy.rpython import rint
from pypy.rpython.lltypesystem.lltype import Signed, Bool, Void, UniChar,\
     cast_primitive, typeOf

class AbstractStringRepr(Repr):
    pass

class AbstractCharRepr(AbstractStringRepr):
    pass

class AbstractUniCharRepr(AbstractStringRepr):
    pass

class AbstractUnicodeRepr(AbstractStringRepr):
    def rtype_method_upper(self, hop):
        raise TypeError("Cannot do toupper on unicode string")

    def rtype_method_lower(self, hop):
        raise TypeError("Cannot do tolower on unicode string")

class __extend__(annmodel.SomeString):
    def rtyper_makerepr(self, rtyper):
        return rtyper.type_system.rstr.string_repr
    def rtyper_makekey(self):
        return self.__class__,

class __extend__(annmodel.SomeUnicodeString):
    def rtyper_makerepr(self, rtyper):
        return rtyper.type_system.rstr.unicode_repr
    
    def rtyper_makekey(self):
        return self.__class__,

class __extend__(annmodel.SomeChar):
    def rtyper_makerepr(self, rtyper):
        return rtyper.type_system.rstr.char_repr
    def rtyper_makekey(self):
        return self.__class__,

class __extend__(annmodel.SomeUnicodeCodePoint):
    def rtyper_makerepr(self, rtyper):
        return rtyper.type_system.rstr.unichar_repr
    def rtyper_makekey(self):
        return self.__class__,


class __extend__(AbstractStringRepr):

    def _str_reprs(self, hop):
        return hop.args_r[0].repr, hop.args_r[1].repr

    def get_ll_eq_function(self):
        return self.ll.ll_streq

    def get_ll_hash_function(self):
        return self.ll.ll_strhash

    def get_ll_fasthash_function(self):
        return self.ll.ll_strfasthash

    def rtype_len(self, hop):
        string_repr = self.repr
        v_str, = hop.inputargs(string_repr)
        return hop.gendirectcall(self.ll.ll_strlen, v_str)

    def rtype_is_true(self, hop):
        s_str = hop.args_s[0]
        if s_str.can_be_None:
            string_repr = hop.args_r[0].repr
            v_str, = hop.inputargs(string_repr)
            return hop.gendirectcall(self.ll.ll_str_is_true, v_str)
        else:
            # defaults to checking the length
            return super(AbstractStringRepr, self).rtype_is_true(hop)

    def rtype_method_startswith(self, hop):
        str1_repr, str2_repr = self._str_reprs(hop)
        v_str, v_value = hop.inputargs(str1_repr, str2_repr)
        hop.exception_cannot_occur()
        return hop.gendirectcall(self.ll.ll_startswith, v_str, v_value)

    def rtype_method_endswith(self, hop):
        str1_repr, str2_repr = self._str_reprs(hop)
        v_str, v_value = hop.inputargs(str1_repr, str2_repr)
        hop.exception_cannot_occur()
        return hop.gendirectcall(self.ll.ll_endswith, v_str, v_value)

    def rtype_method_find(self, hop, reverse=False):
        # XXX binaryop
        string_repr = hop.args_r[0].repr
        char_repr = hop.args_r[0].char_repr
        v_str = hop.inputarg(string_repr, arg=0)
        if hop.args_r[1] == char_repr:
            v_value = hop.inputarg(char_repr, arg=1)
            llfn = reverse and self.ll.ll_rfind_char or self.ll.ll_find_char
        else:
            v_value = hop.inputarg(string_repr, arg=1)
            llfn = reverse and self.ll.ll_rfind or self.ll.ll_find
        if hop.nb_args > 2:
            v_start = hop.inputarg(Signed, arg=2)
            if not hop.args_s[2].nonneg:
                raise TyperError("str.find() start must be proven non-negative")
        else:
            v_start = hop.inputconst(Signed, 0)
        if hop.nb_args > 3:
            v_end = hop.inputarg(Signed, arg=3)
            if not hop.args_s[3].nonneg:
                raise TyperError("str.find() end must be proven non-negative")
        else:
            v_end = hop.gendirectcall(self.ll.ll_strlen, v_str)
        hop.exception_cannot_occur()
        return hop.gendirectcall(llfn, v_str, v_value, v_start, v_end)

    def rtype_method_rfind(self, hop):
        return self.rtype_method_find(hop, reverse=True)

    def rtype_method_count(self, hop):
        rstr = hop.args_r[0].repr
        v_str = hop.inputarg(rstr.repr, arg=0)
        if hop.args_r[1] == rstr.char_repr:
            v_value = hop.inputarg(rstr.char_repr, arg=1)
            llfn = self.ll.ll_count_char
        else:
            v_value = hop.inputarg(rstr.repr, arg=1)
            llfn = self.ll.ll_count
        if hop.nb_args > 2:
            v_start = hop.inputarg(Signed, arg=2)
            if not hop.args_s[2].nonneg:
                raise TyperError("str.count() start must be proven non-negative")
        else:
            v_start = hop.inputconst(Signed, 0)
        if hop.nb_args > 3:
            v_end = hop.inputarg(Signed, arg=3)
            if not hop.args_s[3].nonneg:
                raise TyperError("str.count() end must be proven non-negative")
        else:
            v_end = hop.gendirectcall(self.ll.ll_strlen, v_str)
        hop.exception_cannot_occur()
        return hop.gendirectcall(llfn, v_str, v_value, v_start, v_end)

    def rtype_method_strip(self, hop, left=True, right=True):
        rstr = hop.args_r[0].repr
        v_str = hop.inputarg(rstr.repr, arg=0)
        v_char = hop.inputarg(rstr.char_repr, arg=1)
        v_left = hop.inputconst(Bool, left)
        v_right = hop.inputconst(Bool, right)
        return hop.gendirectcall(self.ll.ll_strip, v_str, v_char, v_left, v_right)

    def rtype_method_lstrip(self, hop):
        return self.rtype_method_strip(hop, left=True, right=False)

    def rtype_method_rstrip(self, hop):
        return self.rtype_method_strip(hop, left=False, right=True)

    def rtype_method_upper(self, hop):
        string_repr = hop.args_r[0].repr
        v_str, = hop.inputargs(string_repr)
        hop.exception_cannot_occur()
        return hop.gendirectcall(self.ll.ll_upper, v_str)
        
    def rtype_method_lower(self, hop):
        string_repr = hop.args_r[0].repr
        v_str, = hop.inputargs(string_repr)
        hop.exception_cannot_occur()
        return hop.gendirectcall(self.ll.ll_lower, v_str)

    def _list_length_items(self, hop, v_lst, LIST):
        """Return two Variables containing the length and items of a
        list. Need to be overriden because it is typesystem-specific."""
        raise NotImplementedError

    def rtype_method_join(self, hop):
        hop.exception_cannot_occur()
        rstr = hop.args_r[0]
        if hop.s_result.is_constant():
            return inputconst(rstr.repr, hop.s_result.const)
        r_lst = hop.args_r[1]
        if not isinstance(r_lst, hop.rtyper.type_system.rlist.BaseListRepr):
            raise TyperError("string.join of non-list: %r" % r_lst)
        v_str, v_lst = hop.inputargs(rstr.repr, r_lst)
        v_length, v_items = self._list_length_items(hop, v_lst, r_lst.lowleveltype)

        if hop.args_s[0].is_constant() and hop.args_s[0].const == '':
            if r_lst.item_repr == rstr.repr:
                llfn = self.ll.ll_join_strs
            elif (r_lst.item_repr == hop.rtyper.type_system.rstr.char_repr or
                  r_lst.item_repr == hop.rtyper.type_system.rstr.unichar_repr):
                v_tp = hop.inputconst(Void, self.lowleveltype)
                return hop.gendirectcall(self.ll.ll_join_chars, v_length,
                                         v_items, v_tp)
            else:
                raise TyperError("''.join() of non-string list: %r" % r_lst)
            return hop.gendirectcall(llfn, v_length, v_items)
        else:
            if r_lst.item_repr == rstr.repr:
                llfn = self.ll.ll_join
            else:
                raise TyperError("sep.join() of non-string list: %r" % r_lst)
            return hop.gendirectcall(llfn, v_str, v_length, v_items)

    def rtype_method_splitlines(self, hop):
        rstr = hop.args_r[0].repr
        if hop.nb_args == 2:
            args = hop.inputargs(rstr.repr, Bool)
        else:
            args = [hop.inputarg(rstr.repr, 0), hop.inputconst(Bool, False)]
        try:
            list_type = hop.r_result.lowleveltype.TO
        except AttributeError:
            list_type = hop.r_result.lowleveltype
        cLIST = hop.inputconst(Void, list_type)
        hop.exception_cannot_occur()
        return hop.gendirectcall(self.ll.ll_splitlines, cLIST, *args)

    def rtype_method_split(self, hop):
        rstr = hop.args_r[0].repr
        if hop.nb_args == 3:
            v_str, v_chr, v_max = hop.inputargs(rstr.repr, rstr.char_repr, Signed)
        else:
            v_str, v_chr = hop.inputargs(rstr.repr, rstr.char_repr)
            v_max = hop.inputconst(Signed, -1)
        try:
            list_type = hop.r_result.lowleveltype.TO
        except AttributeError:
            list_type = hop.r_result.lowleveltype
        cLIST = hop.inputconst(Void, list_type)
        hop.exception_cannot_occur()
        return hop.gendirectcall(self.ll.ll_split_chr, cLIST, v_str, v_chr, v_max)

    def rtype_method_rsplit(self, hop):
        rstr = hop.args_r[0].repr
        if hop.nb_args == 3:
            v_str, v_chr, v_max = hop.inputargs(rstr.repr, rstr.char_repr, Signed)
        else:
            v_str, v_chr = hop.inputargs(rstr.repr, rstr.char_repr)
            v_max = hop.inputconst(Signed, -1)
        try:
            list_type = hop.r_result.lowleveltype.TO
        except AttributeError:
            list_type = hop.r_result.lowleveltype
        cLIST = hop.inputconst(Void, list_type)
        hop.exception_cannot_occur()
        return hop.gendirectcall(self.ll.ll_rsplit_chr, cLIST, v_str, v_chr, v_max)

    def rtype_method_replace(self, hop):
        rstr = hop.args_r[0].repr
        if not (hop.args_r[1] == rstr.char_repr and hop.args_r[2] == rstr.char_repr):
            raise TyperError, 'replace only works for char args'
        v_str, v_c1, v_c2 = hop.inputargs(rstr.repr, rstr.char_repr, rstr.char_repr)
        hop.exception_cannot_occur()
        return hop.gendirectcall(self.ll.ll_replace_chr_chr, v_str, v_c1, v_c2)

    def rtype_int(self, hop):
        hop.has_implicit_exception(ValueError)   # record that we know about it
        string_repr = hop.args_r[0].repr
        if hop.nb_args == 1:
            v_str, = hop.inputargs(string_repr)
            c_base = inputconst(Signed, 10)
            hop.exception_is_here()
            return hop.gendirectcall(self.ll.ll_int, v_str, c_base)
        if not hop.args_r[1] == rint.signed_repr:
            raise TyperError, 'base needs to be an int'
        v_str, v_base= hop.inputargs(string_repr, rint.signed_repr)
        hop.exception_is_here()
        return hop.gendirectcall(self.ll.ll_int, v_str, v_base)

    def rtype_unicode(self, hop):
        if hop.args_s[0].is_constant():
            return hop.inputconst(hop.r_result, hop.s_result.const)
        repr = hop.args_r[0].repr
        v_str = hop.inputarg(repr, 0)
        if repr == hop.r_result: # the argument is a unicode string already
            hop.exception_cannot_occur()
            return v_str
        hop.exception_is_here()
        return hop.gendirectcall(self.ll.ll_str2unicode, v_str)

    def rtype_method_decode(self, hop):
        if not hop.args_s[1].is_constant():
            raise TyperError("encoding must be a constant")
        encoding = hop.args_s[1].const
        v_self = hop.inputarg(self.repr, 0)
        hop.exception_is_here()
        if encoding == 'ascii':
            return hop.gendirectcall(self.ll.ll_str2unicode, v_self)
        elif encoding == 'latin-1':
            return hop.gendirectcall(self.ll_decode_latin1, v_self)
        else:
            raise TyperError("encoding %s not implemented" % (encoding, ))

    def rtype_float(self, hop):
        hop.has_implicit_exception(ValueError)   # record that we know about it
        string_repr = hop.args_r[0].repr
        v_str, = hop.inputargs(string_repr)
        hop.exception_is_here()
        return hop.gendirectcall(self.ll.ll_float, v_str)

    def ll_str(self, s):
        if s:
            return s
        else:
            return self.ll.ll_constant('None')

class __extend__(AbstractUnicodeRepr):
    def rtype_method_encode(self, hop):
        if not hop.args_s[1].is_constant():
            raise TyperError("encoding must be constant")
        encoding = hop.args_s[1].const
        if encoding == "ascii" and self.lowleveltype == UniChar:
            expect = UniChar             # only for unichar.encode('ascii')
        else:
            expect = self.repr           # must be a regular unicode string
        v_self = hop.inputarg(expect, 0)
        hop.exception_is_here()
        if encoding == "ascii":
            return hop.gendirectcall(self.ll_str, v_self)
        elif encoding == "latin-1":
            return hop.gendirectcall(self.ll_encode_latin1, v_self)
        else:
            raise TyperError("encoding %s not implemented" % (encoding, ))


class __extend__(pairtype(AbstractStringRepr, Repr)):
    def rtype_mod((r_str, _), hop):
        # for the case where the 2nd argument is a tuple, see the
        # overriding rtype_mod() below
        return r_str.ll.do_stringformat(hop, [(hop.args_v[1], hop.args_r[1])])


class __extend__(pairtype(AbstractStringRepr, IntegerRepr)):
    def rtype_getitem((r_str, r_int), hop, checkidx=False):
        string_repr = r_str.repr
        v_str, v_index = hop.inputargs(string_repr, Signed)
        if checkidx:
            if hop.args_s[1].nonneg:
                llfn = r_str.ll.ll_stritem_nonneg_checked
            else:
                llfn = r_str.ll.ll_stritem_checked
        else:
            if hop.args_s[1].nonneg:
                llfn = r_str.ll.ll_stritem_nonneg
            else:
                llfn = r_str.ll.ll_stritem
        if checkidx:
            hop.exception_is_here()
        else:
            hop.exception_cannot_occur()
        return hop.gendirectcall(llfn, v_str, v_index)

    rtype_getitem_key = rtype_getitem

    def rtype_getitem_idx((r_str, r_int), hop):
        return pair(r_str, r_int).rtype_getitem(hop, checkidx=True)

    rtype_getitem_idx_key = rtype_getitem_idx


class __extend__(AbstractStringRepr):

    def rtype_getslice(r_str, hop):
        string_repr = r_str.repr
        v_str = hop.inputarg(string_repr, arg=0)
        kind, vlist = hop.decompose_slice_args()
        ll_fn = getattr(r_str.ll, 'll_stringslice_%s' % (kind,))
        return hop.gendirectcall(ll_fn, v_str, *vlist)

class __extend__(pairtype(AbstractStringRepr, AbstractStringRepr)):
    def rtype_add((r_str1, r_str2), hop):
        str1_repr = r_str1.repr
        str2_repr = r_str2.repr
        if hop.s_result.is_constant():
            return hop.inputconst(str1_repr, hop.s_result.const)
        v_str1, v_str2 = hop.inputargs(str1_repr, str2_repr)
        return hop.gendirectcall(r_str1.ll.ll_strconcat, v_str1, v_str2)
    rtype_inplace_add = rtype_add

    def rtype_eq((r_str1, r_str2), hop):
        v_str1, v_str2 = hop.inputargs(r_str1.repr, r_str2.repr)
        return hop.gendirectcall(r_str1.ll.ll_streq, v_str1, v_str2)
    
    def rtype_ne((r_str1, r_str2), hop):
        v_str1, v_str2 = hop.inputargs(r_str1.repr, r_str2.repr)
        vres = hop.gendirectcall(r_str1.ll.ll_streq, v_str1, v_str2)
        return hop.genop('bool_not', [vres], resulttype=Bool)

    def rtype_lt((r_str1, r_str2), hop):
        v_str1, v_str2 = hop.inputargs(r_str1.repr, r_str2.repr)
        vres = hop.gendirectcall(r_str1.ll.ll_strcmp, v_str1, v_str2)
        return hop.genop('int_lt', [vres, hop.inputconst(Signed, 0)],
                         resulttype=Bool)

    def rtype_le((r_str1, r_str2), hop):
        v_str1, v_str2 = hop.inputargs(r_str1.repr, r_str2.repr)
        vres = hop.gendirectcall(r_str1.ll.ll_strcmp, v_str1, v_str2)
        return hop.genop('int_le', [vres, hop.inputconst(Signed, 0)],
                         resulttype=Bool)

    def rtype_ge((r_str1, r_str2), hop):
        v_str1, v_str2 = hop.inputargs(r_str1.repr, r_str2.repr)
        vres = hop.gendirectcall(r_str1.ll.ll_strcmp, v_str1, v_str2)
        return hop.genop('int_ge', [vres, hop.inputconst(Signed, 0)],
                         resulttype=Bool)

    def rtype_gt((r_str1, r_str2), hop):
        v_str1, v_str2 = hop.inputargs(r_str1.repr, r_str2.repr)
        vres = hop.gendirectcall(r_str1.ll.ll_strcmp, v_str1, v_str2)
        return hop.genop('int_gt', [vres, hop.inputconst(Signed, 0)],
                         resulttype=Bool)

    def rtype_contains((r_str1, r_str2), hop):
        v_str1, v_str2 = hop.inputargs(r_str1.repr, r_str2.repr)
        v_end = hop.gendirectcall(r_str1.ll.ll_strlen, v_str1)
        vres = hop.gendirectcall(r_str1.ll.ll_find, v_str1, v_str2,
                                 hop.inputconst(Signed, 0), v_end)
        hop.exception_cannot_occur()
        return hop.genop('int_ne', [vres, hop.inputconst(Signed, -1)],
                         resulttype=Bool)


class __extend__(pairtype(AbstractStringRepr, AbstractCharRepr),
                 pairtype(AbstractUnicodeRepr, AbstractUniCharRepr)):
    def rtype_contains((r_str, r_chr), hop):
        string_repr = r_str.repr
        char_repr = r_chr.char_repr
        v_str, v_chr = hop.inputargs(string_repr, char_repr)
        hop.exception_cannot_occur()
        return hop.gendirectcall(r_str.ll.ll_contains, v_str, v_chr)

class __extend__(pairtype(AbstractStringRepr, AbstractTupleRepr)):
    def rtype_mod((r_str, r_tuple), hop):
        r_tuple = hop.args_r[1]
        v_tuple = hop.args_v[1]

        sourcevars = []
        for i, r_arg in enumerate(r_tuple.external_items_r):
            v_item = r_tuple.getitem(hop.llops, v_tuple, i)
            sourcevars.append((v_item, r_arg))

        return r_str.ll.do_stringformat(hop, sourcevars)


class __extend__(AbstractCharRepr):
    def ll_str(self, ch):
        return self.ll.ll_chr2str(ch)

class __extend__(AbstractUniCharRepr):
    def ll_str(self, ch):
        # xxx suboptimal, maybe
        return str(unicode(ch))


class __extend__(AbstractCharRepr,
                 AbstractUniCharRepr):

    def convert_const(self, value):
        if not isinstance(value, str) or len(value) != 1:
            raise TyperError("not a character: %r" % (value,))
        return value

    def get_ll_eq_function(self):
        return None 

    def get_ll_hash_function(self):
        return self.ll.ll_char_hash

    get_ll_fasthash_function = get_ll_hash_function

    def rtype_len(_, hop):
        return hop.inputconst(Signed, 1)

    def rtype_is_true(_, hop):
        assert not hop.args_s[0].can_be_None
        return hop.inputconst(Bool, True)

    def rtype_ord(_, hop):
        repr = hop.args_r[0].char_repr
        vlist = hop.inputargs(repr)
        return hop.genop('cast_char_to_int', vlist, resulttype=Signed)

    def _rtype_method_isxxx(_, llfn, hop):
        repr = hop.args_r[0].char_repr
        vlist = hop.inputargs(repr)
        hop.exception_cannot_occur()
        return hop.gendirectcall(llfn, vlist[0])

    def rtype_method_isspace(self, hop):
        return self._rtype_method_isxxx(self.ll.ll_char_isspace, hop)
    def rtype_method_isdigit(self, hop):
        return self._rtype_method_isxxx(self.ll.ll_char_isdigit, hop)
    def rtype_method_isalpha(self, hop):
        return self._rtype_method_isxxx(self.ll.ll_char_isalpha, hop)
    def rtype_method_isalnum(self, hop):
        return self._rtype_method_isxxx(self.ll.ll_char_isalnum, hop)
    def rtype_method_isupper(self, hop):
        return self._rtype_method_isxxx(self.ll.ll_char_isupper, hop)
    def rtype_method_islower(self, hop):
        return self._rtype_method_isxxx(self.ll.ll_char_islower, hop)

class __extend__(pairtype(AbstractCharRepr, IntegerRepr),
                 pairtype(AbstractUniCharRepr, IntegerRepr)):
    
    def rtype_mul((r_chr, r_int), hop):
        char_repr = r_chr.char_repr
        v_char, v_int = hop.inputargs(char_repr, Signed)
        return hop.gendirectcall(r_chr.ll.ll_char_mul, v_char, v_int)
    rtype_inplace_mul = rtype_mul

class __extend__(pairtype(IntegerRepr, AbstractCharRepr),
                 pairtype(IntegerRepr, AbstractUniCharRepr)):
    def rtype_mul((r_int, r_chr), hop):
        char_repr = r_chr.char_repr
        v_int, v_char = hop.inputargs(Signed, char_repr)
        return hop.gendirectcall(r_chr.ll.ll_char_mul, v_char, v_int)
    rtype_inplace_mul = rtype_mul

class __extend__(pairtype(AbstractCharRepr, AbstractCharRepr)):
    def rtype_eq(_, hop): return _rtype_compare_template(hop, 'eq')
    def rtype_ne(_, hop): return _rtype_compare_template(hop, 'ne')
    def rtype_lt(_, hop): return _rtype_compare_template(hop, 'lt')
    def rtype_le(_, hop): return _rtype_compare_template(hop, 'le')
    def rtype_gt(_, hop): return _rtype_compare_template(hop, 'gt')
    def rtype_ge(_, hop): return _rtype_compare_template(hop, 'ge')

#Helper functions for comparisons

def _rtype_compare_template(hop, func):
    rstr = hop.rtyper.type_system.rstr
    vlist = hop.inputargs(rstr.char_repr, rstr.char_repr)
    return hop.genop('char_'+func, vlist, resulttype=Bool)

class __extend__(AbstractUniCharRepr):

    def convert_const(self, value):
        if isinstance(value, str):
            value = unicode(value)
        if not isinstance(value, unicode) or len(value) != 1:
            raise TyperError("not a unicode character: %r" % (value,))
        return value

    def get_ll_eq_function(self):
        return None 

    def get_ll_hash_function(self):
        return self.ll.ll_unichar_hash

    get_ll_fasthash_function = get_ll_hash_function

##    def rtype_len(_, hop):
##        return hop.inputconst(Signed, 1)
##
##    def rtype_is_true(_, hop):
##        assert not hop.args_s[0].can_be_None
##        return hop.inputconst(Bool, True)

    def rtype_ord(_, hop):
        rstr = hop.rtyper.type_system.rstr
        vlist = hop.inputargs(rstr.unichar_repr)
        return hop.genop('cast_unichar_to_int', vlist, resulttype=Signed)


class __extend__(pairtype(AbstractUniCharRepr, AbstractUniCharRepr),
                 pairtype(AbstractCharRepr, AbstractUniCharRepr),
                 pairtype(AbstractUniCharRepr, AbstractCharRepr)):
    def rtype_eq(_, hop): return _rtype_unchr_compare_template(hop, 'eq')
    def rtype_ne(_, hop): return _rtype_unchr_compare_template(hop, 'ne')
##    def rtype_lt(_, hop): return _rtype_unchr_compare_template(hop, 'lt')
##    def rtype_le(_, hop): return _rtype_unchr_compare_template(hop, 'le')
##    def rtype_gt(_, hop): return _rtype_unchr_compare_template(hop, 'gt')
##    def rtype_ge(_, hop): return _rtype_unchr_compare_template(hop, 'ge')

#Helper functions for comparisons

def _rtype_unchr_compare_template(hop, func):
    rstr = hop.rtyper.type_system.rstr
    vlist = hop.inputargs(rstr.unichar_repr, rstr.unichar_repr)
    return hop.genop('unichar_'+func, vlist, resulttype=Bool)


#
# _________________________ Conversions _________________________

class __extend__(pairtype(AbstractCharRepr, AbstractStringRepr),
                 pairtype(AbstractUniCharRepr, AbstractUnicodeRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        rstr = llops.rtyper.type_system.rstr
        if (r_from == rstr.char_repr and r_to == rstr.string_repr) or\
           (r_from == rstr.unichar_repr and r_to == rstr.unicode_repr):
            return llops.gendirectcall(r_from.ll.ll_chr2str, v)
        return NotImplemented

class __extend__(pairtype(AbstractStringRepr, AbstractCharRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        rstr = llops.rtyper.type_system.rstr
        if r_from == rstr.string_repr and r_to == rstr.char_repr:
            c_zero = inputconst(Signed, 0)
            return llops.gendirectcall(r_from.ll.ll_stritem_nonneg, v, c_zero)
        return NotImplemented

class __extend__(pairtype(AbstractCharRepr, AbstractUniCharRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        v2 = llops.genop('cast_char_to_int', [v], resulttype=Signed)
        return llops.genop('cast_int_to_unichar', [v2], resulttype=UniChar)

# ____________________________________________________________
#
#  Iteration.

class AbstractStringIteratorRepr(IteratorRepr):

    def newiter(self, hop):
        string_repr = hop.args_r[0].repr
        v_str, = hop.inputargs(string_repr)
        return hop.gendirectcall(self.ll_striter, v_str)

    def rtype_next(self, hop):
        v_iter, = hop.inputargs(self)
        hop.has_implicit_exception(StopIteration) # record that we know about it
        hop.exception_is_here()
        return hop.gendirectcall(self.ll_strnext, v_iter)


# ____________________________________________________________
#
#  Low-level methods.  These can be run for testing, but are meant to
#  be direct_call'ed from rtyped flow graphs, which means that they will
#  get flowed and annotated, mostly with SomePtr.
#

# this class contains low level helpers used both by lltypesystem and
# ootypesystem; each typesystem should subclass it and add its own
# primitives.
class AbstractLLHelpers:
    __metaclass__ = StaticMethods

    def ll_char_isspace(ch):
        c = ord(ch)
        return c == 32 or (9 <= c <= 13)   # c in (9, 10, 11, 12, 13, 32)

    def ll_char_isdigit(ch):
        c = ord(ch)
        return c <= 57 and c >= 48

    def ll_char_isalpha(ch):
        c = ord(ch)
        if c >= 97:
            return c <= 122
        else:
            return 65 <= c <= 90

    def ll_char_isalnum(ch):
        c = ord(ch)
        if c >= 65:
            if c >= 97:
                return c <= 122
            else:
                return c <= 90
        else:
            return 48 <= c <= 57

    def ll_char_isupper(ch):
        c = ord(ch)
        return 65 <= c <= 90

    def ll_char_islower(ch):
        c = ord(ch)
        return 97 <= c <= 122

    def ll_char_hash(ch):
        return ord(ch)

    def ll_unichar_hash(ch):
        return ord(ch)

    def ll_str_is_true(cls, s):
        # check if a string is True, allowing for None
        return bool(s) and cls.ll_strlen(s) != 0
    ll_str_is_true = classmethod(ll_str_is_true)

    def ll_stritem_nonneg_checked(cls, s, i):
        if i >= cls.ll_strlen(s):
            raise IndexError
        return cls.ll_stritem_nonneg(s, i)
    ll_stritem_nonneg_checked = classmethod(ll_stritem_nonneg_checked)

    def ll_stritem(cls, s, i):
        if i < 0:
            i += cls.ll_strlen(s)
        return cls.ll_stritem_nonneg(s, i)
    ll_stritem = classmethod(ll_stritem)

    def ll_stritem_checked(cls, s, i):
        length = cls.ll_strlen(s)
        if i < 0:
            i += length
        if i >= length or i < 0:
            raise IndexError
        return cls.ll_stritem_nonneg(s, i)
    ll_stritem_checked = classmethod(ll_stritem_checked)

    def parse_fmt_string(fmt):
        # we support x, d, s, f, [r]
        it = iter(fmt)
        r = []
        curstr = ''
        for c in it:
            if c == '%':
                f = it.next()
                if f == '%':
                    curstr += '%'
                    continue

                if curstr:
                    r.append(curstr)
                curstr = ''
                if f not in 'xdosrf':
                    raise TyperError("Unsupported formatting specifier: %r in %r" % (f, fmt))

                r.append((f,))
            else:
                curstr += c
        if curstr:
            r.append(curstr)
        return r

    def ll_float(ll_str):
        from pypy.rpython.annlowlevel import hlstr
        from pypy.rlib.rfloat import rstring_to_float
        s = hlstr(ll_str)
        assert s is not None

        n = len(s)
        beg = 0
        while beg < n:
            if s[beg] == ' ':
                beg += 1
            else:
                break
        if beg == n:
            raise ValueError
        end = n-1
        while end >= 0:
            if s[end] == ' ':
                end -= 1
            else:
                break
        assert end >= 0
        return rstring_to_float(s[beg:end+1])

    def ll_splitlines(cls, LIST, ll_str, keep_newlines):
        from pypy.rpython.annlowlevel import hlstr
        s = hlstr(ll_str)
        STR = typeOf(ll_str)
        strlen = len(s)
        i = 0
        j = 0
        # The annotator makes sure this list is resizable.
        res = LIST.ll_newlist(0)
        while j < strlen:
            while i < strlen and s[i] != '\n' and s[i] != '\r':
                i += 1
            eol = i
            if i < strlen:
                if s[i] == '\r' and i + 1 < strlen and s[i + 1] == '\n':
                    i += 2
                else:
                    i += 1
                if keep_newlines:
                    eol = i
            list_length = res.ll_length()
            res._ll_resize_ge(list_length + 1)
            item = cls.ll_stringslice_startstop(ll_str, j, eol)
            res.ll_setitem_fast(list_length, item)
            j = i
        if j < strlen:
            list_length = res.ll_length()
            res._ll_resize_ge(list_length + 1)
            item = cls.ll_stringslice_startstop(ll_str, j, strlen)
            res.ll_setitem_fast(list_length, item)
        return res
    ll_splitlines = classmethod(ll_splitlines)
