"""The builtin unicode implementation"""

import sys

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
from pypy.module.unicodedata.interp_ucd import unicodedb
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

MAX_UNROLL_NEXT_CODEPOINT_POS = 4

@jit.elidable
def next_codepoint_pos_dont_look_inside(utf8, p):
    return rutf8.next_codepoint_pos(utf8, p)

@jit.elidable
def prev_codepoint_pos_dont_look_inside(utf8, p):
    return rutf8.prev_codepoint_pos(utf8, p)

@jit.elidable
def codepoint_at_pos_dont_look_inside(utf8, p):
    return rutf8.codepoint_at_pos(utf8, p)


class W_UnicodeObject(W_Root):
    import_from_mixin(StringMethods)
    _immutable_fields_ = ['_utf8']

    @enforceargs(utf8str=str)
    def __init__(self, utf8str, length):
        assert isinstance(utf8str, str)
        assert length >= 0
        self._utf8 = utf8str
        self._length = length
        self._index_storage = rutf8.null_storage()
        if not we_are_translated() and not sys.platform == 'win32':
            # utf8str must always be a valid utf8 string, except maybe with
            # explicit surrogate characters---which .decode('utf-8') doesn't
            # special-case in Python 2, which is exactly what we want here
            assert length == len(utf8str.decode('utf-8'))

    @staticmethod
    def from_utf8builder(builder):
        return W_UnicodeObject(
            builder.build(), builder.getlength())

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
        return space.text_w(encode_object(space, self, 'ascii', 'strict'))

    def utf8_w(self, space):
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

    def charbuf_w(self, space):
        # Returns ascii-encoded str
        return space.text_w(encode_object(space, self, 'ascii', 'strict'))

    def listview_ascii(self):
        if self.is_ascii():
            return _create_list_from_unicode(self._utf8)
        return None

    def ord(self, space):
        if self._len() != 1:
            raise oefmt(space.w_TypeError,
                         "ord() expected a character, but string of length %d "
                         "found", self._len())
        return space.newint(self.codepoint_at_pos_dont_look_inside(0))

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
        if space.is_w(space.type(w_other), space.w_unicode):
            # XXX why do we need this for translation???
            assert isinstance(w_other, W_UnicodeObject)
            return w_other
        if space.isinstance_w(w_other, space.w_bytes):
            return unicode_from_string(space, w_other)
        if strict:
            raise oefmt(space.w_TypeError,
                "%s arg must be None, unicode or str", strict)
        return unicode_from_encoded_object(space, w_other, 'utf8', "strict")

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

    @staticmethod
    def _isspace(ch):
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

    def _islinebreak(self, ch):
        return unicodedb.islinebreak(ch)

    @staticmethod
    def descr_new(space, w_unicodetype, w_string=None, w_encoding=None,
                  w_errors=None):
        encoding, errors = _get_encoding_and_errors(space, w_encoding,
                                                    w_errors)
        if w_string is None:
            w_value = W_UnicodeObject.EMPTY
        elif encoding is None and errors is None:
            # this is very quick if w_string is already a w_unicode
            w_value = unicode_from_object(space, w_string)
        else:
            if space.isinstance_w(w_string, space.w_unicode):
                raise oefmt(space.w_TypeError,
                            "decoding Unicode is not supported")
            w_value = unicode_from_encoded_object(space, w_string,
                                                  encoding, errors)
        if space.is_w(w_unicodetype, space.w_unicode):
            return w_value

        assert isinstance(w_value, W_UnicodeObject)
        w_newobj = space.allocate_instance(W_UnicodeObject, w_unicodetype)
        W_UnicodeObject.__init__(w_newobj, w_value._utf8, w_value._length)
        if w_value._index_storage:
            # copy the storage if it's there
            w_newobj._index_storage = w_value._index_storage
        return w_newobj

    def descr_repr(self, space):
        return space.newtext(_repr_function(self._utf8))

    def descr_str(self, space):
        return encode_object(space, self, 'ascii', 'strict')

    def hash_w(self):
        # shortcut for UnicodeDictStrategy
        x = compute_hash(self._utf8)
        x -= (x == -1) # convert -1 to -2 without creating a bridge
        return x

    def descr_hash(self, space):
        return space.newint(self.hash_w())

    def eq_w(self, w_other):
        # shortcut for UnicodeDictStrategy
        assert isinstance(w_other, W_UnicodeObject)
        return self._utf8 == w_other._utf8

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
        return formatter.format_string(self2)

    def descr_mod(self, space, w_values):
        return mod_format(space, self, w_values, do_unicode=True)

    def descr_rmod(self, space, w_values):
        return mod_format(space, w_values, self, do_unicode=True)

    def descr_swapcase(self, space):
        input = self._utf8
        builder = rutf8.Utf8StringBuilder(len(input))
        for ch in rutf8.Utf8StringIterator(input):
            if unicodedb.isupper(ch):
                ch = unicodedb.tolower(ch)
            elif unicodedb.islower(ch):
                ch = unicodedb.toupper(ch)
            builder.append_code(ch)
        return self.from_utf8builder(builder)

    def descr_title(self, space):
        if len(self._utf8) == 0:
            return self
        return self.title_unicode(self._utf8)

    @jit.elidable
    def title_unicode(self, value):
        input = self._utf8
        builder = rutf8.Utf8StringBuilder(len(input))
        previous_is_cased = False
        for ch0 in rutf8.Utf8StringIterator(input):
            if not previous_is_cased:
                ch1 = unicodedb.totitle(ch0)
            else:
                ch1 = unicodedb.tolower(ch0)
            builder.append_code(ch1)
            previous_is_cased = unicodedb.iscased(ch0)
        return self.from_utf8builder(builder)

    def descr_translate(self, space, w_table):
        builder = rutf8.Utf8StringBuilder(len(self._utf8))
        for codepoint in rutf8.Utf8StringIterator(self._utf8):
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
                    builder.append_utf8(w_newval._utf8, w_newval._length)
                    continue
                else:
                    raise oefmt(space.w_TypeError,
                                "character mapping must return integer, None "
                                "or unicode")
            try:
                builder.append_code(codepoint)
            except rutf8.OutOfRange:
                raise oefmt(space.w_TypeError,
                            "character mapping must be in range(0x110000)")
        return self.from_utf8builder(builder)

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
            return space.newbool(func(self.codepoint_at_pos_dont_look_inside(0)))
        else:
            return self._is_generic_loop(space, self._utf8, func_name)

    @specialize.arg(3)
    def _is_generic_loop(self, space, v, func_name):
        func = getattr(self, func_name)
        val = self._utf8
        for uchar in rutf8.Utf8StringIterator(val):
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

        return W_UnicodeObject(expanded, newlen)

    _StringMethods_descr_join = descr_join
    def descr_join(self, space, w_list):
        l = space.listview_ascii(w_list)
        if l is not None and self.is_ascii():
            if len(l) == 1:
                return space.newutf8(l[0], len(l[0]))
            s = self._utf8.join(l)
            return space.newutf8(s, len(s))
        return self._StringMethods_descr_join(space, w_list)

    def _join_return_one(self, space, w_obj):
        return space.is_w(space.type(w_obj), space.w_unicode)

    def descr_formatter_parser(self, space):
        from pypy.objspace.std.newformat import unicode_template_formatter
        tformat = unicode_template_formatter(space, space.utf8_w(self))
        return tformat.formatter_parser()

    def descr_formatter_field_name_split(self, space):
        from pypy.objspace.std.newformat import unicode_template_formatter
        tformat = unicode_template_formatter(space, space.utf8_w(self))
        return tformat.formatter_field_name_split()

    def descr_lower(self, space):
        builder = rutf8.Utf8StringBuilder(len(self._utf8))
        for ch in rutf8.Utf8StringIterator(self._utf8):
            lower = unicodedb.tolower(ch)
            builder.append_code(lower)
        return self.from_utf8builder(builder)

    def descr_isdecimal(self, space):
        return self._is_generic(space, '_isdecimal')

    def descr_isnumeric(self, space):
        return self._is_generic(space, '_isnumeric')

    def descr_islower(self, space):
        cased = False
        for uchar in rutf8.Utf8StringIterator(self._utf8):
            if (unicodedb.isupper(uchar) or
                unicodedb.istitle(uchar)):
                return space.w_False
            if not cased and unicodedb.islower(uchar):
                cased = True
        return space.newbool(cased)

    def descr_istitle(self, space):
        cased = False
        previous_is_cased = False
        for uchar in rutf8.Utf8StringIterator(self._utf8):
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
        for uchar in rutf8.Utf8StringIterator(self._utf8):
            if (unicodedb.islower(uchar) or
                unicodedb.istitle(uchar)):
                return space.w_False
            if not cased and unicodedb.isupper(uchar):
                cased = True
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
            if not (space.isinstance_w(w_s, space.w_bytes) or
                    space.isinstance_w(w_s, space.w_unicode)):
                raise oefmt(space.w_TypeError,
                            "sequence item %d: expected string or unicode, %T found",
                            i, w_s)
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
            while pos < length and not self._islinebreak(rutf8.codepoint_at_pos(value, pos)):
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
            strs_w.append(W_UnicodeObject(value[sol:eol], lgt))
        return space.newlist(strs_w)

    def descr_upper(self, space):
        builder = rutf8.Utf8StringBuilder(len(self._utf8))
        for ch in rutf8.Utf8StringIterator(self._utf8):
            ch = unicodedb.toupper(ch)
            builder.append_code(ch)
        return self.from_utf8builder(builder)

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
                if jit.we_are_jitted() and \
                        self._unroll_slice_heuristic(start, stop, w_index.w_stop):
                    return self._unicode_sliced_constant_index_jit(space, start, stop)
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
            builder.append_slice(self._utf8, byte_pos, next_pos)
            if i == sl - 1:
                break
            i += 1
            byte_pos = self._index_to_byte(start + i * step)
        return W_UnicodeObject(builder.build(), sl)

    def descr_getslice(self, space, w_start, w_stop):
        start, stop = normalize_simple_slice(
            space, self._len(), w_start, w_stop)
        if start == stop:
            return self._empty()
        else:
            if (jit.we_are_jitted() and
                    self._unroll_slice_heuristic(start, stop, w_stop)):
                return self._unicode_sliced_constant_index_jit(space, start, stop)
            return self._unicode_sliced(space, start, stop)

    def _unicode_sliced(self, space, start, stop):
        # XXX maybe some heuristic, like first slice does not create
        #     full index, but second does?
        assert start >= 0
        assert stop >= 0
        byte_start = self._index_to_byte(start)
        byte_stop = self._index_to_byte(stop)
        return W_UnicodeObject(self._utf8[byte_start:byte_stop], stop - start)

    @jit.unroll_safe
    def _unicode_sliced_constant_index_jit(self, space, start, stop):
        assert start >= 0
        assert stop >= 0
        byte_start = 0
        for i in range(start):
            byte_start = next_codepoint_pos_dont_look_inside(self._utf8, byte_start)
        byte_stop = len(self._utf8)
        for i in range(self._len() - stop):
            byte_stop = prev_codepoint_pos_dont_look_inside(self._utf8, byte_stop)
        return W_UnicodeObject(self._utf8[byte_start:byte_stop], stop - start)

    def _unroll_slice_heuristic(self, start, stop, w_stop):
        from pypy.objspace.std.intobject import W_IntObject
        # the reason we use the *wrapped* stop is that for
        # w_stop ==  wrapped -1, or w_None the stop that is computed will *not*
        # be constant, because the length is often not constant.
        return (not self.is_ascii() and
            jit.isconstant(start) and
            (jit.isconstant(w_stop) or
                (isinstance(w_stop, W_IntObject) and
                    jit.isconstant(w_stop.intval))) and
            start <= MAX_UNROLL_NEXT_CODEPOINT_POS and
            self._len() - stop <= MAX_UNROLL_NEXT_CODEPOINT_POS)

    def descr_capitalize(self, space):
        value = self._utf8
        if len(value) == 0:
            return self._empty()

        builder = rutf8.Utf8StringBuilder(len(self._utf8))
        it = rutf8.Utf8StringIterator(self._utf8)
        uchar = it.next()
        ch = unicodedb.toupper(uchar)
        builder.append_code(ch)
        for ch in it:
            ch = unicodedb.tolower(ch)
            builder.append_code(ch)
        return self.from_utf8builder(builder)

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
            lgt = rutf8.check_utf8(value, True, stop=pos)
            return space.newtuple(
                [W_UnicodeObject(value[0:pos], lgt), w_sub,
                 W_UnicodeObject(value[pos + len(sub._utf8):len(value)],
                    self._len() - lgt - sublen)])

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
            lgt = rutf8.check_utf8(value, True, stop=pos)
            return space.newtuple(
                [W_UnicodeObject(value[0:pos], lgt), w_sub,
                 W_UnicodeObject(value[pos + len(sub._utf8):len(value)],
                    self._len() - lgt - sublen)])

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

        newlength = self._length + replacements * (w_by._length - w_sub._length)
        return W_UnicodeObject(res, newlength)

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

    def _get_index_storage(self):
        return jit.conditional_call_elidable(self._index_storage,
                    W_UnicodeObject._compute_index_storage, self)

    def _compute_index_storage(self):
        storage = rutf8.create_utf8_index_storage(self._utf8, self._length)
        self._index_storage = storage
        return storage

    def _getitem_result(self, space, index):
        if (jit.we_are_jitted() and
                not self.is_ascii() and
                jit.isconstant(index) and
                -MAX_UNROLL_NEXT_CODEPOINT_POS <= index <= MAX_UNROLL_NEXT_CODEPOINT_POS):
            return self._getitem_result_constant_index_jit(space, index)
        if index < 0:
            index += self._length
        if index < 0 or index >= self._length:
            raise oefmt(space.w_IndexError, "string index out of range")
        start = self._index_to_byte(index)
        # we must not inline next_codepoint_pos, otherwise we produce a guard!
        end = self.next_codepoint_pos_dont_look_inside(start)
        return W_UnicodeObject(self._utf8[start:end], 1)

    @jit.unroll_safe
    def _getitem_result_constant_index_jit(self, space, index):
        # for small known indices, call next/prev_codepoint_pos a few times
        # instead of possibly creating an index structure
        if index < 0:
            posindex = index + self._length
            if posindex < 0:
                raise oefmt(space.w_IndexError, "string index out of range")
            end = len(self._utf8)
            start = self.prev_codepoint_pos_dont_look_inside(end)
            for i in range(-index-1):
                end = start
                start = self.prev_codepoint_pos_dont_look_inside(start)
        else:
            if index >= self._length:
                raise oefmt(space.w_IndexError, "string index out of range")
            start = 0
            end = self.next_codepoint_pos_dont_look_inside(start)
            for i in range(index):
                start = end
                end = self.next_codepoint_pos_dont_look_inside(end)
        assert start >= 0
        assert end >= 0
        return W_UnicodeObject(self._utf8[start:end], 1)

    def is_ascii(self):
        return self._length == len(self._utf8)

    def _index_to_byte(self, index):
        if self.is_ascii():
            assert index >= 0
            return index
        return rutf8.codepoint_position_at_index(
            self._utf8, self._get_index_storage(), index)

    def _codepoints_in_utf8(self, start, end):
        if self.is_ascii():
            return end - start
        return rutf8.codepoints_in_utf8(self._utf8, start, end)

    def _byte_to_index(self, bytepos):
        """ this returns index such that self._index_to_byte(index) == bytepos
        NB: this is slow! roughly logarithmic with a big constant
        """
        if self.is_ascii():
            return bytepos
        return rutf8.codepoint_index_at_byte_position(
            self._utf8, self._get_index_storage(), bytepos, self._len())

    def next_codepoint_pos_dont_look_inside(self, pos):
        if self.is_ascii():
            return pos + 1
        return next_codepoint_pos_dont_look_inside(self._utf8, pos)

    def prev_codepoint_pos_dont_look_inside(self, pos):
        if self.is_ascii():
            return pos - 1
        return prev_codepoint_pos_dont_look_inside(self._utf8, pos)

    def codepoint_at_pos_dont_look_inside(self, pos):
        if self.is_ascii():
            return ord(self._utf8[pos])
        return codepoint_at_pos_dont_look_inside(self._utf8, pos)

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
            res = self._byte_to_index(res_index)
            assert res >= 0
            return space.newint(res)
        else:
            res_index = self._utf8.rfind(w_sub._utf8, start_index, end_index)
            if res_index < 0:
                return None
            res = self._byte_to_index(res_index)
            assert res >= 0
            return space.newint(res)

    def _unwrap_and_compute_idx_params(self, space, w_start, w_end):
        # unwrap start and stop indices, optimized for the case where
        # start == 0 and end == self._length.  Note that 'start' and
        # 'end' are measured in codepoints whereas 'start_index' and
        # 'end_index' are measured in bytes.
        start, end = unwrap_start_stop(space, self._length, w_start, w_end)
        start_index = 0
        end_index = len(self._utf8) + 1
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
            while rpos > lpos:
                prev = rutf8.prev_codepoint_pos(value, rpos)
                if not rutf8.isspace(value, prev):
                    break
                rpos = prev
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
            while rpos > lpos:
                prev = rutf8.prev_codepoint_pos(value, rpos)
                if not rutf8.utf8_in_chars(value, prev, chars):
                    break
                rpos = prev
                lgt -= 1

        assert rpos >= lpos    # annotator hint, don't remove
        return self._utf8_sliced(lpos, rpos, lgt)

    def descr_getnewargs(self, space):
        return space.newtuple([W_UnicodeObject(self._utf8, self._length)])

    _starts_ends_unicode = True


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


