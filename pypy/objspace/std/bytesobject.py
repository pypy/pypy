"""The builtin str implementation"""

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.buffer import StringBuffer
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault
from pypy.objspace.std import newformat
from pypy.objspace.std.basestringtype import basestring_typedef
from pypy.objspace.std.formatting import mod_format
from pypy.objspace.std.stdtypedef import StdTypeDef
from pypy.objspace.std.stringmethods import StringMethods
from pypy.objspace.std.unicodeobject import (unicode_from_string,
    decode_object, unicode_from_encoded_object, _get_encoding_and_errors)
from rpython.rlib.jit import we_are_jitted
from rpython.rlib.objectmodel import compute_hash, compute_unique_id
from rpython.rlib.rstring import StringBuilder, replace


class W_AbstractBytesObject(W_Root):
    __slots__ = ()

    def is_w(self, space, w_other):
        if not isinstance(w_other, W_AbstractBytesObject):
            return False
        if self is w_other:
            return True
        if self.user_overridden_class or w_other.user_overridden_class:
            return False
        return space.str_w(self) is space.str_w(w_other)

    def immutable_unique_id(self, space):
        if self.user_overridden_class:
            return None
        return space.wrap(compute_unique_id(space.str_w(self)))

    def unicode_w(self, space):
        # Use the default encoding.
        w_defaultencoding = space.call_function(space.sys.get(
                                                'getdefaultencoding'))
        encoding, errors = _get_encoding_and_errors(space, w_defaultencoding,
                                                    space.w_None)
        if encoding is None and errors is None:
            return space.unicode_w(unicode_from_string(space, self))
        return space.unicode_w(decode_object(space, self, encoding, errors))


