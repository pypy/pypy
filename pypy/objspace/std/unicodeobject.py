"""The builtin unicode implementation"""

from rpython.rlib.objectmodel import (
    compute_hash, compute_unique_id, import_from_mixin, always_inline,
    enforceargs, newlist_hint, specialize, we_are_translated)
from rpython.rlib.buffer import StringBuffer
from rpython.rlib.mutbuffer import MutableStringBuffer
from rpython.rlib.rarithmetic import ovfcheck
from rpython.rlib.rstring import (
    StringBuilder, split, rsplit, UnicodeBuilder, replace_count, startswith,
    endswith)
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
from pypy.objspace.std.sliceobject import (W_SliceObject,
    unwrap_start_stop, normalize_simple_slice)
from pypy.objspace.std.stringmethods import StringMethods
from pypy.objspace.std.util import IDTAG_SPECIAL, IDTAG_SHIFT

__all__ = ['W_UnicodeObject', 'wrapunicode', 'plain_str2unicode',
           'encode_object', 'decode_object', 'unicode_from_object',
           'unicode_from_string', 'unicode_to_decimal_w']


class W_UnicodeObject(W_Root):
    import_from_mixin(StringMethods)
    _immutable_fields_ = ['_utf8']

    @enforceargs(utf8str=str)
    def __init__(self, utf8str, length, flag):
        assert isinstance(utf8str, str)
        assert length >= 0
        self._utf8 = utf8str
        self._length = length
        if flag == rutf8.FLAG_ASCII:
            self._index_storage = rutf8.UTF8_IS_ASCII
        elif flag == rutf8.FLAG_HAS_SURROGATES:
            self._index_storage = rutf8.UTF8_HAS_SURROGATES
        else:
            assert flag == rutf8.FLAG_REGULAR
            self._index_storage = rutf8.null_storage()
        # XXX checking, remove before any performance measurments
        #     ifdef not_running_in_benchmark
        lgt, flag_check = rutf8.check_utf8(utf8str, True)
        assert lgt == length
        if flag_check == rutf8.FLAG_ASCII:
            # there are cases where we copy part of REULAR that happens
            # to be ascii
            assert flag in (rutf8.FLAG_ASCII, rutf8.FLAG_REGULAR)
        else:
            assert flag == flag_check
        # the storage can be one of:
        # - null, unicode with no surrogates
        # - rutf8.UTF8_HAS_SURROGATES
        # - rutf8.UTF8_IS_ASCII
        # - malloced object, which means it has index, then
        #   _index_storage.flags determines the kind

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

    def str_w(self, space):
        return space.text_w(space.str(self))

    def utf8_w(self, space):
        if self._has_surrogates():
            return rutf8.reencode_utf8_with_surrogates(self._utf8)
        return self._utf8

    def readbuf_w(self, space):
        # XXX for now
        from rpython.rlib.rstruct.unichar import pack_codepoint, UNICODE_SIZE
        builder = MutableStringBuffer(self._len() * UNICODE_SIZE)
        pos = 0
        i = 0
        while i < len(self._utf8):
            unich = rutf8.codepoint_at_pos(self._utf8, i)
            pack_codepoint(unich, builder, pos)
            pos += UNICODE_SIZE
            i = rutf8.next_codepoint_pos(self._utf8, i)
        return StringBuffer(builder.finish())

    def writebuf_w(self, space):
        raise oefmt(space.w_TypeError,
                    "cannot use unicode as modifiable buffer")

    charbuf_w = str_w

    def listview_utf8(self):
        assert self.is_ascii()
        return _create_list_from_unicode(self._utf8)

    def ord(self, space):
        if self._len() != 1:
            raise oefmt(space.w_TypeError,
                         "ord() expected a character, but string of length %d "
                         "found", self._len())
        return space.newint(rutf8.codepoint_at_pos(self._utf8, 0))

    def _empty(self):
        return W_UnicodeObject.EMPTY

    def _len(self):
        return self._length

    @staticmethod
    def _use_rstr_ops(space, w_other):
        # Always return true because we always need to copy the other
        # operand(s) before we can do comparisons
        return True

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
        return unicodedb.isupper(ch)

    def _islower(self, ch):
        return unicodedb.islower(ch)

    def _isnumeric(self, ch):
        return unicodedb.isnumeric(ch)

    def _istitle(self, ch):
        return unicodedb.isupper(ch) or unicodedb.istitle(ch)

    def _isspace(self, ch):
        return unicodedb.isspace(ch)

    def _isalpha(self, ch):
        return unicodedb.isalpha(ch)

    def _isalnum(self, ch):
        return unicodedb.isalnum(ch)

    def _isdigit(self, ch):
        return unicodedb.isdigit(ch)

    def _isdecimal(self, ch):
        return unicodedb.isdecimal(ch)

    def _iscased(self, ch):
        return unicodedb.iscased(ch)

    def _islinebreak(self, s, pos):
        return rutf8.islinebreak(s, pos)

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
        W_UnicodeObject.__init__(w_newobj, w_value._utf8, w_value._length,
                                 w_value._get_flag())
        if w_value._index_storage:
            # copy the storage if it's there
            w_newobj._index_storage = w_value._index_storage
        return w_newobj

    def descr_repr(self, space):
        return space.newtext(_repr_function(self._utf8))

    def descr_str(self, space):
        return encode_object(space, self, None, None)

    def descr_hash(self, space):
        x = compute_hash(self._utf8)
        x -= (x == -1) # convert -1 to -2 without creating a bridge
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
        spec = space.utf8_w(w_format_spec)
        formatter = newformat.unicode_formatter(space, spec)
        self2 = unicode_from_object(space, self)
        assert isinstance(self2, W_UnicodeObject)
        return formatter.format_string(self2._utf8)

    def descr_mod(self, space, w_values):
        return mod_format(space, self, w_values, do_unicode=True)

    def descr_rmod(self, space, w_values):
        return mod_format(space, w_values, self, do_unicode=True)

    def descr_swapcase(self, space):
        selfvalue = self._utf8
        builder = StringBuilder(len(selfvalue))
        flag = self._get_flag()
        i = 0
        while i < len(selfvalue):
            ch = rutf8.codepoint_at_pos(selfvalue, i)
            i = rutf8.next_codepoint_pos(selfvalue, i)
            if unicodedb.isupper(ch):
                ch = unicodedb.tolower(ch)
            elif unicodedb.islower(ch):
                ch = unicodedb.toupper(ch)
            if ch >= 0x80:
                flag = unicodehelper.combine_flags(flag, rutf8.FLAG_REGULAR)
            rutf8.unichr_as_utf8_append(builder, ch)
        return W_UnicodeObject(builder.build(), self._length, flag)

    def descr_title(self, space):
        if len(self._utf8) == 0:
            return self
        utf8, flag = self.title_unicode(self._utf8)
        return W_UnicodeObject(utf8, self._len(), flag)

    @jit.elidable
    def title_unicode(self, value):
        input = self._utf8
        builder = StringBuilder(len(input))
        i = 0
        previous_is_cased = False
        flag = self._get_flag()
        while i < len(input):
            ch = rutf8.codepoint_at_pos(input, i)
            i = rutf8.next_codepoint_pos(input, i)
            if not previous_is_cased:
                ch = unicodedb.totitle(ch)
            else:
                ch = unicodedb.tolower(ch)
            if ch >= 0x80:
                flag = unicodehelper.combine_flags(flag, rutf8.FLAG_REGULAR)
            rutf8.unichr_as_utf8_append(builder, ch)
            previous_is_cased = unicodedb.iscased(ch)
        return builder.build(), flag

    def descr_translate(self, space, w_table):
        input = self._utf8
        result = StringBuilder(len(input))
        result_length = 0
        flag = self._get_flag()
        i = 0
        while i < len(input):
            codepoint = rutf8.codepoint_at_pos(input, i)
            i = rutf8.next_codepoint_pos(input, i)
            try:
                w_newval = space.getitem(w_table, space.newint(codepoint))
            except OperationError as e:
                if not e.match(space, space.w_LookupError):
                    raise
            else:
                if space.is_w(w_newval, space.w_None):
                    continue
                elif space.isinstance_w(w_newval, space.w_int):
                    codepoint = space.int_w(w_newval)
                elif isinstance(w_newval, W_UnicodeObject):
                    result.append(w_newval._utf8)
                    flag = unicodehelper.combine_flags(flag, w_newval._get_flag())
                    result_length += w_newval._length
                    continue
                else:
                    raise oefmt(space.w_TypeError,
                                "character mapping must return integer, None "
                                "or unicode")
            try:
                if codepoint >= 0x80:
                    flag = unicodehelper.combine_flags(flag, rutf8.FLAG_REGULAR)
                rutf8.unichr_as_utf8_append(result, codepoint,
                                            allow_surrogates=True)
                result_length += 1
            except ValueError:
                raise oefmt(space.w_TypeError,
                            "character mapping must be in range(0x110000)")
        return W_UnicodeObject(result.build(), result_length, flag)

    def descr_find(self, space, w_sub, w_start=None, w_end=None):
        w_result = self._unwrap_and_search(space, w_sub, w_start, w_end)
        if w_result is None:
            w_result = space.newint(-1)
        return w_result

    def descr_rfind(self, space, w_sub, w_start=None, w_end=None):
        w_result = self._unwrap_and_search(space, w_sub, w_start, w_end,
                                           forward=False)
        if w_result is None:
            w_result = space.newint(-1)
        return w_result

    def descr_index(self, space, w_sub, w_start=None, w_end=None):
        w_result = self._unwrap_and_search(space, w_sub, w_start, w_end)
        if w_result is None:
            raise oefmt(space.w_ValueError,
                        "substring not found in string.index")
        return w_result

    def descr_rindex(self, space, w_sub, w_start=None, w_end=None):
        w_result = self._unwrap_and_search(space, w_sub, w_start, w_end,
                                           forward=False)
        if w_result is None:
            raise oefmt(space.w_ValueError,
                        "substring not found in string.rindex")
        return w_result

    @specialize.arg(2)
    def _is_generic(self, space, func_name):
        func = getattr(self, func_name)
        if self._length == 0:
            return space.w_False
        if self._length == 1:
            return space.newbool(func(rutf8.codepoint_at_pos(self._utf8, 0)))
        else:
            return self._is_generic_loop(space, self._utf8, func_name)

    @specialize.arg(3)
    def _is_generic_loop(self, space, v, func_name):
        func = getattr(self, func_name)
        val = self._utf8
        i = 0
        while i < len(val):
            uchar = rutf8.codepoint_at_pos(val, i)
            i = rutf8.next_codepoint_pos(val, i)
            if not func(uchar):
                return space.w_False
        return space.w_True

    def descr_encode(self, space, w_encoding=None, w_errors=None):
        encoding, errors = _get_encoding_and_errors(space, w_encoding,
                                                    w_errors)
        return encode_object(space, self, encoding, errors)

    @unwrap_spec(tabsize=int)
    def descr_expandtabs(self, space, tabsize=8):
        value = self._utf8
        if not value:
            return self._empty()

        splitted = value.split('\t')

        try:
            if tabsize > 0:
                ovfcheck(len(splitted) * tabsize)
        except OverflowError:
            raise oefmt(space.w_OverflowError, "new string is too long")
        expanded = oldtoken = splitted.pop(0)
        newlen = self._len() - len(splitted)

        for token in splitted:
            dist = self._tabindent(oldtoken, tabsize)
            expanded += ' ' * dist + token
            newlen += dist
            oldtoken = token

        return W_UnicodeObject(expanded, newlen, self._get_flag())

    _StringMethods_descr_join = descr_join
    def descr_join(self, space, w_list):
        l = space.listview_utf8(w_list)
        if l is not None and self.is_ascii():
            if len(l) == 1:
                return space.newutf8(l[0], len(l[0]), rutf8.FLAG_ASCII)
            s = self._utf8.join(l)
            return space.newutf8(s, len(s), rutf8.FLAG_ASCII)
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
        tformat = unicode_template_formatter(space, space.utf8_w(self))
        return tformat.formatter_parser()

    def descr_formatter_field_name_split(self, space):
        from pypy.objspace.std.newformat import unicode_template_formatter
        tformat = unicode_template_formatter(space, space.utf8_w(self))
        return tformat.formatter_field_name_split()

    def descr_lower(self, space):
        builder = StringBuilder(len(self._utf8))
        pos = 0
        flag = self._get_flag()
        while pos < len(self._utf8):
            lower = unicodedb.tolower(rutf8.codepoint_at_pos(self._utf8, pos))
            if lower >= 0x80:
                flag = unicodehelper.combine_flags(flag, rutf8.FLAG_REGULAR)
            rutf8.unichr_as_utf8_append(builder, lower) # XXX allow surrogates?
            pos = rutf8.next_codepoint_pos(self._utf8, pos)
        return W_UnicodeObject(builder.build(), self._len(), flag)

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

    def descr_istitle(self, space):
        cased = False
        previous_is_cased = False
        val = self._utf8
        i = 0
        while i < len(val):
            uchar = rutf8.codepoint_at_pos(val, i)
            i = rutf8.next_codepoint_pos(val, i)
            if unicodedb.isupper(uchar) or unicodedb.istitle(uchar):
                if previous_is_cased:
                    return space.w_False
                previous_is_cased = True
                cased = True
            elif unicodedb.islower(uchar):
                if not previous_is_cased:
                    return space.w_False
                cased = True
            else:
                previous_is_cased = False
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

    def descr_startswith(self, space, w_prefix, w_start=None, w_end=None):
        start, end = self._unwrap_and_compute_idx_params(space, w_start, w_end)
        value = self._utf8
        if space.isinstance_w(w_prefix, space.w_tuple):
            return self._startswith_tuple(space, value, w_prefix, start, end)
        return space.newbool(self._startswith(space, value, w_prefix, start,
                                              end))

    def _startswith(self, space, value, w_prefix, start, end):
        prefix = self.convert_arg_to_w_unicode(space, w_prefix)._utf8
        if len(prefix) == 0:
            return True
        return startswith(value, prefix, start, end)

    def descr_endswith(self, space, w_suffix, w_start=None, w_end=None):
        start, end = self._unwrap_and_compute_idx_params(space, w_start, w_end)
        value = self._utf8
        if space.isinstance_w(w_suffix, space.w_tuple):
            return self._endswith_tuple(space, value, w_suffix, start, end)
        return space.newbool(self._endswith(space, value, w_suffix, start,
                                            end))

    def _endswith(self, space, value, w_prefix, start, end):
        prefix = self.convert_arg_to_w_unicode(space, w_prefix)._utf8
        if len(prefix) == 0:
            return True
        return endswith(value, prefix, start, end)

    def _get_flag(self):
        if self.is_ascii():
            return rutf8.FLAG_ASCII
        elif self._has_surrogates():
            return rutf8.FLAG_HAS_SURROGATES
        return rutf8.FLAG_REGULAR

    def descr_add(self, space, w_other):
        try:
            w_other = self.convert_arg_to_w_unicode(space, w_other)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise
        flag = unicodehelper.combine_flags(self._get_flag(), w_other._get_flag())
        return W_UnicodeObject(self._utf8 + w_other._utf8,
                               self._len() + w_other._len(), flag)

    @jit.look_inside_iff(lambda self, space, list_w, size:
                         jit.loop_unrolling_heuristic(list_w, size))
    def _str_join_many_items(self, space, list_w, size):
        value = self._utf8
        lgt = self._len() * (size - 1)

        prealloc_size = len(value) * (size - 1)
        unwrapped = newlist_hint(size)
        flag = self._get_flag()
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
            flag = unicodehelper.combine_flags(flag, w_u._get_flag())
            unwrapped.append(w_u._utf8)
            lgt += w_u._length
            prealloc_size += len(unwrapped[i])

        sb = StringBuilder(prealloc_size)
        for i in range(size):
            if value and i != 0:
                sb.append(value)
            sb.append(unwrapped[i])
        return W_UnicodeObject(sb.build(), lgt, flag)

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
                # read CRLF as one line break
                if (value[pos] == '\r' and pos + 1 < length
                                       and value[pos + 1] == '\n'):
                    pos += 2
                    line_end_chars = 2
                else:
                    pos = rutf8.next_codepoint_pos(value, pos)
                    line_end_chars = 1
                if keepends:
                    eol = pos
                    lgt += line_end_chars
            assert eol >= 0
            assert sol >= 0
            # XXX we can do better with flags here, if we want to
            strs_w.append(W_UnicodeObject(value[sol:eol], lgt, self._get_flag()))
        return space.newlist(strs_w)

    def descr_upper(self, space):
        value = self._utf8
        builder = StringBuilder(len(value))
        flag = self._get_flag()
        i = 0
        while i < len(value):
            uchar = rutf8.codepoint_at_pos(value, i)
            uchar = unicodedb.toupper(uchar)
            if uchar >= 0x80:
                flag = unicodehelper.combine_flags(flag, rutf8.FLAG_REGULAR)
            i = rutf8.next_codepoint_pos(value, i)
            rutf8.unichr_as_utf8_append(builder, uchar)
        return W_UnicodeObject(builder.build(), self._length, flag)

    @unwrap_spec(width=int)
    def descr_zfill(self, space, width):
        selfval = self._utf8
        if len(selfval) == 0:
            return W_UnicodeObject('0' * width, width, rutf8.FLAG_ASCII)
        num_zeros = width - self._len()
        if num_zeros <= 0:
            # cannot return self, in case it is a subclass of str
            return W_UnicodeObject(selfval, self._len(), self._get_flag())
        builder = StringBuilder(num_zeros + len(selfval))
        if len(selfval) > 0 and (selfval[0] == '+' or selfval[0] == '-'):
            # copy sign to first position
            builder.append(selfval[0])
            start = 1
        else:
            start = 0
        builder.append_multiple_char('0', num_zeros)
        builder.append_slice(selfval, start, len(selfval))
        return W_UnicodeObject(builder.build(), width, self._get_flag())

    @unwrap_spec(maxsplit=int)
    def descr_split(self, space, w_sep=None, maxsplit=-1):
        res = []
        value = self._utf8
        if space.is_none(w_sep):
            res = split(value, maxsplit=maxsplit, isutf8=True)
            return space.newlist_utf8(res, self.is_ascii())

        by = self.convert_arg_to_w_unicode(space, w_sep)._utf8
        if len(by) == 0:
            raise oefmt(space.w_ValueError, "empty separator")
        res = split(value, by, maxsplit, isutf8=True)

        return space.newlist_utf8(res, self.is_ascii())

    @unwrap_spec(maxsplit=int)
    def descr_rsplit(self, space, w_sep=None, maxsplit=-1):
        res = []
        value = self._utf8
        if space.is_none(w_sep):
            res = rsplit(value, maxsplit=maxsplit, isutf8=True)
            return space.newlist_utf8(res, self.is_ascii())

        by = self.convert_arg_to_w_unicode(space, w_sep)._utf8
        if len(by) == 0:
            raise oefmt(space.w_ValueError, "empty separator")
        res = rsplit(value, by, maxsplit, isutf8=True)

        return space.newlist_utf8(res, self.is_ascii())

    def descr_getitem(self, space, w_index):
        if isinstance(w_index, W_SliceObject):
            length = self._len()
            start, stop, step, sl = w_index.indices4(space, length)
            if sl == 0:
                return self._empty()
            elif step == 1:
                assert start >= 0 and stop >= 0
                return self._unicode_sliced(space, start, stop)
            else:
                return self._getitem_slice_slowpath(space, start, step, sl)

        index = space.getindex_w(w_index, space.w_IndexError, "string index")
        return self._getitem_result(space, index)

    def _getitem_slice_slowpath(self, space, start, step, sl):
        # XXX same comment as in _unicode_sliced
        builder = StringBuilder(step * sl)
        byte_pos = self._index_to_byte(start)
        i = 0
        while True:
            next_pos = rutf8.next_codepoint_pos(self._utf8, byte_pos)
            builder.append(self._utf8[byte_pos:next_pos])
            if i == sl - 1:
                break
            i += 1
            byte_pos = self._index_to_byte(start + i * step)
        return W_UnicodeObject(builder.build(), sl, self._get_flag())

    def descr_getslice(self, space, w_start, w_stop):
        start, stop = normalize_simple_slice(
            space, self._len(), w_start, w_stop)
        if start == stop:
            return self._empty()
        else:
            return self._unicode_sliced(space, start, stop)

    def _unicode_sliced(self, space, start, stop):
        # XXX maybe some heuristic, like first slice does not create
        #     full index, but second does?
        assert start >= 0
        assert stop >= 0
        byte_start = self._index_to_byte(start)
        byte_stop = self._index_to_byte(stop)
        return W_UnicodeObject(self._utf8[byte_start:byte_stop], stop - start,
                               self._get_flag())

    def descr_capitalize(self, space):
        value = self._utf8
        if len(value) == 0:
            return self._empty()

        flag = self._get_flag()
        builder = StringBuilder(len(value))
        uchar = rutf8.codepoint_at_pos(value, 0)
        i = rutf8.next_codepoint_pos(value, 0)
        ch = unicodedb.toupper(uchar)
        rutf8.unichr_as_utf8_append(builder, ch)
        if ch >= 0x80:
            flag = unicodehelper.combine_flags(flag, rutf8.FLAG_REGULAR)
        while i < len(value):
            uchar = rutf8.codepoint_at_pos(value, i)
            i = rutf8.next_codepoint_pos(value, i)
            ch = unicodedb.tolower(uchar)
            rutf8.unichr_as_utf8_append(builder, ch)
            if ch >= 0x80:
                flag = unicodehelper.combine_flags(flag, rutf8.FLAG_REGULAR)
        return W_UnicodeObject(builder.build(), self._len(), flag)

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

        return W_UnicodeObject(centered, self._len() + d, self._get_flag())

    def descr_count(self, space, w_sub, w_start=None, w_end=None):
        value = self._utf8
        start_index, end_index = self._unwrap_and_compute_idx_params(
            space, w_start, w_end)
        sub = self.convert_arg_to_w_unicode(space, w_sub)._utf8
        return space.newint(value.count(sub, start_index, end_index))

    def descr_contains(self, space, w_sub):
        value = self._utf8
        w_other = self.convert_arg_to_w_unicode(space, w_sub)
        return space.newbool(value.find(w_other._utf8) >= 0)

    def descr_partition(self, space, w_sub):
        value = self._utf8
        sub = self.convert_arg_to_w_unicode(space, w_sub)
        sublen = sub._len()
        if sublen == 0:
            raise oefmt(space.w_ValueError, "empty separator")

        pos = value.find(sub._utf8)

        if pos < 0:
            return space.newtuple([self, self._empty(), self._empty()])
        else:
            lgt, _ = rutf8.check_utf8(value, True, stop=pos)
            return space.newtuple(
                [W_UnicodeObject(value[0:pos], lgt, self._get_flag()), w_sub,
                 W_UnicodeObject(value[pos + len(sub._utf8):len(value)],
                    self._len() - lgt - sublen, self._get_flag())])

    def descr_rpartition(self, space, w_sub):
        value = self._utf8
        sub = self.convert_arg_to_w_unicode(space, w_sub)
        sublen = sub._len()
        if sublen == 0:
            raise oefmt(space.w_ValueError, "empty separator")

        pos = value.rfind(sub._utf8)

        if pos < 0:
            return space.newtuple([self._empty(), self._empty(), self])
        else:
            lgt, _ = rutf8.check_utf8(value, True, stop=pos)
            return space.newtuple(
                [W_UnicodeObject(value[0:pos], lgt, self._get_flag()), w_sub,
                 W_UnicodeObject(value[pos + len(sub._utf8):len(value)],
                    self._len() - lgt - sublen, self._get_flag())])

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
            res, replacements = replace_count(input, w_sub._utf8, w_by._utf8,
                                              count, isutf8=True)
        except OverflowError:
            raise oefmt(space.w_OverflowError, "replace string is too long")

        flag = unicodehelper.combine_flags(self._get_flag(), w_by._get_flag())
        newlength = self._length + replacements * (w_by._length - w_sub._length)
        return W_UnicodeObject(res, newlength, flag)

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
            return W_UnicodeObject(self._utf8[0] * times, times,
                                   self._get_flag())
        return W_UnicodeObject(self._utf8 * times, times * self._len(),
                               self._get_flag())

    descr_rmul = descr_mul

    def _get_index_storage(self):
        # XXX write the correct jit.elidable
        condition = (self._index_storage == rutf8.null_storage() or
                     not bool(self._index_storage.contents))
        if condition:
            storage = rutf8.create_utf8_index_storage(self._utf8, self._length)
        else:
            storage = self._index_storage
        if not jit.isconstant(self):
            prev_storage = self._index_storage
            self._index_storage = storage
            if prev_storage == rutf8.UTF8_HAS_SURROGATES:
                flag = rutf8.FLAG_HAS_SURROGATES
            else:
                flag = rutf8.FLAG_REGULAR
            self._index_storage.flag = flag
        return storage

    def _getitem_result(self, space, index):
        if index < 0:
            index += self._length
        if index < 0 or index >= self._length:
            raise oefmt(space.w_IndexError, "string index out of range")
        start = self._index_to_byte(index)
        end = rutf8.next_codepoint_pos(self._utf8, start)
        return W_UnicodeObject(self._utf8[start:end], 1, self._get_flag())

    def is_ascii(self):
        return self._index_storage is rutf8.UTF8_IS_ASCII

    def _has_surrogates(self):
        return (self._index_storage is rutf8.UTF8_HAS_SURROGATES or
                (bool(self._index_storage) and
                 self._index_storage.flag == rutf8.FLAG_HAS_SURROGATES))

    def _index_to_byte(self, index):
        if self.is_ascii():
            assert index >= 0
            return index
        return rutf8.codepoint_position_at_index(
            self._utf8, self._get_index_storage(), index)

    @always_inline
    def _unwrap_and_search(self, space, w_sub, w_start, w_end, forward=True):
        w_sub = self.convert_arg_to_w_unicode(space, w_sub)
        start, end = unwrap_start_stop(space, self._length, w_start, w_end)
        if start == 0:
            start_index = 0
        elif start > self._length:
            return None
        else:
            start_index = self._index_to_byte(start)

        if end >= self._length:
            end = self._length
            end_index = len(self._utf8)
        else:
            end_index = self._index_to_byte(end)

        if forward:
            res_index = self._utf8.find(w_sub._utf8, start_index, end_index)
            if res_index < 0:
                return None
            skip = rutf8.codepoints_in_utf8(self._utf8, start_index, res_index)
            res = start + skip
            assert res >= 0
            return space.newint(res)
        else:
            res_index = self._utf8.rfind(w_sub._utf8, start_index, end_index)
            if res_index < 0:
                return None
            skip = rutf8.codepoints_in_utf8(self._utf8, res_index, end_index)
            res = end - skip
            assert res >= 0
            return space.newint(res)

    def _unwrap_and_compute_idx_params(self, space, w_start, w_end):
        # unwrap start and stop indices, optimized for the case where
        # start == 0 and end == self._length.  Note that 'start' and
        # 'end' are measured in codepoints whereas 'start_index' and
        # 'end_index' are measured in bytes.
        start, end = unwrap_start_stop(space, self._length, w_start, w_end)
        start_index = 0
        end_index = len(self._utf8)
        if start > 0:
            if start > self._length:
                start_index = end_index
            else:
                start_index = self._index_to_byte(start)
        if end < self._length:
            end_index = self._index_to_byte(end)
        return (start_index, end_index)

    @unwrap_spec(width=int, w_fillchar=WrappedDefault(' '))
    def descr_rjust(self, space, width, w_fillchar):
        value = self._utf8
        lgt = self._len()
        w_fillchar = self.convert_arg_to_w_unicode(space, w_fillchar)
        if w_fillchar._len() != 1:
            raise oefmt(space.w_TypeError,
                        "rjust() argument 2 must be a single character")
        flag = unicodehelper.combine_flags(self._get_flag(), w_fillchar._get_flag())
        d = width - lgt
        if d > 0:
            if len(w_fillchar._utf8) == 1:
                # speedup
                value = d * w_fillchar._utf8[0] + value
            else:
                value = d * w_fillchar._utf8 + value
            return W_UnicodeObject(value, width, flag)

        return W_UnicodeObject(value, lgt, flag)

    @unwrap_spec(width=int, w_fillchar=WrappedDefault(' '))
    def descr_ljust(self, space, width, w_fillchar):
        value = self._utf8
        w_fillchar = self.convert_arg_to_w_unicode(space, w_fillchar)
        if w_fillchar._len() != 1:
            raise oefmt(space.w_TypeError,
                        "ljust() argument 2 must be a single character")
        flag = unicodehelper.combine_flags(self._get_flag(), w_fillchar._get_flag())
        d = width - self._len()
        if d > 0:
            if len(w_fillchar._utf8) == 1:
                # speedup
                value = value + d * w_fillchar._utf8[0]
            else:
                value = value + d * w_fillchar._utf8
            return W_UnicodeObject(value, width, flag)

        return W_UnicodeObject(value, self._len(), flag)

    def _utf8_sliced(self, start, stop, lgt):
        assert start >= 0
        assert stop >= 0
        #if start == 0 and stop == len(s) and space.is_w(space.type(orig_obj),
        #                                                space.w_bytes):
        #    return orig_obj
        return W_UnicodeObject(self._utf8[start:stop], lgt, self._get_flag())

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

    def descr_getnewargs(self, space):
        return space.newtuple([W_UnicodeObject(self._utf8, self._length, self._get_flag())])



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
    w_encoder = None
    if encoding is None:
        # Get the encoder functions as a wrapped object.
        # This lookup is cached.
        w_encoder = space.sys.get_w_default_encoder()
    if errors is None or errors == 'strict':
        if ((encoding is None and space.sys.defaultencoding == 'ascii') or
             encoding == 'ascii'):
            s = space.utf8_w(w_object)
            try:
                rutf8.check_ascii(s)
            except rutf8.CheckError as a:
                eh = unicodehelper.encode_error_handler(space)
                eh(None, "ascii", "ordinal not in range(128)", s,
                    a.pos, a.pos + 1)
                assert False, "always raises"
            return space.newbytes(s)
        if ((encoding is None and space.sys.defaultencoding == 'utf8') or
             encoding == 'utf-8' or encoding == 'utf8' or encoding == 'UTF-8'):
            return space.newbytes(space.utf8_w(w_object))
    if w_encoder is None:
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
            s = space.charbuf_w(w_obj)
            unicodehelper.check_ascii_or_raise(space, s)
            return space.newutf8(s, len(s), rutf8.FLAG_ASCII)
        if encoding == 'utf-8':
            s = space.charbuf_w(w_obj)
            lgt, flag = unicodehelper.check_utf8_or_raise(space, s)
            return space.newutf8(s, lgt, flag)
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
                return unicodehelper.convert_arg_to_w_unicode(space, w_obj)
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
    unicodehelper.check_ascii_or_raise(space, s)
    return W_UnicodeObject(s, len(s), rutf8.FLAG_ASCII)


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


