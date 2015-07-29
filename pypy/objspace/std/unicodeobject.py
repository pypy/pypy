"""The builtin unicode implementation"""

from rpython.rlib.objectmodel import (
    compute_hash, compute_unique_id, import_from_mixin)
from rpython.rlib.buffer import StringBuffer
from rpython.rlib.rstring import StringBuilder, UnicodeBuilder
from rpython.rlib.runicode import (
    make_unicode_escape_function, str_decode_ascii, str_decode_utf_8,
    unicode_encode_ascii, unicode_encode_utf_8, fast_str_decode_ascii)

from pypy.interpreter import unicodehelper
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import (
    WrappedDefault, interp2app, interpindirect2app, unwrap_spec)
from pypy.interpreter.typedef import TypeDef
from pypy.module.unicodedata import unicodedb
from pypy.objspace.std import newformat
from pypy.objspace.std.basestringtype import basestring_typedef
from pypy.objspace.std.formatting import mod_format
from pypy.objspace.std.stringmethods import StringMethods

__all__ = ['W_UnicodeObject', 'wrapunicode', 'plain_str2unicode',
           'encode_object', 'decode_object', 'unicode_from_object',
           'unicode_from_string', 'unicode_to_decimal_w']


class W_AbstractUnicodeObject(W_Root):
    __slots__ = ()

    def is_w(self, space, w_other):
        if not isinstance(w_other, W_AbstractUnicodeObject):
            return False
        if self is w_other:
            return True
        if self.user_overridden_class or w_other.user_overridden_class:
            return False
        return space.unicode_w(self) is space.unicode_w(w_other)

    def immutable_unique_id(self, space):
        if self.user_overridden_class:
            return None
        return space.wrap(compute_unique_id(space.unicode_w(self)))

    def str_w(self, space):
        return space.str_w(space.str(self))

    charbuf_w = str_w

    def descr_add(self, space, w_other):
        """x.__add__(y) <==> x+y"""
        raise NotImplementedError

    def descr_contains(self, space, w_sub):
        """x.__contains__(y) <==> y in x"""
        raise NotImplementedError

    def descr_eq(self, space, w_other):
        """x.__eq__(y) <==> x==y"""
        raise NotImplementedError

    def descr__format__(self, space, w_format_spec):
        """S.__format__(format_spec) -> string

        Return a formatted version of S as described by format_spec.
        """
        raise NotImplementedError

    def descr_ge(self, space, w_other):
        """x.__ge__(y) <==> x>=y"""
        raise NotImplementedError

    def descr_getitem(self, space, w_index):
        """x.__getitem__(y) <==> x[y]"""
        raise NotImplementedError

    def descr_getnewargs(self, space):
        ""
        raise NotImplementedError

    def descr_getslice(self, space, w_start, w_stop):
        """x.__getslice__(i, j) <==> x[i:j]

        Use of negative indices is not supported.
        """
        raise NotImplementedError

    def descr_gt(self, space, w_other):
        """x.__gt__(y) <==> x>y"""
        raise NotImplementedError

    def descr_hash(self, space):
        """x.__hash__() <==> hash(x)"""
        raise NotImplementedError

    def descr_le(self, space, w_other):
        """x.__le__(y) <==> x<=y"""
        raise NotImplementedError

    def descr_len(self, space):
        """x.__len__() <==> len(x)"""
        raise NotImplementedError

    def descr_lt(self, space, w_other):
        """x.__lt__(y) <==> x<y"""
        raise NotImplementedError

    def descr_mod(self, space, w_values):
        """x.__mod__(y) <==> x%y"""
        raise NotImplementedError

    def descr_mul(self, space, w_times):
        """x.__mul__(n) <==> x*n"""
        raise NotImplementedError

    def descr_ne(self, space, w_other):
        """x.__ne__(y) <==> x!=y"""
        raise NotImplementedError

    def descr_repr(self, space):
        """x.__repr__() <==> repr(x)"""
        raise NotImplementedError

    def descr_rmod(self, space, w_values):
        """x.__rmod__(y) <==> y%x"""
        raise NotImplementedError

    def descr_rmul(self, space, w_times):
        """x.__rmul__(n) <==> n*x"""
        raise NotImplementedError

    def descr_str(self, space):
        """x.__str__() <==> str(x)"""
        raise NotImplementedError

    def descr_capitalize(self, space):
        """S.capitalize() -> unicode

        Return a capitalized version of S, i.e. make the first character
        have upper case and the rest lower case.
        """
        raise NotImplementedError

    @unwrap_spec(width=int, w_fillchar=WrappedDefault(' '))
    def descr_center(self, space, width, w_fillchar):
        """S.center(width[, fillchar]) -> unicode

        Return S centered in a Unicode string of length width. Padding is
        done using the specified fill character (default is a space).
        """
        raise NotImplementedError

    def descr_count(self, space, w_sub, w_start=None, w_end=None):
        """S.count(sub[, start[, end]]) -> int

        Return the number of non-overlapping occurrences of substring sub in
        Unicode string S[start:end].  Optional arguments start and end are
        interpreted as in slice notation.
        """
        raise NotImplementedError

    def descr_decode(self, space, w_encoding=None, w_errors=None):
        """S.decode(encoding=None, errors='strict') -> string or unicode

        Decode S using the codec registered for encoding. encoding defaults
        to the default encoding. errors may be given to set a different error
        handling scheme. Default is 'strict' meaning that encoding errors raise
        a UnicodeDecodeError. Other possible values are 'ignore' and 'replace'
        as well as any other name registered with codecs.register_error that is
        able to handle UnicodeDecodeErrors.
        """
        raise NotImplementedError

    def descr_encode(self, space, w_encoding=None, w_errors=None):
        """S.encode(encoding=None, errors='strict') -> string or unicode

        Encode S using the codec registered for encoding. encoding defaults
        to the default encoding. errors may be given to set a different error
        handling scheme. Default is 'strict' meaning that encoding errors raise
        a UnicodeEncodeError. Other possible values are 'ignore', 'replace' and
        'xmlcharrefreplace' as well as any other name registered with
        codecs.register_error that can handle UnicodeEncodeErrors.
        """
        raise NotImplementedError

    def descr_endswith(self, space, w_suffix, w_start=None, w_end=None):
        """S.endswith(suffix[, start[, end]]) -> bool

        Return True if S ends with the specified suffix, False otherwise.
        With optional start, test S beginning at that position.
        With optional end, stop comparing S at that position.
        suffix can also be a tuple of strings to try.
        """
        raise NotImplementedError

    @unwrap_spec(tabsize=int)
    def descr_expandtabs(self, space, tabsize=8):
        """S.expandtabs([tabsize]) -> unicode

        Return a copy of S where all tab characters are expanded using spaces.
        If tabsize is not given, a tab size of 8 characters is assumed.
        """
        raise NotImplementedError

    def descr_find(self, space, w_sub, w_start=None, w_end=None):
        """S.find(sub[, start[, end]]) -> int

        Return the lowest index in S where substring sub is found,
        such that sub is contained within S[start:end].  Optional
        arguments start and end are interpreted as in slice notation.

        Return -1 on failure.
        """
        raise NotImplementedError

    def descr_format(self, space, __args__):
        """S.format(*args, **kwargs) -> unicode

        Return a formatted version of S, using substitutions from args and
        kwargs.  The substitutions are identified by braces ('{' and '}').
        """
        raise NotImplementedError

    def descr_index(self, space, w_sub, w_start=None, w_end=None):
        """S.index(sub[, start[, end]]) -> int

        Like S.find() but raise ValueError when the substring is not found.
        """
        raise NotImplementedError

    def descr_isalnum(self, space):
        """S.isalnum() -> bool

        Return True if all characters in S are alphanumeric
        and there is at least one character in S, False otherwise.
        """
        raise NotImplementedError

    def descr_isalpha(self, space):
        """S.isalpha() -> bool

        Return True if all characters in S are alphabetic
        and there is at least one character in S, False otherwise.
        """
        raise NotImplementedError

    def descr_isdecimal(self, space):
        """S.isdecimal() -> bool

        Return True if there are only decimal characters in S,
        False otherwise.
        """
        raise NotImplementedError

    def descr_isdigit(self, space):
        """S.isdigit() -> bool

        Return True if all characters in S are digits
        and there is at least one character in S, False otherwise.
        """
        raise NotImplementedError

    def descr_islower(self, space):
        """S.islower() -> bool

        Return True if all cased characters in S are lowercase and there is
        at least one cased character in S, False otherwise.
        """
        raise NotImplementedError

    def descr_isnumeric(self, space):
        """S.isnumeric() -> bool

        Return True if there are only numeric characters in S,
        False otherwise.
        """
        raise NotImplementedError

    def descr_isspace(self, space):
        """S.isspace() -> bool

        Return True if all characters in S are whitespace
        and there is at least one character in S, False otherwise.
        """
        raise NotImplementedError

    def descr_istitle(self, space):
        """S.istitle() -> bool

        Return True if S is a titlecased string and there is at least one
        character in S, i.e. upper- and titlecase characters may only
        follow uncased characters and lowercase characters only cased ones.
        Return False otherwise.
        """
        raise NotImplementedError

    def descr_isupper(self, space):
        """S.isupper() -> bool

        Return True if all cased characters in S are uppercase and there is
        at least one cased character in S, False otherwise.
        """
        raise NotImplementedError

    def descr_join(self, space, w_list):
        """S.join(iterable) -> unicode

        Return a string which is the concatenation of the strings in the
        iterable.  The separator between elements is S.
        """
        raise NotImplementedError

    @unwrap_spec(width=int, w_fillchar=WrappedDefault(' '))
    def descr_ljust(self, space, width, w_fillchar):
        """S.ljust(width[, fillchar]) -> int

        Return S left-justified in a Unicode string of length width. Padding is
        done using the specified fill character (default is a space).
        """
        raise NotImplementedError

    def descr_lower(self, space):
        """S.lower() -> unicode

        Return a copy of the string S converted to lowercase.
        """
        raise NotImplementedError

    def descr_lstrip(self, space, w_chars=None):
        """S.lstrip([chars]) -> unicode

        Return a copy of the string S with leading whitespace removed.
        If chars is given and not None, remove characters in chars instead.
        If chars is a str, it will be converted to unicode before stripping
        """
        raise NotImplementedError

    def descr_partition(self, space, w_sub):
        """S.partition(sep) -> (head, sep, tail)

        Search for the separator sep in S, and return the part before it,
        the separator itself, and the part after it.  If the separator is not
        found, return S and two empty strings.
        """
        raise NotImplementedError

    @unwrap_spec(count=int)
    def descr_replace(self, space, w_old, w_new, count=-1):
        """S.replace(old, new[, count]) -> unicode

        Return a copy of S with all occurrences of substring
        old replaced by new.  If the optional argument count is
        given, only the first count occurrences are replaced.
        """
        raise NotImplementedError

    def descr_rfind(self, space, w_sub, w_start=None, w_end=None):
        """S.rfind(sub[, start[, end]]) -> int

        Return the highest index in S where substring sub is found,
        such that sub is contained within S[start:end].  Optional
        arguments start and end are interpreted as in slice notation.

        Return -1 on failure.
        """
        raise NotImplementedError

    def descr_rindex(self, space, w_sub, w_start=None, w_end=None):
        """S.rindex(sub[, start[, end]]) -> int

        Like S.rfind() but raise ValueError when the substring is not found.
        """
        raise NotImplementedError

    @unwrap_spec(width=int, w_fillchar=WrappedDefault(' '))
    def descr_rjust(self, space, width, w_fillchar):
        """S.rjust(width[, fillchar]) -> unicode

        Return S right-justified in a Unicode string of length width. Padding
        is done using the specified fill character (default is a space).
        """
        raise NotImplementedError

    def descr_rpartition(self, space, w_sub):
        """S.rpartition(sep) -> (head, sep, tail)

        Search for the separator sep in S, starting at the end of S, and return
        the part before it, the separator itself, and the part after it.  If
        the separator is not found, return two empty strings and S.
        """
        raise NotImplementedError

    @unwrap_spec(maxsplit=int)
    def descr_rsplit(self, space, w_sep=None, maxsplit=-1):
        """S.rsplit(sep=None, maxsplit=-1) -> list of strings

        Return a list of the words in S, using sep as the
        delimiter string, starting at the end of the string and
        working to the front.  If maxsplit is given, at most maxsplit
        splits are done. If sep is not specified, any whitespace string
        is a separator.
        """
        raise NotImplementedError

    def descr_rstrip(self, space, w_chars=None):
        """S.rstrip([chars]) -> unicode

        Return a copy of the string S with trailing whitespace removed.
        If chars is given and not None, remove characters in chars instead.
        If chars is a str, it will be converted to unicode before stripping
        """
        raise NotImplementedError

    @unwrap_spec(maxsplit=int)
    def descr_split(self, space, w_sep=None, maxsplit=-1):
        """S.split(sep=None, maxsplit=-1) -> list of strings

        Return a list of the words in S, using sep as the
        delimiter string.  If maxsplit is given, at most maxsplit
        splits are done. If sep is not specified or is None, any
        whitespace string is a separator and empty strings are
        removed from the result.
        """
        raise NotImplementedError

    @unwrap_spec(keepends=bool)
    def descr_splitlines(self, space, keepends=False):
        """S.splitlines(keepends=False) -> list of strings

        Return a list of the lines in S, breaking at line boundaries.
        Line breaks are not included in the resulting list unless keepends
        is given and true.
        """
        raise NotImplementedError

    def descr_startswith(self, space, w_prefix, w_start=None, w_end=None):
        """S.startswith(prefix[, start[, end]]) -> bool

        Return True if S starts with the specified prefix, False otherwise.
        With optional start, test S beginning at that position.
        With optional end, stop comparing S at that position.
        prefix can also be a tuple of strings to try.
        """
        raise NotImplementedError

    def descr_strip(self, space, w_chars=None):
        """S.strip([chars]) -> unicode

        Return a copy of the string S with leading and trailing
        whitespace removed.
        If chars is given and not None, remove characters in chars instead.
        If chars is a str, it will be converted to unicode before stripping
        """
        raise NotImplementedError

    def descr_swapcase(self, space):
        """S.swapcase() -> unicode

        Return a copy of S with uppercase characters converted to lowercase
        and vice versa.
        """
        raise NotImplementedError

    def descr_title(self, space):
        """S.title() -> unicode

        Return a titlecased version of S, i.e. words start with title case
        characters, all remaining cased characters have lower case.
        """
        raise NotImplementedError

    def descr_translate(self, space, w_table):
        """S.translate(table) -> unicode

        Return a copy of the string S, where all characters have been mapped
        through the given translation table, which must be a mapping of
        Unicode ordinals to Unicode ordinals, Unicode strings or None.
        Unmapped characters are left untouched. Characters mapped to None
        are deleted.
        """
        raise NotImplementedError

    def descr_upper(self, space):
        """S.upper() -> unicode

        Return a copy of S converted to uppercase.
        """
        raise NotImplementedError

    @unwrap_spec(width=int)
    def descr_zfill(self, space, width):
        """S.zfill(width) -> unicode

        Pad a numeric string S with zeros on the left, to fill a field
        of the specified width. The string S is never truncated.
        """

    def readbuf_w(self, space):
        from rpython.rlib.rstruct.unichar import pack_unichar, UNICODE_SIZE
        value = self.unicode_w(space)
        builder = StringBuilder(len(value) * UNICODE_SIZE)
        for unich in value:
            pack_unichar(unich, builder)
        return StringBuffer(builder.build())

    def descr_formatter_parser(self, space):
        from pypy.objspace.std.newformat import unicode_template_formatter
        tformat = unicode_template_formatter(space, self.unicode_w(space))
        return tformat.formatter_parser()

    def descr_formatter_field_name_split(self, space):
        from pypy.objspace.std.newformat import unicode_template_formatter
        tformat = unicode_template_formatter(space, self.unicode_w(space))
        return tformat.formatter_field_name_split()