def encode_object(space, w_obj, encoding, errors):
    from pypy.module._codecs.interp_codecs import encode
    if errors is None or errors == 'strict':
        # fast path
        if ((encoding is None and space.sys.defaultencoding == 'ascii') or
             encoding == 'ascii'):
            s = space.utf8_w(w_obj)
            try:
                rutf8.check_ascii(s)
            except rutf8.CheckError as a:
                if space.isinstance_w(w_obj, space.w_unicode):
                    eh = unicodehelper.encode_error_handler(space)
                else:
                    # must be a bytes-like object. In order to encode it,
                    # first "decode" to unicode. Since we cannot, raise a
                    # UnicodeDecodeError, not a UnicodeEncodeError
                    eh = unicodehelper.decode_error_handler(space)
                eh(None, "ascii", "ordinal not in range(128)", s,
                    a.pos, a.pos + 1)
                assert False, "always raises"
            return space.newbytes(s)
        if ((encoding is None and space.sys.defaultencoding == 'utf8') or
             encoding == 'utf-8' or encoding == 'utf8' or encoding == 'UTF-8'):
            utf8 = space.utf8_w(w_obj)
            if rutf8.has_surrogates(utf8):
                utf8 = rutf8.reencode_utf8_with_surrogates(utf8)
            return space.newbytes(utf8)
    return encode(space, w_obj, encoding, errors)