W_UnicodeObject.EMPTY = W_UnicodeObject('', 0, rutf8.FLAG_ASCII)


# Helper for converting int/long
def unicode_to_decimal_w(space, w_unistr):
    if not isinstance(w_unistr, W_UnicodeObject):
        raise oefmt(space.w_TypeError, "expected unicode, got '%T'", w_unistr)
    unistr = w_unistr._utf8
    result = ['\0'] * w_unistr._length
    digits = ['0', '1', '2', '3', '4',
              '5', '6', '7', '8', '9']
    i = 0
    res_pos = 0
    while i < len(unistr):
        uchr = rutf8.codepoint_at_pos(unistr, i)
        if rutf8.isspace(unistr, i):
            result[res_pos] = ' '
            res_pos += 1
            i = rutf8.next_codepoint_pos(unistr, i)
            continue
        try:
            result[res_pos] = digits[unicodedb.decimal(uchr)]
        except KeyError:
            if 0 < uchr < 256:
                result[res_pos] = chr(uchr)
            else:
                w_encoding = space.newtext('decimal')
                w_start = space.newint(i)
                w_end = space.newint(i+1)
                w_reason = space.newtext('invalid decimal Unicode string')
                raise OperationError(space.w_UnicodeEncodeError,
                                     space.newtuple([w_encoding, w_unistr,
                                                     w_start, w_end,
                                                     w_reason]))
        i = rutf8.next_codepoint_pos(unistr, i)
        res_pos += 1
    return ''.join(result)


_repr_function = rutf8.make_utf8_escape_function(
    pass_printable=False, quotes=True, prefix='u')
