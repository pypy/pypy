"""The builtin str implementation"""

from rpython.rlib import jit, rutf8
from rpython.rlib.objectmodel import (
    compute_hash, compute_unique_id, import_from_mixin)
from rpython.rlib.buffer import StringBuffer
from rpython.rlib.rstring import StringBuilder

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import (
    WrappedDefault, interp2app, interpindirect2app, unwrap_spec)
from pypy.interpreter.typedef import TypeDef
from pypy.objspace.std import newformat
from pypy.objspace.std.basestringtype import basestring_typedef
from pypy.objspace.std.formatting import mod_format
from pypy.objspace.std.stringmethods import StringMethods
from pypy.objspace.std.unicodeobject import (
    decode_object, unicode_from_encoded_object,
    getdefaultencoding)
from pypy.objspace.std.util import IDTAG_SPECIAL, IDTAG_SHIFT


class W_AbstractBytesObject(W_Root):
    __slots__ = ()

    def is_w(self, space, w_other):
        if not isinstance(w_other, W_AbstractBytesObject):
            return False
        if self is w_other:
            return True
        if self.user_overridden_class or w_other.user_overridden_class:
            return False
        s1 = space.bytes_w(self)
        s2 = space.bytes_w(w_other)
        if len(s2) > 1:
            return s1 is s2
        else:            # strings of len <= 1 are unique-ified
            return s1 == s2

    def immutable_unique_id(self, space):
        if self.user_overridden_class:
            return None
        s = space.bytes_w(self)
        if len(s) > 1:
            uid = compute_unique_id(s)
        else:            # strings of len <= 1 are unique-ified
            if len(s) == 1:
                base = ord(s[0])     # base values 0-255
            else:
                base = 256           # empty string: base value 256
            uid = (base << IDTAG_SHIFT) | IDTAG_SPECIAL
        return space.newint(uid)

    def convert_to_w_unicode(self, space):
        # Use the default encoding.
        encoding = getdefaultencoding(space)
        if encoding == 'ascii':
            try:
                rutf8.check_ascii(self._value)
                return space.newutf8(self._value, len(self._value))
            except rutf8.AsciiCheckError:
                xxx
        else:
            xxx
        return space.unicode_w(decode_object(space, self, encoding, None))

    def descr_add(self, space, w_other):
        """x.__add__(y) <==> x+y"""

    def descr_contains(self, space, w_sub):
        """x.__contains__(y) <==> y in x"""

    def descr_eq(self, space, w_other):
        """x.__eq__(y) <==> x==y"""

    def descr__format__(self, space, w_format_spec):
        """S.__format__(format_spec) -> string

        Return a formatted version of S as described by format_spec.
        """

    def descr_ge(self, space, w_other):
        """x.__ge__(y) <==> x>=y"""

    def descr_getitem(self, space, w_index):
        """x.__getitem__(y) <==> x[y]"""

    def descr_getnewargs(self, space):
        ""

    def descr_getslice(self, space, w_start, w_stop):
        """x.__getslice__(i, j) <==> x[i:j]

        Use of negative indices is not supported.
        """

    def descr_gt(self, space, w_other):
        """x.__gt__(y) <==> x>y"""

    def descr_hash(self, space):
        """x.__hash__() <==> hash(x)"""

    def descr_le(self, space, w_other):
        """x.__le__(y) <==> x<=y"""

    def descr_len(self, space):
        """x.__len__() <==> len(x)"""

    def descr_lt(self, space, w_other):
        """x.__lt__(y) <==> x<y"""

    def descr_mod(self, space, w_values):
        """x.__mod__(y) <==> x%y"""

    def descr_mul(self, space, w_times):
        """x.__mul__(n) <==> x*n"""

    def descr_ne(self, space, w_other):
        """x.__ne__(y) <==> x!=y"""

    def descr_repr(self, space):
        """x.__repr__() <==> repr(x)"""

    def descr_rmod(self, space, w_values):
        """x.__rmod__(y) <==> y%x"""

    def descr_rmul(self, space, w_times):
        """x.__rmul__(n) <==> n*x"""

    def descr_str(self, space):
        """x.__str__() <==> str(x)"""

    def descr_capitalize(self, space):
        """S.capitalize() -> string

        Return a capitalized version of S, i.e. make the first character
        have upper case and the rest lower case.
        """

    @unwrap_spec(width=int, w_fillchar=WrappedDefault(' '))
    def descr_center(self, space, width, w_fillchar):
        """S.center(width[, fillchar]) -> string

        Return S centered in a string of length width. Padding is
        done using the specified fill character (default is a space).
        """

    def descr_count(self, space, w_sub, w_start=None, w_end=None):
        """S.count(sub[, start[, end]]) -> int

        Return the number of non-overlapping occurrences of substring sub in
        string S[start:end].  Optional arguments start and end are interpreted
        as in slice notation.
        """

    def descr_decode(self, space, w_encoding=None, w_errors=None):
        """S.decode(encoding=None, errors='strict') -> object

        Decode S using the codec registered for encoding. encoding defaults
        to the default encoding. errors may be given to set a different error
        handling scheme. Default is 'strict' meaning that encoding errors raise
        a UnicodeDecodeError. Other possible values are 'ignore' and 'replace'
        as well as any other name registered with codecs.register_error that is
        able to handle UnicodeDecodeErrors.
        """

    def descr_encode(self, space, w_encoding=None, w_errors=None):
        """S.encode(encoding=None, errors='strict') -> object

        Encode S using the codec registered for encoding. encoding defaults
        to the default encoding. errors may be given to set a different error
        handling scheme. Default is 'strict' meaning that encoding errors raise
        a UnicodeEncodeError. Other possible values are 'ignore', 'replace' and
        'xmlcharrefreplace' as well as any other name registered with
        codecs.register_error that is able to handle UnicodeEncodeErrors.
        """

    def descr_endswith(self, space, w_suffix, w_start=None, w_end=None):
        """S.endswith(suffix[, start[, end]]) -> bool

        Return True if S ends with the specified suffix, False otherwise.
        With optional start, test S beginning at that position.
        With optional end, stop comparing S at that position.
        suffix can also be a tuple of strings to try.
        """

    @unwrap_spec(tabsize=int)
    def descr_expandtabs(self, space, tabsize=8):
        """S.expandtabs([tabsize]) -> string

        Return a copy of S where all tab characters are expanded using spaces.
        If tabsize is not given, a tab size of 8 characters is assumed.
        """

    def descr_find(self, space, w_sub, w_start=None, w_end=None):
        """S.find(sub[, start[, end]]) -> int

        Return the lowest index in S where substring sub is found,
        such that sub is contained within S[start:end].  Optional
        arguments start and end are interpreted as in slice notation.

        Return -1 on failure.
        """

    def descr_format(self, space, __args__):
        """S.format(*args, **kwargs) -> string

        Return a formatted version of S, using substitutions from args and
        kwargs.  The substitutions are identified by braces ('{' and '}').
        """

    def descr_index(self, space, w_sub, w_start=None, w_end=None):
        """S.index(sub[, start[, end]]) -> int

        Like S.find() but raise ValueError when the substring is not found.
        """

    def descr_isalnum(self, space):
        """S.isalnum() -> bool

        Return True if all characters in S are alphanumeric
        and there is at least one character in S, False otherwise.
        """

    def descr_isalpha(self, space):
        """S.isalpha() -> bool

        Return True if all characters in S are alphabetic
        and there is at least one character in S, False otherwise.
        """

    def descr_isdigit(self, space):
        """S.isdigit() -> bool

        Return True if all characters in S are digits
        and there is at least one character in S, False otherwise.
        """

    def descr_islower(self, space):
        """S.islower() -> bool

        Return True if all cased characters in S are lowercase and there is
        at least one cased character in S, False otherwise.
        """

    def descr_isspace(self, space):
        """S.isspace() -> bool

        Return True if all characters in S are whitespace
        and there is at least one character in S, False otherwise.
        """

    def descr_istitle(self, space):
        """S.istitle() -> bool

        Return True if S is a titlecased string and there is at least one
        character in S, i.e. uppercase characters may only follow uncased
        characters and lowercase characters only cased ones. Return False
        otherwise.
        """

    def descr_isupper(self, space):
        """S.isupper() -> bool

        Return True if all cased characters in S are uppercase and there is
        at least one cased character in S, False otherwise.
        """

    def descr_join(self, space, w_list):
        """S.join(iterable) -> string

        Return a string which is the concatenation of the strings in the
        iterable.  The separator between elements is S.
        """

    @unwrap_spec(width=int, w_fillchar=WrappedDefault(' '))
    def descr_ljust(self, space, width, w_fillchar):
        """S.ljust(width[, fillchar]) -> string

        Return S left-justified in a string of length width. Padding is
        done using the specified fill character (default is a space).
        """

    def descr_lower(self, space):
        """S.lower() -> string

        Return a copy of the string S converted to lowercase.
        """

    def descr_lstrip(self, space, w_chars=None):
        """S.lstrip([chars]) -> string or unicode

        Return a copy of the string S with leading whitespace removed.
        If chars is given and not None, remove characters in chars instead.
        If chars is unicode, S will be converted to unicode before stripping
        """

    def descr_partition(self, space, w_sub):
        """S.partition(sep) -> (head, sep, tail)

        Search for the separator sep in S, and return the part before it,
        the separator itself, and the part after it.  If the separator is not
        found, return S and two empty strings.
        """

    @unwrap_spec(count=int)
    def descr_replace(self, space, w_old, w_new, count=-1):
        """S.replace(old, new[, count]) -> string

        Return a copy of string S with all occurrences of substring
        old replaced by new.  If the optional argument count is
        given, only the first count occurrences are replaced.
        """

    def descr_rfind(self, space, w_sub, w_start=None, w_end=None):
        """S.rfind(sub[, start[, end]]) -> int

        Return the highest index in S where substring sub is found,
        such that sub is contained within S[start:end].  Optional
        arguments start and end are interpreted as in slice notation.

        Return -1 on failure.
        """

    def descr_rindex(self, space, w_sub, w_start=None, w_end=None):
        """S.rindex(sub[, start[, end]]) -> int

        Like S.rfind() but raise ValueError when the substring is not found.
        """

    @unwrap_spec(width=int, w_fillchar=WrappedDefault(' '))
    def descr_rjust(self, space, width, w_fillchar):
        """S.rjust(width[, fillchar]) -> string

        Return S right-justified in a string of length width. Padding is
        done using the specified fill character (default is a space).
        """

    def descr_rpartition(self, space, w_sub):
        """S.rpartition(sep) -> (head, sep, tail)

        Search for the separator sep in S, starting at the end of S, and return
        the part before it, the separator itself, and the part after it.  If
        the separator is not found, return two empty strings and S.
        """

    @unwrap_spec(maxsplit=int)
    def descr_rsplit(self, space, w_sep=None, maxsplit=-1):
        """S.rsplit(sep=None, maxsplit=-1) -> list of strings

        Return a list of the words in the string S, using sep as the
        delimiter string, starting at the end of the string and working
        to the front.  If maxsplit is given, at most maxsplit splits are
        done. If sep is not specified or is None, any whitespace string
        is a separator.
        """

    def descr_rstrip(self, space, w_chars=None):
        """S.rstrip([chars]) -> string or unicode

        Return a copy of the string S with trailing whitespace removed.
        If chars is given and not None, remove characters in chars instead.
        If chars is unicode, S will be converted to unicode before stripping
        """

    @unwrap_spec(maxsplit=int)
    def descr_split(self, space, w_sep=None, maxsplit=-1):
        """S.split(sep=None, maxsplit=-1) -> list of strings

        Return a list of the words in the string S, using sep as the
        delimiter string.  If maxsplit is given, at most maxsplit
        splits are done. If sep is not specified or is None, any
        whitespace string is a separator and empty strings are removed
        from the result.
        """

    @unwrap_spec(keepends=bool)
    def descr_splitlines(self, space, keepends=False):
        """S.splitlines(keepends=False) -> list of strings

        Return a list of the lines in S, breaking at line boundaries.
        Line breaks are not included in the resulting list unless keepends
        is given and true.
        """

    def descr_startswith(self, space, w_prefix, w_start=None, w_end=None):
        """S.startswith(prefix[, start[, end]]) -> bool

        Return True if S starts with the specified prefix, False otherwise.
        With optional start, test S beginning at that position.
        With optional end, stop comparing S at that position.
        prefix can also be a tuple of strings to try.
        """

    def descr_strip(self, space, w_chars=None):
        """S.strip([chars]) -> string or unicode

        Return a copy of the string S with leading and trailing
        whitespace removed.
        If chars is given and not None, remove characters in chars instead.
        If chars is unicode, S will be converted to unicode before stripping
        """

    def descr_swapcase(self, space):
        """S.swapcase() -> string

        Return a copy of the string S with uppercase characters
        converted to lowercase and vice versa.
        """

    def descr_title(self, space):
        """S.title() -> string

        Return a titlecased version of S, i.e. words start with uppercase
        characters, all remaining cased characters have lowercase.
        """

    @unwrap_spec(w_deletechars=WrappedDefault(''))
    def descr_translate(self, space, w_table, w_deletechars):
        """S.translate(table[, deletechars]) -> string

        Return a copy of the string S, where all characters occurring
        in the optional argument deletechars are removed, and the
        remaining characters have been mapped through the given
        translation table, which must be a string of length 256 or None.
        If the table argument is None, no translation is applied and
        the operation simply removes the characters in deletechars.
        """

    def descr_upper(self, space):
        """S.upper() -> string

        Return a copy of the string S converted to uppercase.
        """

    @unwrap_spec(width=int)
    def descr_zfill(self, space, width):
        """S.zfill(width) -> string

        Pad a numeric string S with zeros on the left, to fill a field
        of the specified width. The string S is never truncated.
        """

