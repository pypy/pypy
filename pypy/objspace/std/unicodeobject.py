"""The builtin str implementation"""

from rpython.rlib.objectmodel import (
    compute_hash, compute_unique_id, import_from_mixin, always_inline,
    enforceargs, newlist_hint, specialize, we_are_translated)
from rpython.rlib.rarithmetic import ovfcheck
from rpython.rlib.rstring import (
    StringBuilder, split, rsplit, UnicodeBuilder, replace_count, startswith,
    endswith)
from rpython.rlib.runicode import (
    unicode_encode_utf8_forbid_surrogates, SurrogateError)
from rpython.rlib import rutf8, jit

from pypy.interpreter import unicodehelper
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import WrappedDefault, interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef
from pypy.module.unicodedata import unicodedb
from pypy.objspace.std import newformat
from pypy.objspace.std.formatting import mod_format, FORMAT_UNICODE
from pypy.objspace.std.sliceobject import (W_SliceObject,
    unwrap_start_stop, normalize_simple_slice)
from pypy.objspace.std.stringmethods import StringMethods
from pypy.objspace.std.util import IDTAG_SPECIAL, IDTAG_SHIFT

__all__ = ['W_UnicodeObject', 'encode_object', 'decode_object',
           'unicode_from_object', 'unicode_to_decimal_w']


