"""The builtin unicode implementation"""

from rpython.rlib.objectmodel import (
    compute_hash, compute_unique_id, import_from_mixin,
    enforceargs, newlist_hint, specialize, we_are_translated)
from rpython.rlib.buffer import StringBuffer
from rpython.rlib.rstring import StringBuilder, split, rsplit, UnicodeBuilder,\
     replace
from rpython.rlib.runicode import make_unicode_escape_function
from rpython.rlib import rutf8, jit

from pypy.interpreter import unicodehelper
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import WrappedDefault, interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef
from pypy.module.unicodedata import unicodedb
from pypy.objspace.std import newformat
from pypy.objspace.std.basestringtype import basestring_typedef
from pypy.objspace.std.formatting import mod_format
from pypy.objspace.std.stringmethods import StringMethods
from pypy.objspace.std.util import IDTAG_SPECIAL, IDTAG_SHIFT
from pypy.objspace.std.sliceobject import unwrap_start_stop

__all__ = ['W_UnicodeObject', 'wrapunicode', 'plain_str2unicode',
           'encode_object', 'decode_object', 'unicode_from_object',
           'unicode_from_string', 'unicode_to_decimal_w']


class W_UnicodeObject(W_Root):
    import_from_mixin(StringMethods)
    _immutable_fields_ = ['_utf8']

    @enforceargs(utf8str=str)
    def __init__(self, utf8str, length, ucs4str=None):
        assert isinstance(utf8str, str)
        if ucs4str is not None:
            assert isinstance(ucs4str, unicode)
        self._utf8 = utf8str
        self._length = length
        self._ucs4 = ucs4str
        if not we_are_translated() and length != -1:
            assert rutf8.compute_length_utf8(utf8str) == length

    def __repr__(self):
        """representation for debugging purposes"""
        return "%s(%r)" % (self.__class__.__name__, self._utf8)

    def is_w(self, space, w_other):
        if not isinstance(w_other, W_UnicodeObject):
            return False
        if self is w_other:
            return True
        if self.user_overridden_class or w_other.user_overridden_class:
            return False
        s1 = space.utf8_w(self)
        s2 = space.utf8_w(w_other)
        if len(s2) > 2:
            return s1 is s2
        else:            # strings of len <= 1 are unique-ified
            return s1 == s2

    def immutable_unique_id(self, space):
        if self.user_overridden_class:
            return None
        s = space.utf8_w(self)
        if len(s) > 2:
            uid = compute_unique_id(s)
        else:            # strings of len <= 1 are unique-ified
            if len(s) == 1:
                base = ~ord(s[0])      # negative base values
            elif len(s) == 2:
                base = ~((ord(s[1]) << 8) | ord(s[0]))
            else:
                base = 257       # empty unicode string: base value 257
            uid = (base << IDTAG_SHIFT) | IDTAG_SPECIAL
        return space.newint(uid)

    def _convert_idx_params_unicode(self, space, w_start, w_end):
        """ Specialcase this for unicode - one less element in the tuple
        """
        lenself = self._len()
        start, end = unwrap_start_stop(space, lenself, w_start, w_end)
        return start, end

    def str_w(self, space):
        return space.text_w(space.str(self))

    def utf8_w(self, space):
        return self._utf8

    def readbuf_w(self, space):
        # XXX for now
        from rpython.rlib.rstruct.unichar import pack_unichar, UNICODE_SIZE
        v = self._utf8.decode("utf8")
        builder = StringBuilder(len(v) * UNICODE_SIZE)
        for unich in v:
            pack_unichar(unich, builder)
        return StringBuffer(builder.build())

    def writebuf_w(self, space):
        raise oefmt(space.w_TypeError,
                    "cannot use unicode as modifiable buffer")

    charbuf_w = str_w

    def listview_unicode(self):
        XXX # fix at some point
        return _create_list_from_unicode(self._value)

    def ord(self, space):
        if self._len() != 1:
            raise oefmt(space.w_TypeError,
                         "ord() expected a character, but string of length %d "
                         "found", self._len())
        return space.newint(rutf8.codepoint_at_pos(self._utf8, 0))

    def _new(self, value):
        return W_UnicodeObject(value.encode('utf8'), len(value))

    def _new_from_list(self, value):
        u = u''.join(value)
        return W_UnicodeObject(u.encode('utf8'), len(u))
    def _empty(self):
        return W_UnicodeObject.EMPTY

    def _len(self):
        if self._length == -1:
            self._length = self._compute_length()
        return self._length

    def _compute_length(self):
        return rutf8.compute_length_utf8(self._utf8)

    def _val(self, space):
        import pdb
        pdb.set_trace()
        return self._utf8.decode('utf8')

    @staticmethod
    def _use_rstr_ops(space, w_other):
        # Always return true because we always need to copy the other
        # operand(s) before we can do comparisons
        return True

    @staticmethod
    def _op_val(space, w_other, strict=None):
        return W_UnicodeObject.convert_arg_to_w_unicode(space, w_other, strict)._utf8.decode('utf8')

    @staticmethod
    def convert_arg_to_w_unicode(space, w_other, strict=None):
        if isinstance(w_other, W_UnicodeObject):
            return w_other
        if space.isinstance_w(w_other, space.w_bytes):
            return unicode_from_string(space, w_other)
        if strict:
            raise oefmt(space.w_TypeError,
                "%s arg must be None, unicode or str", strict)
        return unicode_from_encoded_object(space, w_other, None, "strict")

    def convert_to_w_unicode(self, space):
        return self

    @specialize.argtype(1)
    def _chr(self, char):
        assert len(char) == 1
        return unichr(ord(char[0]))

    def _multi_chr(self, unichar):
        return unichar

    _builder = UnicodeBuilder

    def _isupper(self, ch):
        return unicodedb.isupper(ord(ch))

    def _islower(self, ch):
        return unicodedb.islower(ord(ch))

    def _isnumeric(self, ch):
        return unicodedb.isnumeric(ord(ch))

    def _istitle(self, ch):
        return unicodedb.isupper(ord(ch)) or unicodedb.istitle(ord(ch))

    def _isspace(self, ch):
        return unicodedb.isspace(ord(ch))

    def _isalpha(self, ch):
        return unicodedb.isalpha(ord(ch))

    def _isalnum(self, ch):
        return unicodedb.isalnum(ord(ch))

    def _isdigit(self, ch):
        return unicodedb.isdigit(ord(ch))

    def _isdecimal(self, ch):
        return unicodedb.isdecimal(ord(ch))

    def _iscased(self, ch):
        return unicodedb.iscased(ord(ch))

    def _islinebreak(self, s, pos):
        return rutf8.islinebreak(s, pos)

    def _upper(self, ch):
        return unichr(unicodedb.toupper(ord(ch)))

    def _lower(self, ch):
        return unichr(unicodedb.tolower(ord(ch)))

    def _title(self, ch):
        return unichr(unicodedb.totitle(ord(ch)))

    def _newlist_unwrapped(self, space, lst):
        assert False, "should not be called"
        return space.newlist_unicode(lst)

    @staticmethod
    @unwrap_spec(w_string=WrappedDefault(""))
    def descr_new(space, w_unicodetype, w_string, w_encoding=None,
                  w_errors=None):
        # NB. the default value of w_obj is really a *wrapped* empty string:
        #     there is gateway magic at work
        w_obj = w_string

        encoding, errors = _get_encoding_and_errors(space, w_encoding,
                                                    w_errors)
        # convoluted logic for the case when unicode subclass has a __unicode__
        # method, we need to call this method
        is_precisely_unicode = space.is_w(space.type(w_obj), space.w_unicode)
        if (is_precisely_unicode or
            (space.isinstance_w(w_obj, space.w_unicode) and
             space.findattr(w_obj, space.newtext('__unicode__')) is None)):
            if encoding is not None or errors is not None:
                raise oefmt(space.w_TypeError,
                            "decoding Unicode is not supported")
            if (is_precisely_unicode and
                space.is_w(w_unicodetype, space.w_unicode)):
                return w_obj
            w_value = w_obj
        else:
            if encoding is None and errors is None:
                w_value = unicode_from_object(space, w_obj)
            else:
                w_value = unicode_from_encoded_object(space, w_obj,
                                                      encoding, errors)
            if space.is_w(w_unicodetype, space.w_unicode):
                return w_value

        assert isinstance(w_value, W_UnicodeObject)
        w_newobj = space.allocate_instance(W_UnicodeObject, w_unicodetype)
        W_UnicodeObject.__init__(w_newobj, w_value._utf8, w_value._length)
        return w_newobj

    def descr_repr(self, space):
        chars = self._utf8.decode('utf8')
        size = len(chars)
        s = _repr_function(chars, size, "strict")
        return space.newtext(s)

    def descr_str(self, space):
        return encode_object(space, self, None, None)

    def descr_hash(self, space):
        x = compute_hash(self._utf8)
        return space.newint(x)

    def descr_eq(self, space, w_other):
        try:
            res = self._utf8 == self.convert_arg_to_w_unicode(space, w_other)._utf8
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            if (e.match(space, space.w_UnicodeDecodeError) or
                e.match(space, space.w_UnicodeEncodeError)):
                msg = ("Unicode equal comparison failed to convert both "
                       "arguments to Unicode - interpreting them as being "
                       "unequal")
                space.warn(space.newtext(msg), space.w_UnicodeWarning)
                return space.w_False
            raise
        return space.newbool(res)

    def descr_ne(self, space, w_other):
        try:
            res = self._utf8 != self.convert_arg_to_w_unicode(space, w_other)._utf8
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            if (e.match(space, space.w_UnicodeDecodeError) or
                e.match(space, space.w_UnicodeEncodeError)):
                msg = ("Unicode unequal comparison failed to convert both "
                       "arguments to Unicode - interpreting them as being "
                       "unequal")
                space.warn(space.newtext(msg), space.w_UnicodeWarning)
                return space.w_True
            raise
        return space.newbool(res)

    def descr_lt(self, space, w_other):
        try:
            res = self._utf8 < self.convert_arg_to_w_unicode(space, w_other)._utf8
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise
        return space.newbool(res)

    def descr_le(self, space, w_other):
        try:
            res = self._utf8 <= self.convert_arg_to_w_unicode(space, w_other)._utf8
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise
        return space.newbool(res)

    def descr_gt(self, space, w_other):
        try:
            res = self._utf8 > self.convert_arg_to_w_unicode(space, w_other)._utf8
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise
        return space.newbool(res)

    def descr_ge(self, space, w_other):
        try:
            res = self._utf8 >= self.convert_arg_to_w_unicode(space, w_other)._utf8
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise
        return space.newbool(res)

    def descr_format(self, space, __args__):
        return newformat.format_method(space, self, __args__, is_unicode=True)

    def descr__format__(self, space, w_format_spec):
        if not space.isinstance_w(w_format_spec, space.w_unicode):
            w_format_spec = space.call_function(space.w_unicode, w_format_spec)
        spec = space.unicode_w(w_format_spec)
        formatter = newformat.unicode_formatter(space, spec)
        self2 = unicode_from_object(space, self)
        assert isinstance(self2, W_UnicodeObject)
        # XXX
        return formatter.format_string(self2._utf8.decode("utf8"))

    def descr_mod(self, space, w_values):
        return mod_format(space, self, w_values, do_unicode=True)

    def descr_rmod(self, space, w_values):
        return mod_format(space, w_values, self, do_unicode=True)

    def descr_translate(self, space, w_table):
        selfvalue = self._utf8.decode("utf8")
        w_sys = space.getbuiltinmodule('sys')
        maxunicode = space.int_w(space.getattr(w_sys,
                                               space.newtext("maxunicode")))
        result = []
        for unichar in selfvalue:
            try:
                w_newval = space.getitem(w_table, space.newint(ord(unichar)))
            except OperationError as e:
                if e.match(space, space.w_LookupError):
                    result.append(unichar)
                else:
                    raise
            else:
                if space.is_w(w_newval, space.w_None):
                    continue
                elif space.isinstance_w(w_newval, space.w_int):
                    newval = space.int_w(w_newval)
                    if newval < 0 or newval > maxunicode:
                        raise oefmt(space.w_TypeError,
                                    "character mapping must be in range(%s)",
                                    hex(maxunicode + 1))
                    result.append(unichr(newval))
                elif space.isinstance_w(w_newval, space.w_unicode):
                    result.append(space.utf8_w(w_newval).decode("utf8"))
                else:
                    raise oefmt(space.w_TypeError,
                                "character mapping must return integer, None "
                                "or unicode")
        return W_UnicodeObject(u''.join(result).encode("utf8"), -1)

    def descr_encode(self, space, w_encoding=None, w_errors=None):
        encoding, errors = _get_encoding_and_errors(space, w_encoding,
                                                    w_errors)
        return encode_object(space, self, encoding, errors)

    _StringMethods_descr_join = descr_join
    def descr_join(self, space, w_list):
        l = space.listview_unicode(w_list)
        if l is not None:
            assert False, "unreachable"
            if len(l) == 1:
                return space.newunicode(l[0])
            return space.newunicode(self._utf8).join(l)
        return self._StringMethods_descr_join(space, w_list)

    def _join_return_one(self, space, w_obj):
        return space.is_w(space.type(w_obj), space.w_unicode)

    def _join_check_item(self, space, w_obj):
        if (space.isinstance_w(w_obj, space.w_bytes) or
            space.isinstance_w(w_obj, space.w_unicode)):
            return 0
        return 1

    def descr_formatter_parser(self, space):
        from pypy.objspace.std.newformat import unicode_template_formatter
        tformat = unicode_template_formatter(space, space.unicode_w(self))
        return tformat.formatter_parser()

    def descr_formatter_field_name_split(self, space):
        from pypy.objspace.std.newformat import unicode_template_formatter
        tformat = unicode_template_formatter(space, space.unicode_w(self))
        return tformat.formatter_field_name_split()

    def descr_isdecimal(self, space):
        return self._is_generic(space, '_isdecimal')

    def descr_isnumeric(self, space):
        return self._is_generic(space, '_isnumeric')

    def descr_islower(self, space):
        cased = False
        val = self._utf8
        i = 0
        while i < len(val):
            uchar = rutf8.codepoint_at_pos(val, i)
            if (unicodedb.isupper(uchar) or
                unicodedb.istitle(uchar)):
                return space.w_False
            if not cased and unicodedb.islower(uchar):
                cased = True
            i = rutf8.next_codepoint_pos(val, i)
        return space.newbool(cased)

    def descr_isupper(self, space):
        cased = False
        i = 0
        val = self._utf8
        while i < len(val):
            uchar = rutf8.codepoint_at_pos(val, i)
            if (unicodedb.islower(uchar) or
                unicodedb.istitle(uchar)):
                return space.w_False
            if not cased and unicodedb.isupper(uchar):
                cased = True
            i = rutf8.next_codepoint_pos(val, i)
        return space.newbool(cased)

    def descr_add(self, space, w_other):
        try:
            w_other = self.convert_arg_to_w_unicode(space, w_other)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise
        return W_UnicodeObject(self._utf8 + w_other._utf8,
                               self._len() + w_other._len())

    @jit.look_inside_iff(lambda self, space, list_w, size:
                         jit.loop_unrolling_heuristic(list_w, size))
    def _str_join_many_items(self, space, list_w, size):
        value = self._utf8
        lgt = self._len() * (size - 1)

        prealloc_size = len(value) * (size - 1)
        unwrapped = newlist_hint(size)
        for i in range(size):
            w_s = list_w[i]
            check_item = self._join_check_item(space, w_s)
            if check_item == 1:
                raise oefmt(space.w_TypeError,
                            "sequence item %d: expected string, %T found",
                            i, w_s)
            elif check_item == 2:
                return self._join_autoconvert(space, list_w)
            # XXX Maybe the extra copy here is okay? It was basically going to
            #     happen anyway, what with being placed into the builder
            w_u = self.convert_arg_to_w_unicode(space, w_s)
            unwrapped.append(w_u._utf8)
            lgt += w_u._length
            prealloc_size += len(unwrapped[i])

        sb = StringBuilder(prealloc_size)
        for i in range(size):
            if value and i != 0:
                sb.append(value)
            sb.append(unwrapped[i])
        return W_UnicodeObject(sb.build(), lgt)

    @unwrap_spec(keepends=bool)
    def descr_splitlines(self, space, keepends=False):
        value = self._utf8
        length = len(value)
        strs_w = []
        pos = 0
        while pos < length:
            sol = pos
            lgt = 0
            while pos < length and not self._islinebreak(value, pos):
                pos = rutf8.next_codepoint_pos(value, pos)
                lgt += 1
            eol = pos
            if pos < length:
                pos = rutf8.next_codepoint_pos(value, pos)
            # read CRLF as one line break
            if pos < length and value[eol] == '\r' and value[pos] == '\n':
                pos += 1
                if keepends:
                    lgt += 1
            if keepends:
                eol = pos
                lgt += 1
            # XXX find out why lgt calculation is off
            strs_w.append(W_UnicodeObject(value[sol:eol], -1))
        return space.newlist(strs_w)

    @unwrap_spec(width=int)
    def descr_zfill(self, space, width):
        selfval = self._utf8
        if len(selfval) == 0:
            return W_UnicodeObject('0' * width, width)
        num_zeros = width - self._len()
        if num_zeros <= 0:
            # cannot return self, in case it is a subclass of str
            return W_UnicodeObject(selfval, self._len())
        builder = StringBuilder(num_zeros + len(selfval))
        if len(selfval) > 0 and (selfval[0] == '+' or selfval[0] == '-'):
            # copy sign to first position
            builder.append(selfval[0])
            start = 1
        else:
            start = 0
        builder.append_multiple_char('0', num_zeros)
        builder.append_slice(selfval, start, len(selfval))
        return W_UnicodeObject(builder.build(), width)

    @unwrap_spec(maxsplit=int)
    def descr_split(self, space, w_sep=None, maxsplit=-1):
        res = []
        value = self._utf8
        if space.is_none(w_sep):
            res = split(value, maxsplit=maxsplit, isutf8=1)
            return space.newlist_from_unicode(res)

        by = self.convert_arg_to_w_unicode(space, w_sep)._utf8
        if len(by) == 0:
            raise oefmt(space.w_ValueError, "empty separator")
        res = split(value, by, maxsplit, isutf8=1)

        return space.newlist_from_unicode(res)

    @unwrap_spec(maxsplit=int)
    def descr_rsplit(self, space, w_sep=None, maxsplit=-1):
        res = []
        value = self._utf8
        if space.is_none(w_sep):
            res = rsplit(value, maxsplit=maxsplit, isutf8=1)
            return space.newlist_from_unicode(res)

        by = self.convert_arg_to_w_unicode(space, w_sep)._utf8
        if len(by) == 0:
            raise oefmt(space.w_ValueError, "empty separator")
        res = rsplit(value, by, maxsplit, isutf8=1)

        return space.newlist_from_unicode(res)

    @unwrap_spec(width=int, w_fillchar=WrappedDefault(' '))
    def descr_center(self, space, width, w_fillchar):
        value = self._utf8
        fillchar = self.convert_arg_to_w_unicode(space, w_fillchar)._utf8
        if len(fillchar) != 1:
            raise oefmt(space.w_TypeError,
                        "center() argument 2 must be a single character")

        d = width - self._len()
        if d > 0:
            offset = d//2 + (d & width & 1)
            fillchar = fillchar[0]
            centered = offset * fillchar + value + (d - offset) * fillchar
        else:
            centered = value
            d = 0

        return W_UnicodeObject(centered, self._len() + d)

    def descr_contains(self, space, w_sub):
        value = self._utf8
        w_other = self.convert_arg_to_w_unicode(space, w_sub)
        return space.newbool(value.find(w_other._utf8) >= 0)


    @unwrap_spec(count=int)
    def descr_replace(self, space, w_old, w_new, count=-1):
        input = self._utf8

        w_sub = self.convert_arg_to_w_unicode(space, w_old)
        w_by = self.convert_arg_to_w_unicode(space, w_new)
        # the following two lines are for being bug-to-bug compatible
        # with CPython: see issue #2448
        if count >= 0 and len(input) == 0:
            return self._empty()
        try:
            res = replace(input, w_sub._utf8, w_by._utf8, count)
        except OverflowError:
            raise oefmt(space.w_OverflowError, "replace string is too long")

        return W_UnicodeObject(res, -1)

    def descr_mul(self, space, w_times):
        try:
            times = space.getindex_w(w_times, space.w_OverflowError)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise
        if times <= 0:
            return self._empty()
        if len(self._utf8) == 1:
            return W_UnicodeObject(self._utf8[0] * times, times)
        return W_UnicodeObject(self._utf8 * times, times * self._len())

    descr_rmul = descr_mul

    def _getitem_result(self, space, index):
        if self._ucs4 is None:
            self._ucs4 = self._utf8.decode('utf-8')
        try:
            return W_UnicodeObject(self._ucs4[index].encode('utf-8'), 1)
        except IndexError:
            raise oefmt(space.w_IndexError, "string index out of range")

    @unwrap_spec(width=int, w_fillchar=WrappedDefault(' '))
    def descr_rjust(self, space, width, w_fillchar):
        value = self._utf8
        lgt = self._len()
        w_fillchar = self.convert_arg_to_w_unicode(space, w_fillchar)
        if w_fillchar._len() != 1:
            raise oefmt(space.w_TypeError,
                        "rjust() argument 2 must be a single character")
        d = width - lgt
        if d > 0:
            if len(w_fillchar._utf8) == 1:
                # speedup
                value = d * w_fillchar._utf8[0] + value
            else:
                value = d * w_fillchar._utf8 + value
            return W_UnicodeObject(value, width)

        return W_UnicodeObject(value, lgt)

    @unwrap_spec(width=int, w_fillchar=WrappedDefault(' '))
    def descr_ljust(self, space, width, w_fillchar):
        value = self._utf8
        w_fillchar = self.convert_arg_to_w_unicode(space, w_fillchar)
        if w_fillchar._len() != 1:
            raise oefmt(space.w_TypeError,
                        "ljust() argument 2 must be a single character")
        d = width - self._len()
        if d > 0:
            if len(w_fillchar._utf8) == 1:
                # speedup
                value = value + d * w_fillchar._utf8[0]
            else:
                value = value + d * w_fillchar._utf8
            return W_UnicodeObject(value, width)

        return W_UnicodeObject(value, self._len())

    def _utf8_sliced(self, start, stop, lgt):
        assert start >= 0
        assert stop >= 0
        #if start == 0 and stop == len(s) and space.is_w(space.type(orig_obj),
        #                                                space.w_bytes):
        #    return orig_obj
        return W_UnicodeObject(self._utf8[start:stop], lgt)

    def _strip_none(self, space, left, right):
        "internal function called by str_xstrip methods"
        value = self._utf8

        lpos = 0
        rpos = len(value)
        lgt = self._len()

        if left:
            while lpos < rpos and rutf8.isspace(value, lpos):
                lpos = rutf8.next_codepoint_pos(value, lpos)
                lgt -= 1

        if right:
            while rpos > lpos and rutf8.isspace(value,
                                         rutf8.prev_codepoint_pos(value, rpos)):
                rpos = rutf8.prev_codepoint_pos(value, rpos)
                lgt -= 1

        assert rpos >= lpos    # annotator hint, don't remove
        return self._utf8_sliced(lpos, rpos, lgt)

    def _strip(self, space, w_chars, left, right, name='strip'):
        "internal function called by str_xstrip methods"
        value = self._utf8
        chars = self.convert_arg_to_w_unicode(space, w_chars, strict=name)._utf8

        lpos = 0
        rpos = len(value)
        lgt = self._len()

        if left:
            while lpos < rpos and rutf8.utf8_in_chars(value, lpos, chars):
                lpos = rutf8.next_codepoint_pos(value, lpos)
                lgt -= 1

        if right:
            while rpos > lpos and rutf8.utf8_in_chars(value,
                    rutf8.prev_codepoint_pos(value, rpos), chars):
                rpos = rutf8.prev_codepoint_pos(value, rpos)
                lgt -= 1

        assert rpos >= lpos    # annotator hint, don't remove
        return self._utf8_sliced(lpos, rpos, lgt)

    def descr_startswith(self, space, w_prefix, w_start=None, w_end=None):
        (start, end) = self._convert_idx_params_unicode(space, w_start, w_end)
        if space.isinstance_w(w_prefix, space.w_tuple):
            return self._startswith_tuple(space, w_prefix, start, end)
        return space.newbool(self._startswith(space, w_prefix, start, end))

    def _startswith_tuple(self, space, w_prefix, start, end):
        for w_prefix in space.fixedview(w_prefix):
            if self._startswith(space, w_prefix, start, end):
                return space.w_True
        return space.w_False

    def _startswith(self, space, w_prefix, start, end):
        prefix = self.convert_arg_to_w_unicode(space, w_prefix)._utf8
        if start > self._len():
            return len(prefix) == 0 # bug-to-bug cpython compatibility
        xxx
        return startswith(self._utf8, prefix, start, end)


    def descr_getnewargs(self, space):
        return space.newtuple([W_UnicodeObject(self._utf8, self._length)])