class W_UnicodeObject(W_AbstractUnicodeObject):
    import_from_mixin(StringMethods)
    _immutable_fields_ = ['_value']

    def __init__(w_self, unistr):
        assert isinstance(unistr, unicode)
        w_self._value = unistr

    def __repr__(w_self):
        """representation for debugging purposes"""
        return "%s(%r)" % (w_self.__class__.__name__, w_self._value)

    def unwrap(w_self, space):
        # for testing
        return w_self._value

    def create_if_subclassed(w_self):
        if type(w_self) is W_UnicodeObject:
            return w_self
        return W_UnicodeObject(w_self._value)

    def unicode_w(self, space):
        return self._value

    def writebuf_w(self, space):
        raise OperationError(space.w_TypeError, space.wrap(
            "cannot use unicode as modifiable buffer"))

    def listview_unicode(w_self):
        return _create_list_from_unicode(w_self._value)

    def ord(self, space):
        if len(self._value) != 1:
            raise oefmt(space.w_TypeError,
                         "ord() expected a character, but string of length %d "
                         "found", len(self._value))
        return space.wrap(ord(self._value[0]))

    def _new(self, value):
        return W_UnicodeObject(value)

    def _new_concat(self, space, value1, value2):
        if space.config.objspace.std.withstrbuf:
            from pypy.objspace.std.unibufobject import W_UnicodeBufferObject
            builder = UnicodeBuilder(len(value1) + len(value2))
            builder.append(value1)
            builder.append(value2)
            return W_UnicodeBufferObject(builder)
        return self._new(value1 + value2)

    def _new_from_list(self, value):
        return W_UnicodeObject(u''.join(value))

    def _empty(self):
        return W_UnicodeObject.EMPTY

    def _len(self):
        return len(self._value)

    _val = unicode_w

    @staticmethod
    def _use_rstr_ops(space, w_other):
        # Always return true because we always need to copy the other
        # operand(s) before we can do comparisons
        return True

    @staticmethod
    def _op_val(space, w_other):
        from pypy.objspace.std.bytesobject import W_AbstractBytesObject

        if isinstance(w_other, W_AbstractUnicodeObject):
            return w_other.unicode_w(space)
        if isinstance(w_other, W_AbstractBytesObject):
            return unicode_from_string(space, w_other)._value
        return unicode_from_encoded_object(
            space, w_other, None, "strict")._value

    @staticmethod
    def _chr(char):
        assert len(char) == 1
        return unichr(ord(char[0]))

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

    def _islinebreak(self, ch):
        return unicodedb.islinebreak(ord(ch))

    def _upper(self, ch):
        return unichr(unicodedb.toupper(ord(ch)))

    def _lower(self, ch):
        return unichr(unicodedb.tolower(ord(ch)))

    def _title(self, ch):
        return unichr(unicodedb.totitle(ord(ch)))

    def _newlist_unwrapped(self, space, lst):
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
             space.findattr(w_obj, space.wrap('__unicode__')) is None)):
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

        value = w_value.unicode_w(space)
        w_newobj = space.allocate_instance(W_UnicodeObject, w_unicodetype)
        W_UnicodeObject.__init__(w_newobj, value)
        return w_newobj

    def descr_repr(self, space):
        chars = self._value
        size = len(chars)
        s = _repr_function(chars, size, "strict")
        return space.wrap(s)

    def descr_str(self, space):
        return encode_object(space, self, None, None)

    def descr_hash(self, space):
        x = compute_hash(self._value)
        return space.wrap(x)

    def descr_eq(self, space, w_other):
        try:
            res = self._val(space) == self._op_val(space, w_other)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            if (e.match(space, space.w_UnicodeDecodeError) or
                e.match(space, space.w_UnicodeEncodeError)):
                msg = ("Unicode equal comparison failed to convert both "
                       "arguments to Unicode - interpreting them as being "
                       "unequal")
                space.warn(space.wrap(msg), space.w_UnicodeWarning)
                return space.w_False
            raise
        return space.newbool(res)

    def descr_ne(self, space, w_other):
        try:
            res = self._val(space) != self._op_val(space, w_other)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            if (e.match(space, space.w_UnicodeDecodeError) or
                e.match(space, space.w_UnicodeEncodeError)):
                msg = ("Unicode unequal comparison failed to convert both "
                       "arguments to Unicode - interpreting them as being "
                       "unequal")
                space.warn(space.wrap(msg), space.w_UnicodeWarning)
                return space.w_True
            raise
        return space.newbool(res)

    def descr_lt(self, space, w_other):
        try:
            res = self._val(space) < self._op_val(space, w_other)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise
        return space.newbool(res)

    def descr_le(self, space, w_other):
        try:
            res = self._val(space) <= self._op_val(space, w_other)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise
        return space.newbool(res)

    def descr_gt(self, space, w_other):
        try:
            res = self._val(space) > self._op_val(space, w_other)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise
        return space.newbool(res)

    def descr_ge(self, space, w_other):
        try:
            res = self._val(space) >= self._op_val(space, w_other)
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
        return formatter.format_string(self2.unicode_w(space))

    def descr_mod(self, space, w_values):
        return mod_format(space, self, w_values, do_unicode=True)

    def descr_translate(self, space, w_table):
        selfvalue = self._value
        w_sys = space.getbuiltinmodule('sys')
        maxunicode = space.int_w(space.getattr(w_sys,
                                               space.wrap("maxunicode")))
        result = []
        for unichar in selfvalue:
            try:
                w_newval = space.getitem(w_table, space.wrap(ord(unichar)))
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
                    result.append(space.unicode_w(w_newval))
                else:
                    raise oefmt(space.w_TypeError,
                                "character mapping must return integer, None "
                                "or unicode")
        return W_UnicodeObject(u''.join(result))

    def descr_encode(self, space, w_encoding=None, w_errors=None):
        encoding, errors = _get_encoding_and_errors(space, w_encoding,
                                                    w_errors)
        return encode_object(space, self, encoding, errors)

    _StringMethods_descr_join = descr_join
    def descr_join(self, space, w_list):
        l = space.listview_unicode(w_list)
        if l is not None:
            if len(l) == 1:
                return space.wrap(l[0])
            return space.wrap(self._val(space).join(l))
        return self._StringMethods_descr_join(space, w_list)

    def _join_return_one(self, space, w_obj):
        return space.is_w(space.type(w_obj), space.w_unicode)

    def _join_check_item(self, space, w_obj):
        if (space.isinstance_w(w_obj, space.w_str) or
            space.isinstance_w(w_obj, space.w_unicode)):
            return 0
        return 1

    def descr_isdecimal(self, space):
        return self._is_generic(space, '_isdecimal')

    def descr_isnumeric(self, space):
        return self._is_generic(space, '_isnumeric')

    def descr_islower(self, space):
        cased = False
        for uchar in self._value:
            if (unicodedb.isupper(ord(uchar)) or
                unicodedb.istitle(ord(uchar))):
                return space.w_False
            if not cased and unicodedb.islower(ord(uchar)):
                cased = True
        return space.newbool(cased)

    def descr_isupper(self, space):
        cased = False
        for uchar in self._value:
            if (unicodedb.islower(ord(uchar)) or
                unicodedb.istitle(ord(uchar))):
                return space.w_False
            if not cased and unicodedb.isupper(ord(uchar)):
                cased = True
        return space.newbool(cased)

    def _starts_ends_overflow(self, prefix):
        return len(prefix) == 0


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
                    space.wrap('ascii'),
                    space.wrap(s),
                    space.wrap(i),
                    space.wrap(i+1),
                    space.wrap("ordinal not in range(128)")]))
        assert False, "unreachable"