class W_BytesObject(W_AbstractBytesObject, StringMethods):
    _immutable_fields_ = ['_value']

    def __init__(self, str):
        self._value = str

    def __repr__(self):
        """ representation for debugging purposes """
        return "%s(%r)" % (self.__class__.__name__, self._value)

    def unwrap(self, space):
        return self._value

    def str_w(self, space):
        return self._value

    def listview_str(self):
        return _create_list_from_string(self._value)

    def ord(self, space):
        if len(self._value) != 1:
            msg = "ord() expected a character, but string of length %d found"
            raise operationerrfmt(space.w_TypeError, msg, len(self._value))
        return space.wrap(ord(self._value[0]))

    def _new(self, value):
        return W_BytesObject(value)

    def _new_from_list(self, value):
        return W_BytesObject(''.join(value))

    def _empty(self):
        return W_BytesObject.EMPTY

    def _len(self):
        return len(self._value)

    def _val(self, space):
        return self._value

    def _op_val(self, space, w_other):
        return space.bufferstr_w(w_other)
        #return w_other._value

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
        return space.newlist_str(lst)

    @staticmethod
    @unwrap_spec(w_object = WrappedDefault(""))
    def descr_new(space, w_stringtype, w_object):
        # NB. the default value of w_object is really a *wrapped* empty string:
        #     there is gateway magic at work
        w_obj = space.str(w_object)
        if space.is_w(w_stringtype, space.w_str):
            return w_obj  # XXX might be reworked when space.str() typechecks
        value = space.str_w(w_obj)
        w_obj = space.allocate_instance(W_BytesObject, w_stringtype)
        W_BytesObject.__init__(w_obj, value)
        return w_obj

    def descr_repr(self, space):
        s = self._value
        quote = "'"
        if quote in s and '"' not in s:
            quote = '"'
        return space.wrap(string_escape_encode(s, quote))

    def descr_str(self, space):
        if type(self) is W_BytesObject:
            return self
        return wrapstr(space, self._value)

    def descr_hash(self, space):
        x = compute_hash(self._value)
        return space.wrap(x)

    def descr_format(self, space, __args__):
        return newformat.format_method(space, self, __args__, is_unicode=False)

    def descr__format__(self, space, w_format_spec):
        if not space.isinstance_w(w_format_spec, space.w_str):
            w_format_spec = space.str(w_format_spec)
        spec = space.str_w(w_format_spec)
        formatter = newformat.str_formatter(space, spec)
        return formatter.format_string(self._value)

    def descr_mod(self, space, w_values):
        return mod_format(space, self, w_values, do_unicode=False)

    def descr_buffer(self, space):
        return space.wrap(StringBuffer(self._value))

    # auto-conversion fun

    def descr_add(self, space, w_other):
        if space.isinstance_w(w_other, space.w_unicode):
            self_as_unicode = unicode_from_encoded_object(space, self, None, None)
            return space.add(self_as_unicode, w_other)
        elif space.isinstance_w(w_other, space.w_bytearray):
            # XXX: eliminate double-copy
            from .bytearrayobject import W_BytearrayObject, _make_data
            self_as_bytearray = W_BytearrayObject(_make_data(self._value))
            return space.add(self_as_bytearray, w_other)
        return StringMethods.descr_add(self, space, w_other)

    def _startswith(self, space, value, w_prefix, start, end):
        if space.isinstance_w(w_prefix, space.w_unicode):
            self_as_unicode = unicode_from_encoded_object(space, self, None, None)
            return self_as_unicode._startswith(space, self_as_unicode._value, w_prefix, start, end)
        return StringMethods._startswith(self, space, value, w_prefix, start, end)

    def _endswith(self, space, value, w_suffix, start, end):
        if space.isinstance_w(w_suffix, space.w_unicode):
            self_as_unicode = unicode_from_encoded_object(space, self, None, None)
            return self_as_unicode._endswith(space, self_as_unicode._value, w_suffix, start, end)
        return StringMethods._endswith(self, space, value, w_suffix, start, end)

    def descr_contains(self, space, w_sub):
        if space.isinstance_w(w_sub, space.w_unicode):
            from pypy.objspace.std.unicodeobject import W_UnicodeObject
            assert isinstance(w_sub, W_UnicodeObject)
            self_as_unicode = unicode_from_encoded_object(space, self, None, None)
            return space.newbool(self_as_unicode._value.find(w_sub._value) >= 0)
        return StringMethods.descr_contains(self, space, w_sub)

    @unwrap_spec(count=int)
    def descr_replace(self, space, w_old, w_new, count=-1):
        old_is_unicode = space.isinstance_w(w_old, space.w_unicode)
        new_is_unicode = space.isinstance_w(w_new, space.w_unicode)
        if old_is_unicode or new_is_unicode:
            self_as_uni = unicode_from_encoded_object(space, self, None, None)
            if not old_is_unicode:
                w_old = unicode_from_encoded_object(space, w_old, None, None)
            if not new_is_unicode:
                w_new = unicode_from_encoded_object(space, w_new, None, None)
            input = self_as_uni._val(space)
            sub = self_as_uni._op_val(space, w_old)
            by = self_as_uni._op_val(space, w_new)
            try:
                res = replace(input, sub, by, count)
            except OverflowError:
                raise OperationError(space.w_OverflowError,
                                     space.wrap("replace string is too long"))
            return self_as_uni._new(res)
        return StringMethods.descr_replace(self, space, w_old, w_new, count)

    def _join_return_one(self, space, w_obj):
        return (space.is_w(space.type(w_obj), space.w_str) or
                space.is_w(space.type(w_obj), space.w_unicode))

    def _join_check_item(self, space, w_obj):
        if space.isinstance_w(w_obj, space.w_str):
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

    def descr_formatter_parser(self, space):
        from pypy.objspace.std.newformat import str_template_formatter
        tformat = str_template_formatter(space, space.str_w(self))
        return tformat.formatter_parser()

    def descr_formatter_field_name_split(self, space):
        from pypy.objspace.std.newformat import str_template_formatter
        tformat = str_template_formatter(space, space.str_w(self))
        return tformat.formatter_field_name_split()