def wrapunicode(space, uni):
    return W_UnicodeObject(uni)


def plain_str2unicode(space, s):
    try:
        return unicode(s)
    except UnicodeDecodeError:
        for i in range(len(s)):
            if ord(s[i]) > 127:
                raise OperationError(
                    space.w_UnicodeDecodeError,
                    space.newtuple([
                    space.newtext('ascii'),
                    space.newbytes(s),
                    space.newint(i),
                    space.newint(i+1),
                    space.newtext("ordinal not in range(128)")]))
        assert False, "unreachable"


# stuff imported from bytesobject for interoperability


# ____________________________________________________________

def getdefaultencoding(space):
    return space.sys.defaultencoding


def _get_encoding_and_errors(space, w_encoding, w_errors):
    encoding = None if w_encoding is None else space.text_w(w_encoding)
    errors = None if w_errors is None else space.text_w(w_errors)
    return encoding, errors


def encode_object(space, w_object, encoding, errors):
    if encoding is None:
        # Get the encoder functions as a wrapped object.
        # This lookup is cached.
        w_encoder = space.sys.get_w_default_encoder()
    else:
        if errors is None or errors == 'strict':
            try:
                if encoding == 'ascii':
                    s = space.utf8_w(w_object)
                    try:
                        rutf8.check_ascii(s)
                    except rutf8.AsciiCheckError as a:
                        eh = unicodehelper.raise_unicode_exception_encode
                        eh(None, "ascii", "ordinal not in range(128)", s,
                            a.pos, a.pos + 1)
                        assert False, "always raises"
                    return space.newbytes(s)
                if encoding == 'utf-8':
                    u = space.utf8_w(w_object)
                    return space.newbytes(u)
                    # XXX is this enough?
                    #eh = unicodehelper.raise_unicode_exception_encode
                    #return space.newbytes(unicode_encode_utf_8(
                    #        u, len(u), None, errorhandler=eh,
                    #        allow_surrogates=True))
            except unicodehelper.RUnicodeEncodeError as ue:
                raise OperationError(space.w_UnicodeEncodeError,
                                     space.newtuple([
                    space.newtext(ue.encoding),
                    space.newutf8(ue.object, -1),
                    space.newint(ue.start),
                    space.newint(ue.end),
                    space.newtext(ue.reason)]))
        from pypy.module._codecs.interp_codecs import lookup_codec
        w_encoder = space.getitem(lookup_codec(space, encoding), space.newint(0))
    if errors is None:
        w_errors = space.newtext('strict')
    else:
        w_errors = space.newtext(errors)
    w_restuple = space.call_function(w_encoder, w_object, w_errors)
    w_retval = space.getitem(w_restuple, space.newint(0))
    if not space.isinstance_w(w_retval, space.w_bytes):
        raise oefmt(space.w_TypeError,
                    "encoder did not return an string object (type '%T')",
                    w_retval)
    return w_retval