# stuff imported from bytesobject for interoperability


# ____________________________________________________________

def getdefaultencoding(space):
    return space.sys.defaultencoding


def _get_encoding_and_errors(space, w_encoding, w_errors):
    encoding = None if space.is_none(w_encoding) else space.str_w(w_encoding)
    errors = None if space.is_none(w_errors) else space.str_w(w_errors)
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
                    u = space.unicode_w(w_object)
                    eh = unicodehelper.raise_unicode_exception_encode
                    return space.wrap(unicode_encode_ascii(
                            u, len(u), None, errorhandler=eh))
                if encoding == 'utf-8':
                    u = space.unicode_w(w_object)
                    eh = unicodehelper.raise_unicode_exception_encode
                    return space.wrap(unicode_encode_utf_8(
                            u, len(u), None, errorhandler=eh,
                            allow_surrogates=True))
            except unicodehelper.RUnicodeEncodeError, ue:
                raise OperationError(space.w_UnicodeEncodeError,
                                     space.newtuple([
                    space.wrap(ue.encoding),
                    space.wrap(ue.object),
                    space.wrap(ue.start),
                    space.wrap(ue.end),
                    space.wrap(ue.reason)]))
        from pypy.module._codecs.interp_codecs import lookup_codec
        w_encoder = space.getitem(lookup_codec(space, encoding), space.wrap(0))
    if errors is None:
        w_errors = space.wrap('strict')
    else:
        w_errors = space.wrap(errors)
    w_restuple = space.call_function(w_encoder, w_object, w_errors)
    w_retval = space.getitem(w_restuple, space.wrap(0))
    if not space.isinstance_w(w_retval, space.w_str):
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
                u = fast_str_decode_ascii(s)
            except ValueError:
                eh = unicodehelper.decode_error_handler(space)
                u = str_decode_ascii(     # try again, to get the error right
                    s, len(s), None, final=True, errorhandler=eh)[0]
            return space.wrap(u)
        if encoding == 'utf-8':
            s = space.charbuf_w(w_obj)
            eh = unicodehelper.decode_error_handler(space)
            return space.wrap(str_decode_utf_8(
                    s, len(s), None, final=True, errorhandler=eh,
                    allow_surrogates=True)[0])
    w_codecs = space.getbuiltinmodule("_codecs")
    w_decode = space.getattr(w_codecs, space.wrap("decode"))
    if errors is None:
        w_retval = space.call_function(w_decode, w_obj, space.wrap(encoding))
    else:
        w_retval = space.call_function(w_decode, w_obj, space.wrap(encoding),
                                       space.wrap(errors))
    return w_retval