class W_UnicodeObject(W_Root):
    import_from_mixin(StringMethods)
    _immutable_fields_ = ['_utf8', '_length']

    @enforceargs(utf8str=str)
    def __init__(self, utf8str, length):
        assert isinstance(utf8str, bytes)
        # TODO: how to handle surrogates
        assert length >= 0
        self._utf8 = utf8str
        self._length = length
        self._index_storage = rutf8.null_storage()
        # XXX checking, remove before any performance measurments
        #     ifdef not_running_in_benchmark
        if not we_are_translated():
            lgt = rutf8.codepoints_in_utf8(utf8str)
            assert lgt == length

    @staticmethod
    def from_utf8builder(builder):
        return W_UnicodeObject(
            builder.build(), builder.getlength())

    def __repr__(self):
        """representation for debugging purposes"""
        return "%s(%r)" % (self.__class__.__name__, self._utf8)

    def unwrap(self, space):
        # for testing
        return space.realunicode_w(self)

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

    def text_w(self, space):
        return self._utf8

    def utf8_w(self, space):
        return self._utf8

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
            raise oefmt(space.w_TypeError,
                    "Can't convert '%T' object to str implicitly", w_other)
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

    def _generic_name(self):
        return "str"

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
    def descr_new(space, w_unicodetype, w_object=None, w_encoding=None,
                  w_errors=None):
        if w_object is None:
            w_value = W_UnicodeObject.EMPTY
        else:
            encoding, errors = _get_encoding_and_errors(space, w_encoding,
                                                        w_errors)
            if encoding is None and errors is None:
                w_value = unicode_from_object(space, w_object)
            else:
                w_value = unicode_from_encoded_object(space, w_object,
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

    @staticmethod
    def descr_maketrans(space, w_type, w_x, w_y=None, w_z=None):
        y = None if space.is_none(w_y) else space.utf8_w(w_y)
        z = None if space.is_none(w_z) else space.utf8_w(w_z)
        w_new = space.newdict()

        if y is not None:
            # x must be a string too, of equal length
            ylen = len(y)
            try:
                x = space.utf8_w(w_x)
            except OperationError as e:
                if not e.match(space, space.w_TypeError):
                    raise
                raise oefmt(space.w_TypeError,
                            "first maketrans argument must be a string if "
                            "there is a second argument")
            if len(x) != ylen:
                raise oefmt(space.w_ValueError,
                            "the first two maketrans arguments must have "
                            "equal length")
            # create entries for translating chars in x to those in y
            for i in range(len(x)):
                w_key = space.newint(ord(x[i]))
                w_value = space.newint(ord(y[i]))
                space.setitem(w_new, w_key, w_value)
            # create entries for deleting chars in z
            if z is not None:
                for i in range(len(z)):
                    w_key = space.newint(ord(z[i]))
                    space.setitem(w_new, w_key, space.w_None)
        else:
            # x must be a dict
            if not space.is_w(space.type(w_x), space.w_dict):
                raise oefmt(space.w_TypeError,
                            "if you give only one argument to maketrans it "
                            "must be a dict")
            # copy entries into the new dict, converting string keys to int keys
            w_iter = space.iter(space.call_method(w_x, "items"))
            while True:
                try:
                    w_item = space.next(w_iter)
                except OperationError as e:
                    if not e.match(space, space.w_StopIteration):
                        raise
                    break
                w_key, w_value = space.unpackiterable(w_item, 2)
                if space.isinstance_w(w_key, space.w_unicode):
                    # convert string keys to integer keys
                    key = space.utf8_w(w_key)
                    if len(key) != 1:
                        raise oefmt(space.w_ValueError,
                                    "string keys in translate table must be "
                                    "of length 1")
                    w_key = space.newint(ord(key[0]))
                else:
                    # just keep integer keys
                    try:
                        space.int_w(w_key)
                    except OperationError as e:
                        if not e.match(space, space.w_TypeError):
                            raise
                        raise oefmt(space.w_TypeError,
                                    "keys in translate table must be strings "
                                    "or integers")
                space.setitem(w_new, w_key, w_value)
        return w_new

    def descr_repr(self, space):
        return space.newtext(_repr_function(self._utf8)) # quotes=True

    def descr_str(self, space):
        if space.is_w(space.type(self), space.w_unicode):
            return self
        # Subtype -- return genuine unicode string with the same value.
        return space.newtext(space.utf8_w(self), space.len_w(self))

    def descr_hash(self, space):
        x = compute_hash(self._utf8)
        x -= (x == -1) # convert -1 to -2 without creating a bridge
        return space.newint(x)

    def descr_eq(self, space, w_other):
        try:
            res = self._utf8 == self.convert_arg_to_w_unicode(space, w_other,
                                                        strict='__eq__')._utf8
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise
        return space.newbool(res)

    def descr_ne(self, space, w_other):
        try:
            res = self._utf8 != self.convert_arg_to_w_unicode(space, w_other,
                                                     strict='__neq__')._utf8
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
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

    def _parse_format_arg(self, space, w_kwds, __args__):
        for i in range(len(__args__.keywords)):
            try:     # pff
                arg = __args__.keywords[i]
            except UnicodeDecodeError:
                continue   # uh, just skip that
            space.setitem(w_kwds, space.newtext(arg),
                          __args__.keywords_w[i])

    def descr_format(self, space, __args__):
        w_kwds = space.newdict()
        if __args__.keywords:
            self._parse_format_arg(space, w_kwds, __args__)
        return newformat.format_method(space, self, __args__.arguments_w,
                                       w_kwds, True)

    def descr_format_map(self, space, w_mapping):
        return newformat.format_method(space, self, None, w_mapping, True)

    def descr__format__(self, space, w_format_spec):
        return newformat.run_formatter(space, w_format_spec, "format_string",
                                       self)

    def descr_mod(self, space, w_values):
        return mod_format(space, self, w_values, fmt_type=FORMAT_UNICODE)

    def descr_rmod(self, space, w_values):
        return mod_format(space, w_values, self, fmt_type=FORMAT_UNICODE)

    def descr_swapcase(self, space):
        value = self._utf8
        builder = rutf8.Utf8StringBuilder(len(value))
        for ch in rutf8.Utf8StringIterator(value):
            if unicodedb.isupper(ch):
                codes = unicodedb.tolower_full(ch)
            elif unicodedb.islower(ch):
                codes = unicodedb.toupper_full(ch)
            else:
                codes = [ch,]
            for c in codes:
                builder.append_code(c)
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
        i = 0
        for ch in rutf8.Utf8StringIterator(input):
            if ch == 0x3a3:
                codes = [self._handle_capital_sigma(input, i),]
            elif not previous_is_cased:
                codes = unicodedb.totitle_full(ch)
            else:
                codes = unicodedb.tolower_full(ch)
            for c in codes:
                builder.append_code(c)
            previous_is_cased = unicodedb.iscased(codes[-1])
            i += 1
        return self.from_utf8builder(builder)

    def _handle_capital_sigma(self, value, i):
        # U+03A3 is in the Final_Sigma context when, it is found like this:
        #\p{cased} \p{case-ignorable}* U+03A3 not(\p{case-ignorable}* \p{cased})
        # where \p{xxx} is a character with property xxx.

        # TODO: find a better way for utf8 -> codepoints
        value = [ch for ch in rutf8.Utf8StringIterator(value)]
        j = i - 1
        final_sigma = False
        while j >= 0:
            ch = value[j]
            if unicodedb.iscaseignorable(ch):
                j -= 1
                continue
            final_sigma = unicodedb.iscased(ch)
            break
        if final_sigma:
            j = i + 1
            length = len(value)
            while j < length:
                ch = value[j]
                if unicodedb.iscaseignorable(ch):
                    j += 1
                    continue
                final_sigma = not unicodedb.iscased(ch)
                break
        if final_sigma:
            return 0x3C2
        else:
            return 0x3C3

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
                                "or str")
            try:
                builder.append_code(codepoint)
            except ValueError:
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
            return space.newbool(func(rutf8.codepoint_at_pos(self._utf8, 0)))
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
        return encode_object(space, self, encoding, errors, allow_surrogates=False)

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
        l = space.listview_utf8(w_list)
        if l is not None and self.is_ascii():
            if len(l) == 1:
                return space.newutf8(l[0], len(l[0]))
            s = self._utf8.join(l)
            return space.newutf8(s, len(s))
        return self._StringMethods_descr_join(space, w_list)

    def _join_return_one(self, space, w_obj):
        return space.is_w(space.type(w_obj), space.w_unicode)

    def descr_casefold(self, space):
        value = self._utf8
        builder = rutf8.Utf8StringBuilder(len(value))
        for ch in rutf8.Utf8StringIterator(value):
            folded = unicodedb.casefold_lookup(ch)
            if folded is None:
                builder.append_code(unicodedb.tolower(ch))
            else:
                for r in folded:
                    builder.append_code(r)
        return self.from_utf8builder(builder)

    def descr_lower(self, space):
        value = self._utf8
        builder = rutf8.Utf8StringBuilder(len(value))
        i = 0
        for ch in rutf8.Utf8StringIterator(value):
            if ch == 0x3a3:
                codes = [self._handle_capital_sigma(value, i),]
            else:
                codes = unicodedb.tolower_full(ch)
            for c in codes:
                builder.append_code(c)
            i += 1
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

    def descr_isidentifier(self, space):
        return space.newbool(_isidentifier(self._utf8))

    def descr_startswith(self, space, w_prefix, w_start=None, w_end=None):
        start, end = self._unwrap_and_compute_idx_params(space, w_start, w_end)
        value = self._utf8
        if space.isinstance_w(w_prefix, space.w_tuple):
            return self._startswith_tuple(space, value, w_prefix, start, end)
        try:
            return space.newbool(self._startswith(space, value, w_prefix, start,
                                              end))
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                raise oefmt(space.w_TypeError, 'startswith first arg must be str '
                        'or a tuple of str, not %T', w_prefix)

    def _startswith(self, space, value, w_prefix, start, end):
        prefix = self.convert_arg_to_w_unicode(space, w_prefix)._utf8
        if start > len(value):
            return False
        if len(prefix) == 0:
            return True
        return startswith(value, prefix, start, end)

    def descr_endswith(self, space, w_suffix, w_start=None, w_end=None):
        start, end = self._unwrap_and_compute_idx_params(space, w_start, w_end)
        value = self._utf8
        if space.isinstance_w(w_suffix, space.w_tuple):
            return self._endswith_tuple(space, value, w_suffix, start, end)
        try:
            return space.newbool(self._endswith(space, value, w_suffix, start,
                                            end))
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                raise oefmt(space.w_TypeError, 'endswith first arg must be str '
                        'or a tuple of str, not %T', w_suffix)

    def _endswith(self, space, value, w_prefix, start, end):
        prefix = self.convert_arg_to_w_unicode(space, w_prefix)._utf8
        if start > len(value):
            return False
        if len(prefix) == 0:
            return True
        return endswith(value, prefix, start, end)

    def descr_add(self, space, w_other):
        try:
            w_other = self.convert_arg_to_w_unicode(space, w_other, strict='__add__')
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
            codes = unicodedb.toupper_full(ch)
            for c in codes:
                builder.append_code(c)
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
        return W_UnicodeObject(builder.build(), sl)

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
        return W_UnicodeObject(self._utf8[byte_start:byte_stop], stop - start)

    def descr_capitalize(self, space):
        value = self._utf8
        if len(value) == 0:
            return self._empty()

        builder = rutf8.Utf8StringBuilder(len(self._utf8))
        it = rutf8.Utf8StringIterator(self._utf8)
        uchar = it.next()
        codes = unicodedb.toupper_full(uchar)
        # can sometimes give more than one, like for omega-with-Ypogegrammeni, 8179
        for c in codes:
            builder.append_code(c)
        for ch in it:
            ch = unicodedb.tolower(ch)
            builder.append_code(ch)
        return self.from_utf8builder(builder)

    @unwrap_spec(width=int, w_fillchar=WrappedDefault(u' '))
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
        # XXX write the correct jit.elidable
        if self._index_storage == rutf8.null_storage():
            storage = rutf8.create_utf8_index_storage(self._utf8, self._length)
        else:
            storage = self._index_storage
        if not jit.isconstant(self):
            self._index_storage = storage
        return storage

    def _getitem_result(self, space, index):
        if index < 0:
            index += self._length
        if index < 0 or index >= self._length:
            raise oefmt(space.w_IndexError, "string index out of range")
        start = self._index_to_byte(index)
        end = rutf8.next_codepoint_pos(self._utf8, start)
        return W_UnicodeObject(self._utf8[start:end], 1)

    def is_ascii(self):
        return self._length == len(self._utf8)

    def _has_surrogates(self):
        if self.is_ascii():
            return False
        return rutf8.has_surrogates(self._utf8)

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
                start_index = end_index + 1
            else:
                start_index = self._index_to_byte(start)
        if end < self._length:
            end_index = self._index_to_byte(end)
        return (start_index, end_index)

    @unwrap_spec(width=int, w_fillchar=WrappedDefault(u' '))
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

    @unwrap_spec(width=int, w_fillchar=WrappedDefault(u' '))
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
        chars = self.convert_arg_to_w_unicode(space, w_chars)._utf8

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
        return space.newtuple([W_UnicodeObject(self._utf8, self._length)])


    def descr_isprintable(self, space):
        for ch in rutf8.Utf8StringIterator(self._utf8):
            if not unicodedb.isprintable(ch):
                return space.w_False
        return space.w_True

    @staticmethod
    def _iter_getitem_result(self, space, index):
        assert isinstance(self, W_UnicodeObject)
        return self._getitem_result(space, index)