def decode_object(space, w_obj, encoding, errors):
    if encoding is None:
        encoding = getdefaultencoding(space)
    if errors is None or errors == 'strict':
        if encoding == 'ascii':
            # XXX error handling
            s = space.charbuf_w(w_obj)
            try:
                rutf8.check_ascii(s)
            except rutf8.AsciiCheckError as e:
                unicodehelper.decode_error_handler(space)(None,
                    'ascii', "ordinal not in range(128)", s, e.pos, e.pos+1)
                assert False
            return space.newutf8(s, len(s))
        if encoding == 'utf-8':
            s = space.charbuf_w(w_obj)
            eh = unicodehelper.decode_error_handler(space)
            try:
                _, lgt = rutf8.str_check_utf8(s, len(s), final=True,
                                              allow_surrogates=True)
            except rutf8.Utf8CheckError as e:
                eh(None, 'utf8', e.msg, s, e.startpos, e.endpos)
                assert False, "has to raise"
            return space.newutf8(s, lgt)
    w_codecs = space.getbuiltinmodule("_codecs")
    w_decode = space.getattr(w_codecs, space.newtext("decode"))
    if errors is None:
        w_retval = space.call_function(w_decode, w_obj, space.newtext(encoding))
    else:
        w_retval = space.call_function(w_decode, w_obj, space.newtext(encoding),
                                       space.newtext(errors))
    return w_retval