def unicode_from_encoded_object(space, w_obj, encoding, errors):
    # explicitly block bytearray on 2.7
    from .bytearrayobject import W_BytearrayObject
    if isinstance(w_obj, W_BytearrayObject):
        raise oefmt(space.w_TypeError, "decoding bytearray is not supported")

    w_retval = decode_object(space, w_obj, encoding, errors)
    if not isinstance(w_retval, W_UnicodeObject):
        if not space.isinstance_w(w_retval, space.w_unicode):
            raise oefmt(space.w_TypeError,
                        "decoder did not return an unicode object (type '%T')",
                        w_retval)
        w_retval = W_UnicodeObject(w_retval.unicode_w(space))
    return w_retval


def unicode_from_object(space, w_obj):
    if space.is_w(space.type(w_obj), space.w_unicode):
        return w_obj
    elif space.is_w(space.type(w_obj), space.w_str):
        w_res = w_obj
    else:
        w_unicode_method = space.lookup(w_obj, "__unicode__")
        # obscure workaround: for the next two lines see
        # test_unicode_conversion_with__str__
        if w_unicode_method is None:
            if space.isinstance_w(w_obj, space.w_unicode):
                return space.wrap(space.unicode_w(w_obj))
            w_unicode_method = space.lookup(w_obj, "__str__")
        if w_unicode_method is not None:
            w_res = space.get_and_call_function(w_unicode_method, w_obj)
        else:
            w_res = space.str(w_obj)
        if space.isinstance_w(w_res, space.w_unicode):
            return w_res
    return unicode_from_encoded_object(space, w_res, None, "strict")