def _isidentifier(u):
    if not u:
        return False

    # PEP 3131 says that the first character must be in XID_Start and
    # subsequent characters in XID_Continue, and for the ASCII range,
    # the 2.x rules apply (i.e start with letters and underscore,
    # continue with letters, digits, underscore). However, given the
    # current definition of XID_Start and XID_Continue, it is sufficient
    # to check just for these, except that _ must be allowed as starting
    # an identifier.
    first = u[0]
    it = rutf8.Utf8StringIterator(u)
    code = it.next()
    if not (unicodedb.isxidstart(code) or first == u'_'):
        return False

    for ch in it:
        if not unicodedb.isxidcontinue(ch):
            return False
    return True

# stuff imported from bytesobject for interoperability


# ____________________________________________________________

def getdefaultencoding(space):
    return space.sys.defaultencoding


def _get_encoding_and_errors(space, w_encoding, w_errors):
    encoding = None if w_encoding is None else space.text_w(w_encoding)
    errors = None if w_errors is None else space.text_w(w_errors)
    return encoding, errors


def encode_object(space, w_object, encoding, errors, allow_surrogates=False):
    utf8 = space.utf8_w(w_object)
    # TODO: refactor unnatrual use of error hanlders here,
    # we should make a single pass over the utf8 str
    from pypy.module._codecs.interp_codecs import encode_text, CodecState
    if not allow_surrogates:
        if errors is None:
            errors = 'strict'
        pos = rutf8.surrogate_in_utf8(utf8)
        if pos >= 0:
            state = space.fromcache(CodecState)
            eh = state.encode_error_handler
            start = utf8[:pos]
            ru, pos = eh(errors, "utf8", "surrogates not allowed", utf8,
                pos, pos + 1)
            end = utf8[pos+1:]
            utf8 = start + ru + end
    if errors is None or errors == 'strict':
        if encoding is None or encoding == 'utf-8':
            #if rutf8.has_surrogates(utf8):
            #    utf8 = rutf8.reencode_utf8_with_surrogates(utf8)
            return space.newbytes(utf8)
        elif encoding == 'ascii':
            try:
                rutf8.check_ascii(utf8)
            except rutf8.CheckError as a:
                eh = unicodehelper.encode_error_handler(space)
                eh(None, "ascii", "ordinal not in range(128)", utf8,
                    a.pos, a.pos + 1)
                assert False, "always raises"
            return space.newbytes(utf8)

    if encoding is None:
        encoding = space.sys.defaultencoding
    w_retval = encode_text(space, w_object, encoding, errors)
    if not space.isinstance_w(w_retval, space.w_bytes):
        raise oefmt(space.w_TypeError,
                    "'%s' encoder returned '%T' instead of 'bytes'; "
                    "use codecs.encode() to encode to arbitrary types",
                    encoding,
                    w_retval)
    return w_retval