def unicode_from_encoded_object(space, w_obj, encoding, errors):
    # explicitly block bytearray on 2.7
    from .bytearrayobject import W_BytearrayObject
    if isinstance(w_obj, W_BytearrayObject):
        raise oefmt(space.w_TypeError, "decoding bytearray is not supported")

    w_retval = decode_object(space, w_obj, encoding, errors)
    if not space.isinstance_w(w_retval, space.w_unicode):
        raise oefmt(space.w_TypeError,
                    "decoder did not return an unicode object (type '%T')",
                    w_retval)
    assert isinstance(w_retval, W_UnicodeObject)
    return w_retval


def unicode_from_object(space, w_obj):
    if space.is_w(space.type(w_obj), space.w_unicode):
        return w_obj
    elif space.is_w(space.type(w_obj), space.w_bytes):
        w_res = w_obj
    else:
        w_unicode_method = space.lookup(w_obj, "__unicode__")
        # obscure workaround: for the next two lines see
        # test_unicode_conversion_with__str__
        if w_unicode_method is None:
            if space.isinstance_w(w_obj, space.w_unicode):
                return space.newunicode(space.unicode_w(w_obj))
            w_unicode_method = space.lookup(w_obj, "__str__")
        if w_unicode_method is not None:
            w_res = space.get_and_call_function(w_unicode_method, w_obj)
        else:
            w_res = space.str(w_obj)
        if space.isinstance_w(w_res, space.w_unicode):
            return w_res
    return unicode_from_encoded_object(space, w_res, None, "strict")