class W_BytesObject(W_AbstractBytesObject):
    import_from_mixin(StringMethods)
    _immutable_fields_ = ['_value']

    def __init__(self, str):
        assert str is not None
        self._value = str

    def __repr__(self):
        """representation for debugging purposes"""
        return "%s(%r)" % (self.__class__.__name__, self._value)

    def unwrap(self, space):
        return self._value

    def str_w(self, space):
        return self._value

    def buffer_w(self, space, flags):
        space.check_buf_flags(flags, True)
        return StringBuffer(self._value)

    def readbuf_w(self, space):
        return StringBuffer(self._value)

    def writebuf_w(self, space):
        raise oefmt(space.w_TypeError,
                    "Cannot use string as modifiable buffer")

    def descr_getbuffer(self, space, w_flags):
        #from pypy.objspace.std.bufferobject import W_Buffer
        #return W_Buffer(StringBuffer(self._value))
        return self

    charbuf_w = str_w

    def listview_bytes(self):
        return _create_list_from_bytes(self._value)

    def ord(self, space):
        if len(self._value) != 1:
            raise oefmt(space.w_TypeError,
                        "ord() expected a character, but string of length %d "
                        "found", len(self._value))
        return space.newint(ord(self._value[0]))

    def _new(self, value):
        return W_BytesObject(value)

    def _new_from_list(self, value):
        return W_BytesObject(''.join(value))

    def _empty(self):
        return W_BytesObject.EMPTY

    def _len(self):
        return len(self._value)

    _val = str_w

    @staticmethod
    def _use_rstr_ops(space, w_other):
        from pypy.objspace.std.unicodeobject import W_UnicodeObject
        return (isinstance(w_other, W_BytesObject) or
                isinstance(w_other, W_UnicodeObject))

    @staticmethod
    def _op_val(space, w_other, strict=None):
        if strict and not space.isinstance_w(w_other, space.w_bytes):
            raise oefmt(space.w_TypeError,
                "%s arg must be None, str or unicode", strict)
        try:
            return space.bytes_w(w_other)
        except OperationError as e:
            if not e.match(space, space.w_TypeError):
                raise
        return space.charbuf_w(w_other)

    def _chr(self, char):
        assert len(char) == 1
        return str(char)[0]

    _builder = StringBuilder

    def _isupper(self, ch):
        return ch.isupper()

    def _islower(self, ch):
        return ch.islower()

    def _istitle(self, ch):
        return ch.isupper()

    def _isspace(self, ch):
        return ch.isspace()

    def _isalpha(self, ch):
        return ch.isalpha()

    def _isalnum(self, ch):
        return ch.isalnum()

    def _isdigit(self, ch):
        return ch.isdigit()

    _iscased = _isalpha

    def _islinebreak(self, ch):
        return (ch == '\n') or (ch == '\r')

    def _upper(self, ch):
        if ch.islower():
            o = ord(ch) - 32
            return chr(o)
        else:
            return ch

    def _lower(self, ch):
        if ch.isupper():
            o = ord(ch) + 32
            return chr(o)
        else:
            return ch

    _title = _upper

    def _newlist_unwrapped(self, space, lst):
        return space.newlist_bytes(lst)

    @staticmethod
    @unwrap_spec(w_object=WrappedDefault(""))
    def descr_new(space, w_stringtype, w_object):
        # NB. the default value of w_object is really a *wrapped* empty string:
        #     there is gateway magic at work
        w_obj = space.str(w_object)
        if space.is_w(w_stringtype, space.w_bytes):
            return w_obj  # XXX might be reworked when space.str() typechecks
        value = space.bytes_w(w_obj)
        w_obj = space.allocate_instance(W_BytesObject, w_stringtype)
        W_BytesObject.__init__(w_obj, value)
        return w_obj

    def descr_repr(self, space):
        s = self._value
        quote = "'"
        if quote in s and '"' not in s:
            quote = '"'
        return space.newtext(string_escape_encode(s, quote))

    def descr_str(self, space):
        if type(self) is W_BytesObject:
            return self
        return W_BytesObject(self._value)

    def descr_hash(self, space):
        x = compute_hash(self._value)
        return space.newint(x)

    def descr_format(self, space, __args__):
        return newformat.format_method(space, self, __args__, is_unicode=False)

    def descr__format__(self, space, w_format_spec):
        if not space.isinstance_w(w_format_spec, space.w_bytes):
            w_format_spec = space.str(w_format_spec)
        spec = space.bytes_w(w_format_spec)
        formatter = newformat.str_formatter(space, spec)
        return formatter.format_string(self._value)

    def descr_mod(self, space, w_values):
        return mod_format(space, self, w_values, do_unicode=False)

    def descr_rmod(self, space, w_values):
        return mod_format(space, w_values, self, do_unicode=False)

    def descr_eq(self, space, w_other):
        if space.config.objspace.std.withstrbuf:
            from pypy.objspace.std.strbufobject import W_StringBufferObject
            if isinstance(w_other, W_StringBufferObject):
                return space.newbool(self._value == w_other.force())
        if not isinstance(w_other, W_BytesObject):
            return space.w_NotImplemented
        return space.newbool(self._value == w_other._value)

    def descr_ne(self, space, w_other):
        if space.config.objspace.std.withstrbuf:
            from pypy.objspace.std.strbufobject import W_StringBufferObject
            if isinstance(w_other, W_StringBufferObject):
                return space.newbool(self._value != w_other.force())
        if not isinstance(w_other, W_BytesObject):
            return space.w_NotImplemented
        return space.newbool(self._value != w_other._value)

    def descr_lt(self, space, w_other):
        if space.config.objspace.std.withstrbuf:
            from pypy.objspace.std.strbufobject import W_StringBufferObject
            if isinstance(w_other, W_StringBufferObject):
                return space.newbool(self._value < w_other.force())
        if not isinstance(w_other, W_BytesObject):
            return space.w_NotImplemented
        return space.newbool(self._value < w_other._value)

    def descr_le(self, space, w_other):
        if space.config.objspace.std.withstrbuf:
            from pypy.objspace.std.strbufobject import W_StringBufferObject
            if isinstance(w_other, W_StringBufferObject):
                return space.newbool(self._value <= w_other.force())
        if not isinstance(w_other, W_BytesObject):
            return space.w_NotImplemented
        return space.newbool(self._value <= w_other._value)

    def descr_gt(self, space, w_other):
        if space.config.objspace.std.withstrbuf:
            from pypy.objspace.std.strbufobject import W_StringBufferObject
            if isinstance(w_other, W_StringBufferObject):
                return space.newbool(self._value > w_other.force())
        if not isinstance(w_other, W_BytesObject):
            return space.w_NotImplemented
        return space.newbool(self._value > w_other._value)

    def descr_ge(self, space, w_other):
        if space.config.objspace.std.withstrbuf:
            from pypy.objspace.std.strbufobject import W_StringBufferObject
            if isinstance(w_other, W_StringBufferObject):
                return space.newbool(self._value >= w_other.force())
        if not isinstance(w_other, W_BytesObject):
            return space.w_NotImplemented
        return space.newbool(self._value >= w_other._value)

    # auto-conversion fun

    _StringMethods_descr_add = descr_add
    def descr_add(self, space, w_other):
        if space.isinstance_w(w_other, space.w_unicode):
            self_as_unicode = unicode_from_encoded_object(space, self, None,
                                                          None)
            return space.add(self_as_unicode, w_other)
        elif space.isinstance_w(w_other, space.w_bytearray):
            # XXX: eliminate double-copy
            from .bytearrayobject import W_BytearrayObject, _make_data
            self_as_bytearray = W_BytearrayObject(_make_data(self._value))
            return space.add(self_as_bytearray, w_other)
        if space.config.objspace.std.withstrbuf:
            from pypy.objspace.std.strbufobject import W_StringBufferObject
            try:
                other = self._op_val(space, w_other)
            except OperationError as e:
                if e.match(space, space.w_TypeError):
                    return space.w_NotImplemented
                raise
            builder = StringBuilder()
            builder.append(self._value)
            builder.append(other)
            return W_StringBufferObject(builder)
        return self._StringMethods_descr_add(space, w_other)

    _StringMethods__startswith = _startswith
    def _startswith(self, space, value, w_prefix, start, end):
        if space.isinstance_w(w_prefix, space.w_unicode):
            self_as_unicode = unicode_from_encoded_object(space, self, None,
                                                          None)
            return self_as_unicode._startswith(space, self_as_unicode._utf8.decode("utf8"),
                                               w_prefix, start, end)
        return self._StringMethods__startswith(space, value, w_prefix, start,
                                               end)

    _StringMethods__endswith = _endswith
    def _endswith(self, space, value, w_suffix, start, end):
        if space.isinstance_w(w_suffix, space.w_unicode):
            self_as_unicode = unicode_from_encoded_object(space, self, None,
                                                          None)
            return self_as_unicode._endswith(space, self_as_unicode._utf8.decode("utf8"),
                                             w_suffix, start, end)
        return self._StringMethods__endswith(space, value, w_suffix, start,
                                             end)

    _StringMethods_descr_contains = descr_contains
    def descr_contains(self, space, w_sub):
        if space.isinstance_w(w_sub, space.w_unicode):
            from pypy.objspace.std.unicodeobject import W_UnicodeObject
            assert isinstance(w_sub, W_UnicodeObject)
            self_as_unicode = unicode_from_encoded_object(space, self, None,
                                                          None)
            return space.newbool(
                self_as_unicode._utf8.find(w_sub._utf8) >= 0)
        return self._StringMethods_descr_contains(space, w_sub)

    _StringMethods_descr_replace = descr_replace
    @unwrap_spec(count=int)
    def descr_replace(self, space, w_old, w_new, count=-1):
        old_is_unicode = space.isinstance_w(w_old, space.w_unicode)
        new_is_unicode = space.isinstance_w(w_new, space.w_unicode)
        if old_is_unicode or new_is_unicode:
            self_as_uni = unicode_from_encoded_object(space, self, None, None)
            return self_as_uni.descr_replace(space, w_old, w_new, count)
        return self._StringMethods_descr_replace(space, w_old, w_new, count)

    _StringMethods_descr_join = descr_join
    def descr_join(self, space, w_list):
        l = space.listview_bytes(w_list)
        if l is not None:
            if len(l) == 1:
                return space.newbytes(l[0])
            return space.newbytes(self._val(space).join(l))
        return self._StringMethods_descr_join(space, w_list)

    _StringMethods_descr_split = descr_split
    @unwrap_spec(maxsplit=int)
    def descr_split(self, space, w_sep=None, maxsplit=-1):
        if w_sep is not None and space.isinstance_w(w_sep, space.w_unicode):
            self_as_uni = unicode_from_encoded_object(space, self, None, None)
            return self_as_uni.descr_split(space, w_sep, maxsplit)
        return self._StringMethods_descr_split(space, w_sep, maxsplit)

    _StringMethods_descr_rsplit = descr_rsplit
    @unwrap_spec(maxsplit=int)
    def descr_rsplit(self, space, w_sep=None, maxsplit=-1):
        if w_sep is not None and space.isinstance_w(w_sep, space.w_unicode):
            self_as_uni = unicode_from_encoded_object(space, self, None, None)
            return self_as_uni.descr_rsplit(space, w_sep, maxsplit)
        return self._StringMethods_descr_rsplit(space, w_sep, maxsplit)

    _StringMethods_descr_strip = descr_strip
    def descr_strip(self, space, w_chars=None):
        if w_chars is not None and space.isinstance_w(w_chars, space.w_unicode):
            self_as_uni = unicode_from_encoded_object(space, self, None, None)
            return self_as_uni.descr_strip(space, w_chars)
        return self._StringMethods_descr_strip(space, w_chars)

    _StringMethods_descr_lstrip = descr_lstrip
    def descr_lstrip(self, space, w_chars=None):
        if w_chars is not None and space.isinstance_w(w_chars, space.w_unicode):
            self_as_uni = unicode_from_encoded_object(space, self, None, None)
            return self_as_uni.descr_lstrip(space, w_chars)
        return self._StringMethods_descr_lstrip(space, w_chars)

    _StringMethods_descr_rstrip = descr_rstrip
    def descr_rstrip(self, space, w_chars=None):
        if w_chars is not None and space.isinstance_w(w_chars, space.w_unicode):
            self_as_uni = unicode_from_encoded_object(space, self, None, None)
            return self_as_uni.descr_rstrip(space, w_chars)
        return self._StringMethods_descr_rstrip(space, w_chars)

    _StringMethods_descr_count = descr_count
    def descr_count(self, space, w_sub, w_start=None, w_end=None):
        if space.isinstance_w(w_sub, space.w_unicode):
            self_as_uni = unicode_from_encoded_object(space, self, None, None)
            return self_as_uni.descr_count(space, w_sub, w_start, w_end)
        return self._StringMethods_descr_count(space, w_sub, w_start, w_end)

    _StringMethods_descr_find = descr_find
    def descr_find(self, space, w_sub, w_start=None, w_end=None):
        if space.isinstance_w(w_sub, space.w_unicode):
            self_as_uni = unicode_from_encoded_object(space, self, None, None)
            return self_as_uni.descr_find(space, w_sub, w_start, w_end)
        return self._StringMethods_descr_find(space, w_sub, w_start, w_end)

    _StringMethods_descr_rfind = descr_rfind
    def descr_rfind(self, space, w_sub, w_start=None, w_end=None):
        if space.isinstance_w(w_sub, space.w_unicode):
            self_as_uni = unicode_from_encoded_object(space, self, None, None)
            return self_as_uni.descr_rfind(space, w_sub, w_start, w_end)
        return self._StringMethods_descr_rfind(space, w_sub, w_start, w_end)

    _StringMethods_descr_index = descr_index
    def descr_index(self, space, w_sub, w_start=None, w_end=None):
        if space.isinstance_w(w_sub, space.w_unicode):
            self_as_uni = unicode_from_encoded_object(space, self, None, None)
            return self_as_uni.descr_index(space, w_sub, w_start, w_end)
        return self._StringMethods_descr_index(space, w_sub, w_start, w_end)

    _StringMethods_descr_rindex = descr_rindex
    def descr_rindex(self, space, w_sub, w_start=None, w_end=None):
        if space.isinstance_w(w_sub, space.w_unicode):
            self_as_uni = unicode_from_encoded_object(space, self, None, None)
            return self_as_uni.descr_rindex(space, w_sub, w_start, w_end)
        return self._StringMethods_descr_rindex(space, w_sub, w_start, w_end)

    _StringMethods_descr_partition = descr_partition
    def descr_partition(self, space, w_sub):
        if space.isinstance_w(w_sub, space.w_unicode):
            self_as_uni = unicode_from_encoded_object(space, self, None, None)
            return self_as_uni.descr_partition(space, w_sub)
        return self._StringMethods_descr_partition(space, w_sub)

    _StringMethods_descr_rpartition = descr_rpartition
    def descr_rpartition(self, space, w_sub):
        if space.isinstance_w(w_sub, space.w_unicode):
            self_as_uni = unicode_from_encoded_object(space, self, None, None)
            return self_as_uni.descr_rpartition(space, w_sub)
        return self._StringMethods_descr_rpartition(space, w_sub)

    def _join_return_one(self, space, w_obj):
        return (space.is_w(space.type(w_obj), space.w_bytes) or
                space.is_w(space.type(w_obj), space.w_unicode))

    def _join_check_item(self, space, w_obj):
        if space.isinstance_w(w_obj, space.w_bytes):
            return 0
        if space.isinstance_w(w_obj, space.w_unicode):
            return 2
        return 1

    def _join_autoconvert(self, space, list_w):
        # we need to rebuild w_list here, because the original
        # w_list might be an iterable which we already consumed
        w_list = space.newlist(list_w)
        w_u = space.call_function(space.w_unicode, self)
        return space.call_method(w_u, "join", w_list)

    def descr_lower(self, space):
        return W_BytesObject(self._value.lower())

    def descr_upper(self, space):
        return W_BytesObject(self._value.upper())

    def descr_formatter_parser(self, space):
        from pypy.objspace.std.newformat import str_template_formatter
        tformat = str_template_formatter(space, space.bytes_w(self))
        return tformat.formatter_parser()

    def descr_formatter_field_name_split(self, space):
        from pypy.objspace.std.newformat import str_template_formatter
        tformat = str_template_formatter(space, space.bytes_w(self))
        return tformat.formatter_field_name_split()