def decode_object(space, w_obj, encoding, errors='strict'):
    assert errors is not None
    assert encoding is not None
    if errors == 'surrogateescape':
        s = space.charbuf_w(w_obj)
        s, lgt, pos = unicodehelper.str_decode_utf8(s, errors, True,
                    unicodehelper.decode_surrogateescape, True)
        return space.newutf8(s, pos)
    elif errors == 'strict':
        if encoding == 'ascii':
            s = space.charbuf_w(w_obj)
            unicodehelper.check_ascii_or_raise(space, s)
            return space.newtext(s, len(s))
        if encoding == 'utf-8' or encoding == 'utf8':
            s = space.charbuf_w(w_obj)
            lgt = unicodehelper.check_utf8_or_raise(space, s)
            return space.newutf8(s, lgt)
    from pypy.module._codecs.interp_codecs import decode_text
    w_retval = decode_text(space, w_obj, encoding, errors)
    if not space.isinstance_w(w_retval, space.w_unicode):
        raise oefmt(space.w_TypeError,
                    "'%s' decoder returned '%T' instead of 'str'; "
                    "use codecs.decode() to decode to arbitrary types",
                    encoding,
                    w_retval)
    return w_retval


def unicode_from_encoded_object(space, w_obj, encoding, errors):
    if errors is None:
        errors = 'strict'
    if encoding is None:
        encoding = getdefaultencoding(space)
    w_retval = decode_object(space, w_obj, encoding, errors)
    if not space.isinstance_w(w_retval, space.w_unicode):
        raise oefmt(space.w_TypeError,
                    "decoder did not return a str object (type '%T')",
                    w_retval)
    assert isinstance(w_retval, W_UnicodeObject)
    return w_retval