def unicode_from_string(space, w_bytes):
    # this is a performance and bootstrapping hack
    encoding = getdefaultencoding(space)
    if encoding != 'ascii':
        return unicode_from_encoded_object(space, w_bytes, encoding, "strict")
    s = space.bytes_w(w_bytes)
    try:
        rutf8.check_ascii(s)
    except rutf8.AsciiCheckError:
        # raising UnicodeDecodeError is messy, "please crash for me"
        return unicode_from_encoded_object(space, w_bytes, "ascii", "strict")
    return W_UnicodeObject(s, len(s))


class UnicodeDocstrings:
    """unicode(object='') -> unicode object
    unicode(string[, encoding[, errors]]) -> unicode object

    Create a new Unicode object from the given encoded string.
    encoding defaults to the current default string encoding.
    errors can be 'strict', 'replace' or 'ignore' and defaults to 'strict'.

    """

    def __add__():
        """x.__add__(y) <==> x+y"""

    def __contains__():
        """x.__contains__(y) <==> y in x"""

    def __eq__():
        """x.__eq__(y) <==> x==y"""

    def __format__():
        """S.__format__(format_spec) -> unicode

        Return a formatted version of S as described by format_spec.
        """

    def __ge__():
        """x.__ge__(y) <==> x>=y"""

    def __getattribute__():
        """x.__getattribute__('name') <==> x.name"""

    def __getitem__():
        """x.__getitem__(y) <==> x[y]"""

    def __getnewargs__():
        ""

    def __getslice__():
        """x.__getslice__(i, j) <==> x[i:j]

        Use of negative indices is not supported.
        """

    def __gt__():
        """x.__gt__(y) <==> x>y"""

    def __hash__():
        """x.__hash__() <==> hash(x)"""

    def __le__():
        """x.__le__(y) <==> x<=y"""

    def __len__():
        """x.__len__() <==> len(x)"""

    def __lt__():
        """x.__lt__(y) <==> x<y"""

    def __mod__():
        """x.__mod__(y) <==> x%y"""

    def __rmod__():
        """x.__rmod__(y) <==> y%x"""

    def __mul__():
        """x.__mul__(n) <==> x*n"""

    def __ne__():
        """x.__ne__(y) <==> x!=y"""

    def __repr__():
        """x.__repr__() <==> repr(x)"""

    def __rmod__():
        """x.__rmod__(y) <==> y%x"""

    def __rmul__():
        """x.__rmul__(n) <==> n*x"""

    def __sizeof__():
        """S.__sizeof__() -> size of S in memory, in bytes"""

    def __str__():
        """x.__str__() <==> str(x)"""

    def capitalize():
        """S.capitalize() -> unicode

        Return a capitalized version of S, i.e. make the first character
        have upper case and the rest lower case.
        """

    def center():
        """S.center(width[, fillchar]) -> unicode

        Return S centered in a Unicode string of length width. Padding is
        done using the specified fill character (default is a space).
        """

    def count():
        """S.count(sub[, start[, end]]) -> int

        Return the number of non-overlapping occurrences of substring sub in
        Unicode string S[start:end].  Optional arguments start and end are
        interpreted as in slice notation.
        """

    def decode():
        """S.decode(encoding=None, errors='strict') -> string or unicode

        Decode S using the codec registered for encoding. encoding defaults
        to the default encoding. errors may be given to set a different error
        handling scheme. Default is 'strict' meaning that encoding errors raise
        a UnicodeDecodeError. Other possible values are 'ignore' and 'replace'
        as well as any other name registered with codecs.register_error that is
        able to handle UnicodeDecodeErrors.
        """

    def encode():
        """S.encode(encoding=None, errors='strict') -> string or unicode

        Encode S using the codec registered for encoding. encoding defaults
        to the default encoding. errors may be given to set a different error
        handling scheme. Default is 'strict' meaning that encoding errors raise
        a UnicodeEncodeError. Other possible values are 'ignore', 'replace' and
        'xmlcharrefreplace' as well as any other name registered with
        codecs.register_error that can handle UnicodeEncodeErrors.
        """

    def endswith():
        """S.endswith(suffix[, start[, end]]) -> bool

        Return True if S ends with the specified suffix, False otherwise.
        With optional start, test S beginning at that position.
        With optional end, stop comparing S at that position.
        suffix can also be a tuple of strings to try.
        """

    def expandtabs():
        """S.expandtabs([tabsize]) -> unicode

        Return a copy of S where all tab characters are expanded using spaces.
        If tabsize is not given, a tab size of 8 characters is assumed.
        """

    def find():
        """S.find(sub[, start[, end]]) -> int

        Return the lowest index in S where substring sub is found,
        such that sub is contained within S[start:end].  Optional
        arguments start and end are interpreted as in slice notation.

        Return -1 on failure.
        """

    def format():
        """S.format(*args, **kwargs) -> unicode

        Return a formatted version of S, using substitutions from args and
        kwargs.  The substitutions are identified by braces ('{' and '}').
        """

    def index():
        """S.index(sub[, start[, end]]) -> int

        Like S.find() but raise ValueError when the substring is not found.
        """

    def isalnum():
        """S.isalnum() -> bool

        Return True if all characters in S are alphanumeric
        and there is at least one character in S, False otherwise.
        """

    def isalpha():
        """S.isalpha() -> bool

        Return True if all characters in S are alphabetic
        and there is at least one character in S, False otherwise.
        """

    def isdecimal():
        """S.isdecimal() -> bool

        Return True if there are only decimal characters in S,
        False otherwise.
        """

    def isdigit():
        """S.isdigit() -> bool

        Return True if all characters in S are digits
        and there is at least one character in S, False otherwise.
        """

    def islower():
        """S.islower() -> bool

        Return True if all cased characters in S are lowercase and there is
        at least one cased character in S, False otherwise.
        """

    def isnumeric():
        """S.isnumeric() -> bool

        Return True if there are only numeric characters in S,
        False otherwise.
        """

    def isspace():
        """S.isspace() -> bool

        Return True if all characters in S are whitespace
        and there is at least one character in S, False otherwise.
        """

    def istitle():
        """S.istitle() -> bool

        Return True if S is a titlecased string and there is at least one
        character in S, i.e. upper- and titlecase characters may only
        follow uncased characters and lowercase characters only cased ones.
        Return False otherwise.
        """

    def isupper():
        """S.isupper() -> bool

        Return True if all cased characters in S are uppercase and there is
        at least one cased character in S, False otherwise.
        """

    def join():
        """S.join(iterable) -> unicode

        Return a string which is the concatenation of the strings in the
        iterable.  The separator between elements is S.
        """

    def ljust():
        """S.ljust(width[, fillchar]) -> int

        Return S left-justified in a Unicode string of length width. Padding is
        done using the specified fill character (default is a space).
        """

    def lower():
        """S.lower() -> unicode

        Return a copy of the string S converted to lowercase.
        """

    def lstrip():
        """S.lstrip([chars]) -> unicode

        Return a copy of the string S with leading whitespace removed.
        If chars is given and not None, remove characters in chars instead.
        If chars is a str, it will be converted to unicode before stripping
        """

    def partition():
        """S.partition(sep) -> (head, sep, tail)

        Search for the separator sep in S, and return the part before it,
        the separator itself, and the part after it.  If the separator is not
        found, return S and two empty strings.
        """

    def replace():
        """S.replace(old, new[, count]) -> unicode

        Return a copy of S with all occurrences of substring
        old replaced by new.  If the optional argument count is
        given, only the first count occurrences are replaced.
        """

    def rfind():
        """S.rfind(sub[, start[, end]]) -> int

        Return the highest index in S where substring sub is found,
        such that sub is contained within S[start:end].  Optional
        arguments start and end are interpreted as in slice notation.

        Return -1 on failure.
        """

    def rindex():
        """S.rindex(sub[, start[, end]]) -> int

        Like S.rfind() but raise ValueError when the substring is not found.
        """

    def rjust():
        """S.rjust(width[, fillchar]) -> unicode

        Return S right-justified in a Unicode string of length width. Padding
        is done using the specified fill character (default is a space).
        """

    def rpartition():
        """S.rpartition(sep) -> (head, sep, tail)

        Search for the separator sep in S, starting at the end of S, and return
        the part before it, the separator itself, and the part after it.  If
        the separator is not found, return two empty strings and S.
        """

    def rsplit():
        """S.rsplit(sep=None, maxsplit=-1) -> list of strings

        Return a list of the words in S, using sep as the
        delimiter string, starting at the end of the string and
        working to the front.  If maxsplit is given, at most maxsplit
        splits are done. If sep is not specified, any whitespace string
        is a separator.
        """

    def rstrip():
        """S.rstrip([chars]) -> unicode

        Return a copy of the string S with trailing whitespace removed.
        If chars is given and not None, remove characters in chars instead.
        If chars is a str, it will be converted to unicode before stripping
        """

    def split():
        """S.split(sep=None, maxsplit=-1) -> list of strings

        Return a list of the words in S, using sep as the
        delimiter string.  If maxsplit is given, at most maxsplit
        splits are done. If sep is not specified or is None, any
        whitespace string is a separator and empty strings are
        removed from the result.
        """

    def splitlines():
        """S.splitlines(keepends=False) -> list of strings

        Return a list of the lines in S, breaking at line boundaries.
        Line breaks are not included in the resulting list unless keepends
        is given and true.
        """

    def startswith():
        """S.startswith(prefix[, start[, end]]) -> bool

        Return True if S starts with the specified prefix, False otherwise.
        With optional start, test S beginning at that position.
        With optional end, stop comparing S at that position.
        prefix can also be a tuple of strings to try.
        """

    def strip():
        """S.strip([chars]) -> unicode

        Return a copy of the string S with leading and trailing
        whitespace removed.
        If chars is given and not None, remove characters in chars instead.
        If chars is a str, it will be converted to unicode before stripping
        """

    def swapcase():
        """S.swapcase() -> unicode

        Return a copy of S with uppercase characters converted to lowercase
        and vice versa.
        """

    def title():
        """S.title() -> unicode

        Return a titlecased version of S, i.e. words start with title case
        characters, all remaining cased characters have lower case.
        """

    def translate():
        """S.translate(table) -> unicode

        Return a copy of the string S, where all characters have been mapped
        through the given translation table, which must be a mapping of
        Unicode ordinals to Unicode ordinals, Unicode strings or None.
        Unmapped characters are left untouched. Characters mapped to None
        are deleted.
        """

    def upper():
        """S.upper() -> unicode

        Return a copy of S converted to uppercase.
        """

    def zfill():
        """S.zfill(width) -> unicode

        Pad a numeric string S with zeros on the left, to fill a field
        of the specified width. The string S is never truncated.
        """