def _create_list_from_bytes(value):
    # need this helper function to allow the jit to look inside and inline
    # listview_bytes
    return [s for s in value]

W_BytesObject.EMPTY = W_BytesObject('')


W_BytesObject.typedef = TypeDef(
    "str", basestring_typedef, None, "read",
    __new__ = interp2app(W_BytesObject.descr_new),
    __doc__ = """str(object='') -> string

    Return a nice string representation of the object.
    If the argument is a string, the return value is the same object.
    """,

    __repr__ = interpindirect2app(W_AbstractBytesObject.descr_repr),
    __str__ = interpindirect2app(W_AbstractBytesObject.descr_str),
    __hash__ = interpindirect2app(W_AbstractBytesObject.descr_hash),

    __eq__ = interpindirect2app(W_AbstractBytesObject.descr_eq),
    __ne__ = interpindirect2app(W_AbstractBytesObject.descr_ne),
    __lt__ = interpindirect2app(W_AbstractBytesObject.descr_lt),
    __le__ = interpindirect2app(W_AbstractBytesObject.descr_le),
    __gt__ = interpindirect2app(W_AbstractBytesObject.descr_gt),
    __ge__ = interpindirect2app(W_AbstractBytesObject.descr_ge),

    __len__ = interpindirect2app(W_AbstractBytesObject.descr_len),
    __contains__ = interpindirect2app(W_AbstractBytesObject.descr_contains),

    __add__ = interpindirect2app(W_AbstractBytesObject.descr_add),
    __mul__ = interpindirect2app(W_AbstractBytesObject.descr_mul),
    __rmul__ = interpindirect2app(W_AbstractBytesObject.descr_rmul),

    __getitem__ = interpindirect2app(W_AbstractBytesObject.descr_getitem),
    __getslice__ = interpindirect2app(W_AbstractBytesObject.descr_getslice),

    capitalize = interpindirect2app(W_AbstractBytesObject.descr_capitalize),
    center = interpindirect2app(W_AbstractBytesObject.descr_center),
    count = interpindirect2app(W_AbstractBytesObject.descr_count),
    decode = interpindirect2app(W_AbstractBytesObject.descr_decode),
    encode = interpindirect2app(W_AbstractBytesObject.descr_encode),
    expandtabs = interpindirect2app(W_AbstractBytesObject.descr_expandtabs),
    find = interpindirect2app(W_AbstractBytesObject.descr_find),
    rfind = interpindirect2app(W_AbstractBytesObject.descr_rfind),
    index = interpindirect2app(W_AbstractBytesObject.descr_index),
    rindex = interpindirect2app(W_AbstractBytesObject.descr_rindex),
    isalnum = interpindirect2app(W_AbstractBytesObject.descr_isalnum),
    isalpha = interpindirect2app(W_AbstractBytesObject.descr_isalpha),
    isdigit = interpindirect2app(W_AbstractBytesObject.descr_isdigit),
    islower = interpindirect2app(W_AbstractBytesObject.descr_islower),
    isspace = interpindirect2app(W_AbstractBytesObject.descr_isspace),
    istitle = interpindirect2app(W_AbstractBytesObject.descr_istitle),
    isupper = interpindirect2app(W_AbstractBytesObject.descr_isupper),
    join = interpindirect2app(W_AbstractBytesObject.descr_join),
    ljust = interpindirect2app(W_AbstractBytesObject.descr_ljust),
    rjust = interpindirect2app(W_AbstractBytesObject.descr_rjust),
    lower = interpindirect2app(W_AbstractBytesObject.descr_lower),
    partition = interpindirect2app(W_AbstractBytesObject.descr_partition),
    rpartition = interpindirect2app(W_AbstractBytesObject.descr_rpartition),
    replace = interpindirect2app(W_AbstractBytesObject.descr_replace),
    split = interpindirect2app(W_AbstractBytesObject.descr_split),
    rsplit = interpindirect2app(W_AbstractBytesObject.descr_rsplit),
    splitlines = interpindirect2app(W_AbstractBytesObject.descr_splitlines),
    startswith = interpindirect2app(W_AbstractBytesObject.descr_startswith),
    endswith = interpindirect2app(W_AbstractBytesObject.descr_endswith),
    strip = interpindirect2app(W_AbstractBytesObject.descr_strip),
    lstrip = interpindirect2app(W_AbstractBytesObject.descr_lstrip),
    rstrip = interpindirect2app(W_AbstractBytesObject.descr_rstrip),
    swapcase = interpindirect2app(W_AbstractBytesObject.descr_swapcase),
    title = interpindirect2app(W_AbstractBytesObject.descr_title),
    translate = interpindirect2app(W_AbstractBytesObject.descr_translate),
    upper = interpindirect2app(W_AbstractBytesObject.descr_upper),
    zfill = interpindirect2app(W_AbstractBytesObject.descr_zfill),
    __buffer__ = interp2app(W_BytesObject.descr_getbuffer),

    format = interpindirect2app(W_BytesObject.descr_format),
    __format__ = interpindirect2app(W_BytesObject.descr__format__),
    __mod__ = interpindirect2app(W_BytesObject.descr_mod),
    __rmod__ = interpindirect2app(W_BytesObject.descr_rmod),
    __getnewargs__ = interpindirect2app(
        W_AbstractBytesObject.descr_getnewargs),
    _formatter_parser = interp2app(W_BytesObject.descr_formatter_parser),
    _formatter_field_name_split =
        interp2app(W_BytesObject.descr_formatter_field_name_split),
)
W_BytesObject.typedef.flag_sequence_bug_compat = True


@jit.elidable
def string_escape_encode(s, quote):
    buf = StringBuilder(len(s) + 2)

    buf.append(quote)
    startslice = 0

    for i in range(len(s)):
        c = s[i]
        use_bs_char = False # character quoted by backspace

        if c == '\\' or c == quote:
            bs_char = c
            use_bs_char = True
        elif c == '\t':
            bs_char = 't'
            use_bs_char = True
        elif c == '\r':
            bs_char = 'r'
            use_bs_char = True
        elif c == '\n':
            bs_char = 'n'
            use_bs_char = True
        elif not '\x20' <= c < '\x7f':
            n = ord(c)
            if i != startslice:
                buf.append_slice(s, startslice, i)
            startslice = i + 1
            buf.append('\\x')
            buf.append("0123456789abcdef"[n >> 4])
            buf.append("0123456789abcdef"[n & 0xF])

        if use_bs_char:
            if i != startslice:
                buf.append_slice(s, startslice, i)
            startslice = i + 1
            buf.append('\\')
            buf.append(bs_char)

    if len(s) != startslice:
        buf.append_slice(s, startslice, len(s))

    buf.append(quote)

    return buf.build()