def decode_object(space, w_obj, encoding, errors):
    from pypy.module._codecs.interp_codecs import lookup_codec, decode
    if errors is None or errors == 'strict':
        # fast paths
        if encoding is None:
            encoding = getdefaultencoding(space)
        if encoding == 'ascii':
            s = space.charbuf_w(w_obj)
            unicodehelper.check_ascii_or_raise(space, s)
            return space.newutf8(s, len(s))
        if encoding == 'utf-8' or encoding == 'utf8':
            if (space.isinstance_w(w_obj, space.w_unicode) or
                space.isinstance_w(w_obj, space.w_bytes)):
                s = space.utf8_w(w_obj)
            else:
                s = space.charbuf_w(w_obj)
            lgt = unicodehelper.check_utf8_or_raise(space, s)
            return space.newutf8(s, lgt)
    if encoding is None:
        encoding = space.sys.defaultencoding
    return decode(space, w_obj, encoding, errors)

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
                return space.convert_arg_to_w_unicode(w_obj)
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
    # listview_ascii
    return [s for s in value]

W_UnicodeObject.EMPTY = W_UnicodeObject('', 0)


# Helper for converting int/long
def unicode_to_decimal_w(space, w_unistr):
    if not isinstance(w_unistr, W_UnicodeObject):
        raise oefmt(space.w_TypeError, "expected unicode, got '%T'", w_unistr)
    utf8 = w_unistr._utf8
    result = StringBuilder(w_unistr._len())
    it = rutf8.Utf8StringIterator(utf8)
    for uchr in it:
        if W_UnicodeObject._isspace(uchr):
            result.append(' ')
            continue
        if not (0 < uchr < 256):
            try:
                uchr = ord('0') + unicodedb.decimal(uchr)
            except KeyError:
                w_encoding = space.newtext('decimal')
                pos = it.get_pos()
                w_start = space.newint(pos)
                w_end = space.newint(pos + 1)
                w_reason = space.newtext('invalid decimal Unicode string')
                raise OperationError(space.w_UnicodeEncodeError,
                                        space.newtuple([w_encoding, w_unistr,
                                                        w_start, w_end,
                                                        w_reason]))
        result.append(chr(uchr))
    return result.build()


_repr_function = rutf8.make_utf8_escape_function(
    pass_printable=False, quotes=True, prefix='u')