def unicode_from_object(space, w_obj):
    if space.is_w(space.type(w_obj), space.w_unicode):
        return w_obj
    if space.lookup(w_obj, "__str__") is not None:
        return space.str(w_obj)
    return space.repr(w_obj)

def ascii_from_object(space, w_obj):
    """Implements builtins.ascii()"""
    # repr is guaranteed to be unicode
    w_repr = space.repr(w_obj)
    w_encoded = encode_object(space, w_repr, 'ascii', 'backslashreplace')
    return decode_object(space, w_encoded, 'ascii', 'strict')

def unicode_from_string(space, w_bytes):
    # this is a performance and bootstrapping hack
    encoding = getdefaultencoding(space)
    if encoding != 'ascii':
        return unicode_from_encoded_object(space, w_bytes, encoding, "strict")
    s = space.bytes_w(w_bytes)
    unicodehelper.check_ascii_or_raise(space, s)
    return W_UnicodeObject(s, len(s))


class UnicodeDocstrings:
    """str(object='') -> str
    str(bytes_or_buffer[, encoding[, errors]]) -> str

    Create a new string object from the given object. If encoding or
    errors is specified, then the object must expose a data buffer
    that will be decoded using the given encoding and error handler.
    Otherwise, returns the result of object.__str__() (if defined)
    or repr(object).
    encoding defaults to sys.getdefaultencoding().
    errors defaults to 'strict'.

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

    def __gt__():
        """x.__gt__(y) <==> x>y"""

    def __hash__():
        """x.__hash__() <==> hash(x)"""

    def __iter__():
        """x.__iter__() <==> iter(x)"""

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

    def format_map():
        """S.format_map(mapping) -> str

        Return a formatted version of S, using substitutions from
        mapping.  The substitutions are identified by braces ('{' and
        '}').
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

    def casefold():
        """S.casefold() -> str

        Return a version of S suitable for caseless comparisons.
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

    def isidentifier():
        """S.isidentifier() -> bool

        Return True if S is a valid identifier according to the language
        definition.
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

    def isprintable():
        """S.isprintable() -> bool

        Return True if all characters in S are considered printable in
        repr() or S is empty, False otherwise.
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

    def maketrans():
        """str.maketrans(x[, y[, z]]) -> dict (static method)

        Return a translation table usable for str.translate().  If there
        is only one argument, it must be a dictionary mapping Unicode
        ordinals (integers) or characters to Unicode ordinals, strings
        or None.  Character keys will be then converted to ordinals.  If
        there are two arguments, they must be strings of equal length,
        and in the resulting dictionary, each character in x will be
        mapped to the character at the same position in y. If there is a
        third argument, it must be a string, whose characters will be
        mapped to None in the result.
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
    "str",
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

    __iter__ = interp2app(W_UnicodeObject.descr_iter,
                         doc=UnicodeDocstrings.__iter__.__doc__),
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

    capitalize = interp2app(W_UnicodeObject.descr_capitalize,
                            doc=UnicodeDocstrings.capitalize.__doc__),
    casefold = interp2app(W_UnicodeObject.descr_casefold,
                            doc=UnicodeDocstrings.casefold.__doc__),
    center = interp2app(W_UnicodeObject.descr_center,
                        doc=UnicodeDocstrings.center.__doc__),
    count = interp2app(W_UnicodeObject.descr_count,
                       doc=UnicodeDocstrings.count.__doc__),
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
    isidentifier = interp2app(W_UnicodeObject.descr_isidentifier,
                         doc=UnicodeDocstrings.isidentifier.__doc__),
    islower = interp2app(W_UnicodeObject.descr_islower,
                         doc=UnicodeDocstrings.islower.__doc__),
    isnumeric = interp2app(W_UnicodeObject.descr_isnumeric,
                           doc=UnicodeDocstrings.isnumeric.__doc__),
    isprintable = interp2app(W_UnicodeObject.descr_isprintable,
                         doc=UnicodeDocstrings.isprintable.__doc__),
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
    format_map = interp2app(W_UnicodeObject.descr_format_map,
                        doc=UnicodeDocstrings.format_map.__doc__),
    __format__ = interp2app(W_UnicodeObject.descr__format__,
                            doc=UnicodeDocstrings.__format__.__doc__),
    __mod__ = interp2app(W_UnicodeObject.descr_mod,
                         doc=UnicodeDocstrings.__mod__.__doc__),
    __rmod__ = interp2app(W_UnicodeObject.descr_rmod,
                         doc=UnicodeDocstrings.__rmod__.__doc__),
    __getnewargs__ = interp2app(W_UnicodeObject.descr_getnewargs,
                                doc=UnicodeDocstrings.__getnewargs__.__doc__),
    maketrans = interp2app(W_UnicodeObject.descr_maketrans,
                           as_classmethod=True,
                           doc=UnicodeDocstrings.maketrans.__doc__),
)
W_UnicodeObject.typedef.flag_sequence_bug_compat = True