def _create_list_from_string(value):
    # need this helper function to allow the jit to look inside and inline
    # listview_str
    return [s for s in value]

W_BytesObject.EMPTY = W_BytesObject('')
W_BytesObject.PREBUILT = [W_BytesObject(chr(i)) for i in range(256)]
del i


def wrapstr(space, s):
    if space.config.objspace.std.sharesmallstr:
        if space.config.objspace.std.withprebuiltchar:
            # share characters and empty string
            if len(s) <= 1:
                if len(s) == 0:
                    return W_BytesObject.EMPTY
                else:
                    s = s[0]     # annotator hint: a single char
                    return wrapchar(space, s)
        else:
            # only share the empty string
            if len(s) == 0:
                return W_BytesObject.EMPTY
    return W_BytesObject(s)

def wrapchar(space, c):
    if space.config.objspace.std.withprebuiltchar and not we_are_jitted():
        return W_BytesObject.PREBUILT[ord(c)]
    else:
        return W_BytesObject(c)


class BytesDocstrings:
    """str(object='') -> string

    Return a nice string representation of the object.
    If the argument is a string, the return value is the same object.

    """

    def __add__():
        """x.__add__(y) <==> x+y"""

    def __contains__():
        """x.__contains__(y) <==> y in x"""

    def __eq__():
        """x.__eq__(y) <==> x==y"""

    def __format__():
        """S.__format__(format_spec) -> string

        Return a formatted version of S as described by format_spec.
        """

    def __ge__():
        """x.__ge__(y) <==> x>=y"""

    def __getattribute__():
        """x.__getattribute__('name') <==> x.name"""

    def __getitem__():
        """x.__getitem__(y) <==> x[y]"""

    def __getnewargs__():
        """"""

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
        """S.capitalize() -> string

        Return a capitalized version of S, i.e. make the first character
        have upper case and the rest lower case.
        """

    def center():
        """S.center(width[, fillchar]) -> string

        Return S centered in a string of length width. Padding is
        done using the specified fill character (default is a space).
        """

    def count():
        """S.count(sub[, start[, end]]) -> int

        Return the number of non-overlapping occurrences of substring sub in
        string S[start:end].  Optional arguments start and end are interpreted
        as in slice notation.
        """

    def decode():
        """S.decode(encoding=None, errors='strict') -> object

        Decode S using the codec registered for encoding. encoding defaults
        to the default encoding. errors may be given to set a different error
        handling scheme. Default is 'strict' meaning that encoding errors raise
        a UnicodeDecodeError. Other possible values are 'ignore' and 'replace'
        as well as any other name registered with codecs.register_error that is
        able to handle UnicodeDecodeErrors.
        """

    def encode():
        """S.encode(encoding=None, errors='strict') -> object

        Encode S using the codec registered for encoding. encoding defaults
        to the default encoding. errors may be given to set a different error
        handling scheme. Default is 'strict' meaning that encoding errors raise
        a UnicodeEncodeError. Other possible values are 'ignore', 'replace' and
        'xmlcharrefreplace' as well as any other name registered with
        codecs.register_error that is able to handle UnicodeEncodeErrors.
        """

    def endswith():
        """S.endswith(suffix[, start[, end]]) -> bool

        Return True if S ends with the specified suffix, False otherwise.
        With optional start, test S beginning at that position.
        With optional end, stop comparing S at that position.
        suffix can also be a tuple of strings to try.
        """

    def expandtabs():
        """S.expandtabs([tabsize]) -> string

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
        """S.format(*args, **kwargs) -> string

        Return a formatted version of S, using substitutions from args and kwargs.
        The substitutions are identified by braces ('{' and '}').
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

    def isspace():
        """S.isspace() -> bool

        Return True if all characters in S are whitespace
        and there is at least one character in S, False otherwise.
        """

    def istitle():
        """S.istitle() -> bool

        Return True if S is a titlecased string and there is at least one
        character in S, i.e. uppercase characters may only follow uncased
        characters and lowercase characters only cased ones. Return False
        otherwise.
        """

    def isupper():
        """S.isupper() -> bool

        Return True if all cased characters in S are uppercase and there is
        at least one cased character in S, False otherwise.
        """

    def join():
        """S.join(iterable) -> string

        Return a string which is the concatenation of the strings in the
        iterable.  The separator between elements is S.
        """

    def ljust():
        """S.ljust(width[, fillchar]) -> string

        Return S left-justified in a string of length width. Padding is
        done using the specified fill character (default is a space).
        """

    def lower():
        """S.lower() -> string

        Return a copy of the string S converted to lowercase.
        """

    def lstrip():
        """S.lstrip([chars]) -> string or unicode

        Return a copy of the string S with leading whitespace removed.
        If chars is given and not None, remove characters in chars instead.
        If chars is unicode, S will be converted to unicode before stripping
        """

    def partition():
        """S.partition(sep) -> (head, sep, tail)

        Search for the separator sep in S, and return the part before it,
        the separator itself, and the part after it.  If the separator is not
        found, return S and two empty strings.
        """

    def replace():
        """S.replace(old, new[, count]) -> string

        Return a copy of string S with all occurrences of substring
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
        """S.rjust(width[, fillchar]) -> string

        Return S right-justified in a string of length width. Padding is
        done using the specified fill character (default is a space).
        """

    def rpartition():
        """S.rpartition(sep) -> (head, sep, tail)

        Search for the separator sep in S, starting at the end of S, and return
        the part before it, the separator itself, and the part after it.  If the
        separator is not found, return two empty strings and S.
        """

    def rsplit():
        """S.rsplit(sep=None, maxsplit=-1) -> list of strings

        Return a list of the words in the string S, using sep as the
        delimiter string, starting at the end of the string and working
        to the front.  If maxsplit is given, at most maxsplit splits are
        done. If sep is not specified or is None, any whitespace string
        is a separator.
        """

    def rstrip():
        """S.rstrip([chars]) -> string or unicode

        Return a copy of the string S with trailing whitespace removed.
        If chars is given and not None, remove characters in chars instead.
        If chars is unicode, S will be converted to unicode before stripping
        """

    def split():
        """S.split(sep=None, maxsplit=-1) -> list of strings

        Return a list of the words in the string S, using sep as the
        delimiter string.  If maxsplit is given, at most maxsplit
        splits are done. If sep is not specified or is None, any
        whitespace string is a separator and empty strings are removed
        from the result.
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
        """S.strip([chars]) -> string or unicode

        Return a copy of the string S with leading and trailing
        whitespace removed.
        If chars is given and not None, remove characters in chars instead.
        If chars is unicode, S will be converted to unicode before stripping
        """

    def swapcase():
        """S.swapcase() -> string

        Return a copy of the string S with uppercase characters
        converted to lowercase and vice versa.
        """

    def title():
        """S.title() -> string

        Return a titlecased version of S, i.e. words start with uppercase
        characters, all remaining cased characters have lowercase.
        """

    def translate():
        """S.translate(table[, deletechars]) -> string

        Return a copy of the string S, where all characters occurring
        in the optional argument deletechars are removed, and the
        remaining characters have been mapped through the given
        translation table, which must be a string of length 256 or None.
        If the table argument is None, no translation is applied and
        the operation simply removes the characters in deletechars.
        """

    def upper():
        """S.upper() -> string

        Return a copy of the string S converted to uppercase.
        """

    def zfill():
        """S.zfill(width) -> string

        Pad a numeric string S with zeros on the left, to fill a field
        of the specified width. The string S is never truncated.
        """