W_UnicodeObject.typedef = TypeDef(
    "unicode", basestring_typedef,
    __new__ = interp2app(W_UnicodeObject.descr_new),
    __doc__ = UnicodeDocstrings.__doc__,

    __repr__ = interp2app(W_UnicodeObject.descr_repr,
                          doc=UnicodeDocstrings.__repr__.__doc__),
    __str__ = interp2app(W_UnicodeObject.descr_str,
                         doc=UnicodeDocstrings.__str__.__doc__),
    __hash__ = interp2app(W_UnicodeObject.descr_hash,
                          doc=UnicodeDocstrings.__hash__.__doc__),

    __eq__ = interp2app(W_UnicodeObject.descr_eq,
                        doc=UnicodeDocstrings.__eq__.__doc__),
    __ne__ = interp2app(W_UnicodeObject.descr_ne,
                        doc=UnicodeDocstrings.__ne__.__doc__),
    __lt__ = interp2app(W_UnicodeObject.descr_lt,
                        doc=UnicodeDocstrings.__lt__.__doc__),
    __le__ = interp2app(W_UnicodeObject.descr_le,
                        doc=UnicodeDocstrings.__le__.__doc__),
    __gt__ = interp2app(W_UnicodeObject.descr_gt,
                        doc=UnicodeDocstrings.__gt__.__doc__),
    __ge__ = interp2app(W_UnicodeObject.descr_ge,
                        doc=UnicodeDocstrings.__ge__.__doc__),

    __len__ = interp2app(W_UnicodeObject.descr_len,
                         doc=UnicodeDocstrings.__len__.__doc__),
    __contains__ = interp2app(W_UnicodeObject.descr_contains,
                              doc=UnicodeDocstrings.__contains__.__doc__),

    __add__ = interp2app(W_UnicodeObject.descr_add,
                         doc=UnicodeDocstrings.__add__.__doc__),
    __mul__ = interp2app(W_UnicodeObject.descr_mul,
                         doc=UnicodeDocstrings.__mul__.__doc__),
    __rmul__ = interp2app(W_UnicodeObject.descr_mul,
                          doc=UnicodeDocstrings.__rmul__.__doc__),

    __getitem__ = interp2app(W_UnicodeObject.descr_getitem,
                             doc=UnicodeDocstrings.__getitem__.__doc__),
    __getslice__ = interp2app(W_UnicodeObject.descr_getslice,
                              doc=UnicodeDocstrings.__getslice__.__doc__),

    capitalize = interp2app(W_UnicodeObject.descr_capitalize,
                            doc=UnicodeDocstrings.capitalize.__doc__),
    center = interp2app(W_UnicodeObject.descr_center,
                        doc=UnicodeDocstrings.center.__doc__),
    count = interp2app(W_UnicodeObject.descr_count,
                       doc=UnicodeDocstrings.count.__doc__),
    decode = interp2app(W_UnicodeObject.descr_decode,
                        doc=UnicodeDocstrings.decode.__doc__),
    encode = interp2app(W_UnicodeObject.descr_encode,
                        doc=UnicodeDocstrings.encode.__doc__),
    expandtabs = interp2app(W_UnicodeObject.descr_expandtabs,
                            doc=UnicodeDocstrings.expandtabs.__doc__),
    find = interp2app(W_UnicodeObject.descr_find,
                      doc=UnicodeDocstrings.find.__doc__),
    rfind = interp2app(W_UnicodeObject.descr_rfind,
                       doc=UnicodeDocstrings.rfind.__doc__),
    index = interp2app(W_UnicodeObject.descr_index,
                       doc=UnicodeDocstrings.index.__doc__),
    rindex = interp2app(W_UnicodeObject.descr_rindex,
                        doc=UnicodeDocstrings.rindex.__doc__),
    isalnum = interp2app(W_UnicodeObject.descr_isalnum,
                         doc=UnicodeDocstrings.isalnum.__doc__),
    isalpha = interp2app(W_UnicodeObject.descr_isalpha,
                         doc=UnicodeDocstrings.isalpha.__doc__),
    isdecimal = interp2app(W_UnicodeObject.descr_isdecimal,
                           doc=UnicodeDocstrings.isdecimal.__doc__),
    isdigit = interp2app(W_UnicodeObject.descr_isdigit,
                         doc=UnicodeDocstrings.isdigit.__doc__),
    islower = interp2app(W_UnicodeObject.descr_islower,
                         doc=UnicodeDocstrings.islower.__doc__),
    isnumeric = interp2app(W_UnicodeObject.descr_isnumeric,
                           doc=UnicodeDocstrings.isnumeric.__doc__),
    isspace = interp2app(W_UnicodeObject.descr_isspace,
                         doc=UnicodeDocstrings.isspace.__doc__),
    istitle = interp2app(W_UnicodeObject.descr_istitle,
                         doc=UnicodeDocstrings.istitle.__doc__),
    isupper = interp2app(W_UnicodeObject.descr_isupper,
                         doc=UnicodeDocstrings.isupper.__doc__),
    join = interp2app(W_UnicodeObject.descr_join,
                      doc=UnicodeDocstrings.join.__doc__),
    ljust = interp2app(W_UnicodeObject.descr_ljust,
                       doc=UnicodeDocstrings.ljust.__doc__),
    rjust = interp2app(W_UnicodeObject.descr_rjust,
                       doc=UnicodeDocstrings.rjust.__doc__),
    lower = interp2app(W_UnicodeObject.descr_lower,
                       doc=UnicodeDocstrings.lower.__doc__),
    partition = interp2app(W_UnicodeObject.descr_partition,
                           doc=UnicodeDocstrings.partition.__doc__),
    rpartition = interp2app(W_UnicodeObject.descr_rpartition,
                            doc=UnicodeDocstrings.rpartition.__doc__),
    replace = interp2app(W_UnicodeObject.descr_replace,
                         doc=UnicodeDocstrings.replace.__doc__),
    split = interp2app(W_UnicodeObject.descr_split,
                       doc=UnicodeDocstrings.split.__doc__),
    rsplit = interp2app(W_UnicodeObject.descr_rsplit,
                        doc=UnicodeDocstrings.rsplit.__doc__),
    splitlines = interp2app(W_UnicodeObject.descr_splitlines,
                            doc=UnicodeDocstrings.splitlines.__doc__),
    startswith = interp2app(W_UnicodeObject.descr_startswith,
                            doc=UnicodeDocstrings.startswith.__doc__),
    endswith = interp2app(W_UnicodeObject.descr_endswith,
                          doc=UnicodeDocstrings.endswith.__doc__),
    strip = interp2app(W_UnicodeObject.descr_strip,
                       doc=UnicodeDocstrings.strip.__doc__),
    lstrip = interp2app(W_UnicodeObject.descr_lstrip,
                        doc=UnicodeDocstrings.lstrip.__doc__),
    rstrip = interp2app(W_UnicodeObject.descr_rstrip,
                        doc=UnicodeDocstrings.rstrip.__doc__),
    swapcase = interp2app(W_UnicodeObject.descr_swapcase,
                          doc=UnicodeDocstrings.swapcase.__doc__),
    title = interp2app(W_UnicodeObject.descr_title,
                       doc=UnicodeDocstrings.title.__doc__),
    translate = interp2app(W_UnicodeObject.descr_translate,
                           doc=UnicodeDocstrings.translate.__doc__),
    upper = interp2app(W_UnicodeObject.descr_upper,
                       doc=UnicodeDocstrings.upper.__doc__),
    zfill = interp2app(W_UnicodeObject.descr_zfill,
                       doc=UnicodeDocstrings.zfill.__doc__),

    format = interp2app(W_UnicodeObject.descr_format,
                        doc=UnicodeDocstrings.format.__doc__),
    __format__ = interp2app(W_UnicodeObject.descr__format__,
                            doc=UnicodeDocstrings.__format__.__doc__),
    __mod__ = interp2app(W_UnicodeObject.descr_mod,
                         doc=UnicodeDocstrings.__mod__.__doc__),
    __rmod__ = interp2app(W_UnicodeObject.descr_rmod,
                         doc=UnicodeDocstrings.__rmod__.__doc__),
    __getnewargs__ = interp2app(W_UnicodeObject.descr_getnewargs,
                                doc=UnicodeDocstrings.__getnewargs__.__doc__),
    _formatter_parser = interp2app(W_UnicodeObject.descr_formatter_parser),
    _formatter_field_name_split =
        interp2app(W_UnicodeObject.descr_formatter_field_name_split),
)
W_UnicodeObject.typedef.flag_sequence_bug_compat = True