def _create_list_from_unicode(value):
    # need this helper function to allow the jit to look inside and inline
    # listview_unicode
    return [s for s in value]


W_UnicodeObject.EMPTY = W_UnicodeObject('', 0)

# Helper for converting int/long this is called only from
# {int,long,float}type.descr__new__: in the default branch this is implemented
# using the same logic as PyUnicode_EncodeDecimal, as CPython 2.7 does.
#
# In CPython3 the call to PyUnicode_EncodeDecimal has been replaced to a call
# to _PyUnicode_TransformDecimalAndSpaceToASCII, which is much simpler.
# We do that here plus the final step of encoding the result to utf-8.
# This final step corresponds to encode_utf8. In float.__new__() and
# complex.__new__(), a lone surrogate will throw an app-level
# UnicodeEncodeError.

def unicode_to_decimal_w(space, w_unistr, allow_surrogates=False):
    if not isinstance(w_unistr, W_UnicodeObject):
        raise oefmt(space.w_TypeError, "expected unicode, got '%T'", w_unistr)
    value = _rpy_unicode_to_decimal_w(space, w_unistr.utf8_w(space).decode('utf8'))
    # XXX this is the only place in the code that this funcion is called.
    # It does not translate, since it uses a pypy-level error handler
    # to throw the UnicodeEncodeError not the rpython default handler
    #return unicodehelper.encode_utf8(space, value,
    #                                 allow_surrogates=allow_surrogates)
    assert isinstance(value, unicode)
    return value.encode('utf8')

def _rpy_unicode_to_decimal_w(space, unistr):
    # XXX rewrite this to accept a utf8 string and use a StringBuilder
    result = [u'\0'] * len(unistr)
    for i in xrange(len(unistr)):
        uchr = ord(unistr[i])
        if uchr > 127:
            if unicodedb.isspace(uchr):
                result[i] = ' '
                continue
            try:
                uchr = ord(u'0') + unicodedb.decimal(uchr)
            except KeyError:
                pass
        result[i] = unichr(uchr)
    return u''.join(result)

@jit.elidable
def g_encode_utf8(value):
    """This is a global function because of jit.conditional_call_value"""
    return unicode_encode_utf8_forbid_surrogates(value, len(value))

_repr_function = rutf8.make_utf8_escape_function(
    pass_printable=True, quotes=True, prefix='')