def unicode_from_string(space, w_str):
    # this is a performance and bootstrapping hack
    encoding = getdefaultencoding(space)
    if encoding != 'ascii':
        return unicode_from_encoded_object(space, w_str, encoding, "strict")
    s = space.str_w(w_str)
    try:
        return W_UnicodeObject(s.decode("ascii"))
    except UnicodeDecodeError:
        # raising UnicodeDecodeError is messy, "please crash for me"
        return unicode_from_encoded_object(space, w_str, "ascii", "strict")


W_UnicodeObject.typedef = TypeDef(
    "unicode", basestring_typedef,
    __new__ = interp2app(W_UnicodeObject.descr_new),
    __doc__ = """unicode(object='') -> unicode object
    unicode(string[, encoding[, errors]]) -> unicode object

    Create a new Unicode object from the given encoded string.
    encoding defaults to the current default string encoding.
    errors can be 'strict', 'replace' or 'ignore' and defaults to 'strict'.
    """,

    __repr__ = interpindirect2app(W_AbstractUnicodeObject.descr_repr),
    __str__ = interpindirect2app(W_AbstractUnicodeObject.descr_str),
    __hash__ = interpindirect2app(W_AbstractUnicodeObject.descr_hash),

    __eq__ = interpindirect2app(W_AbstractUnicodeObject.descr_eq),
    __ne__ = interpindirect2app(W_AbstractUnicodeObject.descr_ne),
    __lt__ = interpindirect2app(W_AbstractUnicodeObject.descr_lt),
    __le__ = interpindirect2app(W_AbstractUnicodeObject.descr_le),
    __gt__ = interpindirect2app(W_AbstractUnicodeObject.descr_gt),
    __ge__ = interpindirect2app(W_AbstractUnicodeObject.descr_ge),

    __len__ = interpindirect2app(W_AbstractUnicodeObject.descr_len),
    __contains__ = interpindirect2app(W_AbstractUnicodeObject.descr_contains),

    __add__ = interpindirect2app(W_AbstractUnicodeObject.descr_add),
    __mul__ = interpindirect2app(W_AbstractUnicodeObject.descr_mul),
    __rmul__ = interpindirect2app(W_AbstractUnicodeObject.descr_rmul),

    __getitem__ = interpindirect2app(W_AbstractUnicodeObject.descr_getitem),
    __getslice__ = interpindirect2app(W_AbstractUnicodeObject.descr_getslice),

    capitalize = interpindirect2app(W_AbstractUnicodeObject.descr_capitalize),
    center = interpindirect2app(W_AbstractUnicodeObject.descr_center),
    count = interpindirect2app(W_AbstractUnicodeObject.descr_count),
    decode = interpindirect2app(W_AbstractUnicodeObject.descr_decode),
    encode = interpindirect2app(W_AbstractUnicodeObject.descr_encode),
    expandtabs = interpindirect2app(W_AbstractUnicodeObject.descr_expandtabs),
    find = interpindirect2app(W_AbstractUnicodeObject.descr_find),
    rfind = interpindirect2app(W_AbstractUnicodeObject.descr_rfind),
    index = interpindirect2app(W_AbstractUnicodeObject.descr_index),
    rindex = interpindirect2app(W_AbstractUnicodeObject.descr_rindex),
    isalnum = interpindirect2app(W_AbstractUnicodeObject.descr_isalnum),
    isalpha = interpindirect2app(W_AbstractUnicodeObject.descr_isalpha),
    isdecimal = interpindirect2app(W_AbstractUnicodeObject.descr_isdecimal),
    isdigit = interpindirect2app(W_AbstractUnicodeObject.descr_isdigit),
    islower = interpindirect2app(W_AbstractUnicodeObject.descr_islower),
    isnumeric = interpindirect2app(W_AbstractUnicodeObject.descr_isnumeric),
    isspace = interpindirect2app(W_AbstractUnicodeObject.descr_isspace),
    istitle = interpindirect2app(W_AbstractUnicodeObject.descr_istitle),
    isupper = interpindirect2app(W_AbstractUnicodeObject.descr_isupper),
    join = interpindirect2app(W_AbstractUnicodeObject.descr_join),
    ljust = interpindirect2app(W_AbstractUnicodeObject.descr_ljust),
    rjust = interpindirect2app(W_AbstractUnicodeObject.descr_rjust),
    lower = interpindirect2app(W_AbstractUnicodeObject.descr_lower),
    partition = interpindirect2app(W_AbstractUnicodeObject.descr_partition),
    rpartition = interpindirect2app(W_AbstractUnicodeObject.descr_rpartition),
    replace = interpindirect2app(W_AbstractUnicodeObject.descr_replace),
    split = interpindirect2app(W_AbstractUnicodeObject.descr_split),
    rsplit = interpindirect2app(W_AbstractUnicodeObject.descr_rsplit),
    splitlines = interpindirect2app(W_AbstractUnicodeObject.descr_splitlines),
    startswith = interpindirect2app(W_AbstractUnicodeObject.descr_startswith),
    endswith = interpindirect2app(W_AbstractUnicodeObject.descr_endswith),
    strip = interpindirect2app(W_AbstractUnicodeObject.descr_strip),
    lstrip = interpindirect2app(W_AbstractUnicodeObject.descr_lstrip),
    rstrip = interpindirect2app(W_AbstractUnicodeObject.descr_rstrip),
    swapcase = interpindirect2app(W_AbstractUnicodeObject.descr_swapcase),
    title = interpindirect2app(W_AbstractUnicodeObject.descr_title),
    translate = interpindirect2app(W_AbstractUnicodeObject.descr_translate),
    upper = interpindirect2app(W_AbstractUnicodeObject.descr_upper),
    zfill = interpindirect2app(W_AbstractUnicodeObject.descr_zfill),

    format = interpindirect2app(W_AbstractUnicodeObject.descr_format),
    __format__ = interpindirect2app(W_AbstractUnicodeObject.descr__format__),
    __mod__ = interpindirect2app(W_AbstractUnicodeObject.descr_mod),
    __getnewargs__ = interpindirect2app(W_AbstractUnicodeObject.descr_getnewargs),
    _formatter_parser =
        interp2app(W_AbstractUnicodeObject.descr_formatter_parser),
    _formatter_field_name_split =
        interp2app(W_AbstractUnicodeObject.descr_formatter_field_name_split),
)
W_UnicodeObject.typedef.flag_sequence_bug_compat = True


def _create_list_from_unicode(value):
    # need this helper function to allow the jit to look inside and inline
    # listview_unicode
    return [s for s in value]


W_UnicodeObject.EMPTY = W_UnicodeObject(u'')


# Helper for converting int/long
def unicode_to_decimal_w(space, w_unistr):
    if not space.isinstance_w(w_unistr, space.w_unicode):
        raise oefmt(space.w_TypeError, "expected unicode, got '%T'", w_unistr)
    unistr = w_unistr.unicode_w(space)
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
                w_encoding = space.wrap('decimal')
                w_start = space.wrap(i)
                w_end = space.wrap(i+1)
                w_reason = space.wrap('invalid decimal Unicode string')
                raise OperationError(space.w_UnicodeEncodeError,
                                     space.newtuple([w_encoding, w_unistr,
                                                     w_start, w_end,
                                                     w_reason]))
    return ''.join(result)


_repr_function, _ = make_unicode_escape_function(
    pass_printable=False, unicode_output=False, quotes=True, prefix='u')