def _create_list_from_unicode(value):
    # need this helper function to allow the jit to look inside and inline
    # listview_unicode
    return [s for s in value]


W_UnicodeObject.EMPTY = W_UnicodeObject('', 0)


# Helper for converting int/long
def unicode_to_decimal_w(space, w_unistr):
    if not isinstance(w_unistr, W_UnicodeObject):
        raise oefmt(space.w_TypeError, "expected unicode, got '%T'", w_unistr)
    unistr = w_unistr._utf8.decode("utf8")
    # XXX speed up
    result = ['\0'] * len(unistr)
    digits = ['0', '1', '2', '3', '4',
              '5', '6', '7', '8', '9']
    for i in xrange(len(unistr)):
        uchr = ord(unistr[i])
        if unicodedb.isspace(uchr):
            result[i] = ' '
            continue
        try:
            result[i] = digits[unicodedb.decimal(uchr)]
        except KeyError:
            if 0 < uchr < 256:
                result[i] = chr(uchr)
            else:
                w_encoding = space.newtext('decimal')
                w_start = space.newint(i)
                w_end = space.newint(i+1)
                w_reason = space.newtext('invalid decimal Unicode string')
                raise OperationError(space.w_UnicodeEncodeError,
                                     space.newtuple([w_encoding, w_unistr,
                                                     w_start, w_end,
                                                     w_reason]))
    return ''.join(result)


_repr_function, _ = make_unicode_escape_function(
    pass_printable=False, unicode_output=False, quotes=True, prefix='u')