W_BytesObject.typedef = StdTypeDef(
    "str", basestring_typedef,
    __new__ = interp2app(W_BytesObject.descr_new),
    __doc__ = BytesDocstrings.__doc__,

    __repr__ = interp2app(W_BytesObject.descr_repr,
                          doc=BytesDocstrings.__repr__.__doc__),
    __str__ = interp2app(W_BytesObject.descr_str,
                         doc=BytesDocstrings.__str__.__doc__),
    __hash__ = interp2app(W_BytesObject.descr_hash,
                          doc=BytesDocstrings.__hash__.__doc__),

    __eq__ = interp2app(W_BytesObject.descr_eq,
                        doc=BytesDocstrings.__eq__.__doc__),
    __ne__ = interp2app(W_BytesObject.descr_ne,
                        doc=BytesDocstrings.__ne__.__doc__),
    __lt__ = interp2app(W_BytesObject.descr_lt,
                        doc=BytesDocstrings.__lt__.__doc__),
    __le__ = interp2app(W_BytesObject.descr_le,
                        doc=BytesDocstrings.__le__.__doc__),
    __gt__ = interp2app(W_BytesObject.descr_gt,
                        doc=BytesDocstrings.__gt__.__doc__),
    __ge__ = interp2app(W_BytesObject.descr_ge,
                        doc=BytesDocstrings.__ge__.__doc__),

    __len__ = interp2app(W_BytesObject.descr_len,
                         doc=BytesDocstrings.__len__.__doc__),
    __contains__ = interp2app(W_BytesObject.descr_contains,
                              doc=BytesDocstrings.__contains__.__doc__),

    __add__ = interp2app(W_BytesObject.descr_add,
                         doc=BytesDocstrings.__add__.__doc__),
    __mul__ = interp2app(W_BytesObject.descr_mul,
                         doc=BytesDocstrings.__mul__.__doc__),
    __rmul__ = interp2app(W_BytesObject.descr_mul,
                          doc=BytesDocstrings.__rmul__.__doc__),

    __getitem__ = interp2app(W_BytesObject.descr_getitem,
                             doc=BytesDocstrings.__getitem__.__doc__),
    __getslice__ = interp2app(W_BytesObject.descr_getslice,
                              doc=BytesDocstrings.__getslice__.__doc__),

    capitalize = interp2app(W_BytesObject.descr_capitalize,
                            doc=BytesDocstrings.capitalize.__doc__),
    center = interp2app(W_BytesObject.descr_center,
                        doc=BytesDocstrings.center.__doc__),
    count = interp2app(W_BytesObject.descr_count,
                       doc=BytesDocstrings.count.__doc__),
    decode = interp2app(W_BytesObject.descr_decode,
                        doc=BytesDocstrings.decode.__doc__),
    encode = interp2app(W_BytesObject.descr_encode,
                        doc=BytesDocstrings.encode.__doc__),
    expandtabs = interp2app(W_BytesObject.descr_expandtabs,
                            doc=BytesDocstrings.expandtabs.__doc__),
    find = interp2app(W_BytesObject.descr_find,
                      doc=BytesDocstrings.find.__doc__),
    rfind = interp2app(W_BytesObject.descr_rfind,
                       doc=BytesDocstrings.rfind.__doc__),
    index = interp2app(W_BytesObject.descr_index,
                       doc=BytesDocstrings.index.__doc__),
    rindex = interp2app(W_BytesObject.descr_rindex,
                        doc=BytesDocstrings.rindex.__doc__),
    isalnum = interp2app(W_BytesObject.descr_isalnum,
                         doc=BytesDocstrings.isalnum.__doc__),
    isalpha = interp2app(W_BytesObject.descr_isalpha,
                         doc=BytesDocstrings.isalpha.__doc__),
    isdigit = interp2app(W_BytesObject.descr_isdigit,
                         doc=BytesDocstrings.isdigit.__doc__),
    islower = interp2app(W_BytesObject.descr_islower,
                         doc=BytesDocstrings.islower.__doc__),
    isspace = interp2app(W_BytesObject.descr_isspace,
                         doc=BytesDocstrings.isspace.__doc__),
    istitle = interp2app(W_BytesObject.descr_istitle,
                         doc=BytesDocstrings.istitle.__doc__),
    isupper = interp2app(W_BytesObject.descr_isupper,
                         doc=BytesDocstrings.isupper.__doc__),
    join = interp2app(W_BytesObject.descr_join,
                      doc=BytesDocstrings.join.__doc__),
    ljust = interp2app(W_BytesObject.descr_ljust,
                       doc=BytesDocstrings.ljust.__doc__),
    rjust = interp2app(W_BytesObject.descr_rjust,
                       doc=BytesDocstrings.rjust.__doc__),
    lower = interp2app(W_BytesObject.descr_lower,
                       doc=BytesDocstrings.lower.__doc__),
    partition = interp2app(W_BytesObject.descr_partition,
                           doc=BytesDocstrings.partition.__doc__),
    rpartition = interp2app(W_BytesObject.descr_rpartition,
                            doc=BytesDocstrings.rpartition.__doc__),
    replace = interp2app(W_BytesObject.descr_replace,
                         doc=BytesDocstrings.replace.__doc__),
    split = interp2app(W_BytesObject.descr_split,
                       doc=BytesDocstrings.split.__doc__),
    rsplit = interp2app(W_BytesObject.descr_rsplit,
                        doc=BytesDocstrings.rsplit.__doc__),
    splitlines = interp2app(W_BytesObject.descr_splitlines,
                            doc=BytesDocstrings.splitlines.__doc__),
    startswith = interp2app(W_BytesObject.descr_startswith,
                            doc=BytesDocstrings.startswith.__doc__),
    endswith = interp2app(W_BytesObject.descr_endswith,
                          doc=BytesDocstrings.endswith.__doc__),
    strip = interp2app(W_BytesObject.descr_strip,
                       doc=BytesDocstrings.strip.__doc__),
    lstrip = interp2app(W_BytesObject.descr_lstrip,
                        doc=BytesDocstrings.lstrip.__doc__),
    rstrip = interp2app(W_BytesObject.descr_rstrip,
                        doc=BytesDocstrings.rstrip.__doc__),
    swapcase = interp2app(W_BytesObject.descr_swapcase,
                          doc=BytesDocstrings.swapcase.__doc__),
    title = interp2app(W_BytesObject.descr_title,
                       doc=BytesDocstrings.title.__doc__),
    translate = interp2app(W_BytesObject.descr_translate,
                           doc=BytesDocstrings.translate.__doc__),
    upper = interp2app(W_BytesObject.descr_upper,
                       doc=BytesDocstrings.upper.__doc__),
    zfill = interp2app(W_BytesObject.descr_zfill,
                       doc=BytesDocstrings.zfill.__doc__),

    format = interp2app(W_BytesObject.descr_format,
                        doc=BytesDocstrings.format.__doc__),
    __format__ = interp2app(W_BytesObject.descr__format__,
                            doc=BytesDocstrings.__format__.__doc__),
    __mod__ = interp2app(W_BytesObject.descr_mod,
                         doc=BytesDocstrings.__mod__.__doc__),
    __buffer__ = interp2app(W_BytesObject.descr_buffer),
    __getnewargs__ = interp2app(W_BytesObject.descr_getnewargs,
                                doc=BytesDocstrings.__getnewargs__.__doc__),
    _formatter_parser = interp2app(W_BytesObject.descr_formatter_parser),
    _formatter_field_name_split =
        interp2app(W_BytesObject.descr_formatter_field_name_split),
)


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
            buf.append("0123456789abcdef"[n>>4])
            buf.append("0123456789abcdef"[n&0xF])

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
