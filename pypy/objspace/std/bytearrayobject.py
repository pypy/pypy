"""The builtin bytearray implementation"""

from rpython.rlib.objectmodel import (
    import_from_mixin, newlist_hint, resizelist_hint, specialize)
from rpython.rlib.buffer import Buffer
from rpython.rlib.rstring import StringBuilder, ByteListBuilder
from rpython.rlib.debug import check_list_of_chars
from rpython.rtyper.lltypesystem import rffi
from rpython.rlib.rgc import (resizable_list_supporting_raw_ptr,
        nonmoving_raw_ptr_for_resizable_list)

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt
from pypy.objspace.std.bytesobject import (
    getbytevalue, makebytesdata_w, newbytesdata_w)
from pypy.interpreter.gateway import WrappedDefault, interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef
from pypy.objspace.std.sliceobject import W_SliceObject
from pypy.objspace.std.stringmethods import StringMethods, _get_buffer
from pypy.objspace.std.bytesobject import W_BytesObject
from pypy.objspace.std.util import get_positive_index

NON_HEX_MSG = "non-hexadecimal number found in fromhex() arg at position %d"


class W_BytearrayObject(W_Root):
    import_from_mixin(StringMethods)

    def __init__(self, data):
        check_list_of_chars(data)
        self.data = resizable_list_supporting_raw_ptr(data)

    def __repr__(self):
        """representation for debugging purposes"""
        return "%s(%s)" % (self.__class__.__name__, ''.join(self.data))

    def buffer_w(self, space, flags):
        return BytearrayBuffer(self.data, False)

    def bytearray_list_of_chars_w(self, space):
        return self.data

    def nonmovable_carray(self, space):
        return BytearrayBuffer(self.data, False).get_raw_address()

    def _new(self, value):
        if value is self.data:
            value = value[:]
        return W_BytearrayObject(value)

    def _new_from_buffer(self, buffer):
        return W_BytearrayObject([buffer[i] for i in range(len(buffer))])

    def _new_from_list(self, value):
        return W_BytearrayObject(value)

    def _empty(self):
        return W_BytearrayObject([])

    def _len(self):
        return len(self.data)

    def _getitem_result(self, space, index):
        try:
            character = self.data[index]
        except IndexError:
            raise oefmt(space.w_IndexError, "bytearray index out of range")
        return space.wrap(ord(character))

    def _val(self, space):
        return self.data

    @staticmethod
    def _use_rstr_ops(space, w_other):
        return False

    @staticmethod
    def _op_val(space, w_other, allow_char=False):
        # Some functions (contains, find) allow a number to specify a
        # single char.
        if allow_char and space.isinstance_w(w_other, space.w_int):
            return StringMethods._single_char(space, w_other)
        try:
            return space.bytes_w(w_other)
        except OperationError as e:
            if not e.match(space, space.w_TypeError):
                raise
        return space.buffer_w(w_other, space.BUF_SIMPLE).as_str()

    def _chr(self, char):
        assert len(char) == 1
        return str(char)[0]

    def _multi_chr(self, char):
        return [char]

    @staticmethod
    def _builder(size=100):
        return ByteListBuilder(size)

    def _newlist_unwrapped(self, space, res):
        return space.newlist([W_BytearrayObject(i) for i in res])

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

    def _join_return_one(self, space, w_obj):
        return False

    def _join_check_item(self, space, w_obj):
        return not (space.isinstance_w(w_obj, space.w_bytes) or
                    space.isinstance_w(w_obj, space.w_bytearray))

    def ord(self, space):
        if len(self.data) != 1:
            raise oefmt(space.w_TypeError,
                        "ord() expected a character, but string of length %d "
                        "found", len(self.data))
        return space.wrap(ord(self.data[0]))

    @staticmethod
    def descr_new(space, w_bytearraytype, __args__):
        return new_bytearray(space, w_bytearraytype, [])

    def descr_reduce(self, space):
        assert isinstance(self, W_BytearrayObject)
        w_dict = self.getdict(space)
        if w_dict is None:
            w_dict = space.w_None
        return space.newtuple([
            space.type(self), space.newtuple([
                space.wrap(''.join(self.data).decode('latin-1')),
                space.wrap('latin-1')]),
            w_dict])

    @staticmethod
    def descr_fromhex(space, w_bytearraytype, w_hexstring):
        if not space.is_w(space.type(w_hexstring), space.w_unicode):
            raise oefmt(space.w_TypeError, "must be str, not %T", w_hexstring)
        hexstring = space.unicode_w(w_hexstring)
        data = _hexstring_to_array(space, hexstring)
        # in CPython bytearray.fromhex is a staticmethod, so
        # we ignore w_type and always return a bytearray
        return new_bytearray(space, space.w_bytearray, data)

    @unwrap_spec(encoding='str_or_None', errors='str_or_None')
    def descr_init(self, space, w_source=None, encoding=None, errors=None):
        assert isinstance(self, W_BytearrayObject)
        data = newbytesdata_w(space, w_source, encoding, errors)
        self.data = resizable_list_supporting_raw_ptr(data)

    def descr_repr(self, space):
        s = self.data

        # Good default if there are no replacements.
        buf = StringBuilder(len("bytearray(b'')") + len(s))

        buf.append("bytearray(b")
        quote = "'"
        for c in s:
            if c == '"':
                quote = "'"
                break
            elif c == "'":
                quote = '"'
        buf.append(quote)

        for i in range(len(s)):
            c = s[i]

            if c == '\\' or c == "'":
                buf.append('\\')
                buf.append(c)
            elif c == '\t':
                buf.append('\\t')
            elif c == '\r':
                buf.append('\\r')
            elif c == '\n':
                buf.append('\\n')
            elif not '\x20' <= c < '\x7f':
                n = ord(c)
                buf.append('\\x')
                buf.append("0123456789abcdef"[n >> 4])
                buf.append("0123456789abcdef"[n & 0xF])
            else:
                buf.append(c)

        buf.append(quote)
        buf.append(")")

        return space.wrap(buf.build())

    def descr_str(self, space):
        if space.sys.get_flag('bytes_warning'):
            space.warn(space.wrap("str() on a bytearray instance"),
                       space.w_BytesWarning)
        return self.descr_repr(space)

    def descr_eq(self, space, w_other):
        if isinstance(w_other, W_BytearrayObject):
            return space.newbool(self.data == w_other.data)

        try:
            buffer = _get_buffer(space, w_other)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise

        value = self._val(space)
        buffer_len = buffer.getlength()

        if len(value) != buffer_len:
            return space.newbool(False)

        min_length = min(len(value), buffer_len)
        return space.newbool(_memcmp(value, buffer, min_length) == 0)

    def descr_ne(self, space, w_other):
        if isinstance(w_other, W_BytearrayObject):
            return space.newbool(self.data != w_other.data)

        try:
            buffer = _get_buffer(space, w_other)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise

        value = self._val(space)
        buffer_len = buffer.getlength()

        if len(value) != buffer_len:
            return space.newbool(True)

        min_length = min(len(value), buffer_len)
        return space.newbool(_memcmp(value, buffer, min_length) != 0)

    def _comparison_helper(self, space, w_other):
        value = self._val(space)

        if isinstance(w_other, W_BytearrayObject):
            other = w_other.data
            other_len = len(other)
            cmp = _memcmp(value, other, min(len(value), len(other)))
        elif isinstance(w_other, W_BytesObject):
            other = self._op_val(space, w_other)
            other_len = len(other)
            cmp = _memcmp(value, other, min(len(value), len(other)))
        else:
            try:
                buffer = _get_buffer(space, w_other)
            except OperationError as e:
                if e.match(space, space.w_TypeError):
                    return False, 0, 0
                raise
            other_len = len(buffer)
            cmp = _memcmp(value, buffer, min(len(value), len(buffer)))

        return True, cmp, other_len

    def descr_lt(self, space, w_other):
        success, cmp, other_len = self._comparison_helper(space, w_other)
        if not success:
            return space.w_NotImplemented
        return space.newbool(cmp < 0 or (cmp == 0 and self._len() < other_len))

    def descr_le(self, space, w_other):
        success, cmp, other_len = self._comparison_helper(space, w_other)
        if not success:
            return space.w_NotImplemented
        return space.newbool(cmp < 0 or (cmp == 0 and self._len() <= other_len))

    def descr_gt(self, space, w_other):
        success, cmp, other_len = self._comparison_helper(space, w_other)
        if not success:
            return space.w_NotImplemented
        return space.newbool(cmp > 0 or (cmp == 0 and self._len() > other_len))

    def descr_ge(self, space, w_other):
        success, cmp, other_len = self._comparison_helper(space, w_other)
        if not success:
            return space.w_NotImplemented
        return space.newbool(cmp > 0 or (cmp == 0 and self._len() >= other_len))

    def descr_inplace_add(self, space, w_other):
        if isinstance(w_other, W_BytearrayObject):
            self.data += w_other.data
            return self

        if isinstance(w_other, W_BytesObject):
            self._inplace_add(self._op_val(space, w_other))
        else:
            self._inplace_add(_get_buffer(space, w_other))
        return self

    @specialize.argtype(1)
    def _inplace_add(self, other):
        for i in range(len(other)):
            self.data.append(other[i])

    def descr_inplace_mul(self, space, w_times):
        try:
            times = space.getindex_w(w_times, space.w_OverflowError)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise
        self.data *= times
        return self

    def descr_setitem(self, space, w_index, w_other):
        if isinstance(w_index, W_SliceObject):
            oldsize = len(self.data)
            start, stop, step, slicelength = w_index.indices4(space, oldsize)
            sequence2 = makebytesdata_w(space, w_other)
            _setitem_slice_helper(space, self.data, start, step,
                                  slicelength, sequence2, empty_elem='\x00')
        else:
            idx = space.getindex_w(w_index, space.w_IndexError,
                                   "bytearray index")
            try:
                self.data[idx] = getbytevalue(space, w_other)
            except IndexError:
                raise oefmt(space.w_IndexError, "bytearray index out of range")

    def descr_delitem(self, space, w_idx):
        if isinstance(w_idx, W_SliceObject):
            start, stop, step, slicelength = w_idx.indices4(space,
                                                            len(self.data))
            _delitem_slice_helper(space, self.data, start, step, slicelength)
        else:
            idx = space.getindex_w(w_idx, space.w_IndexError,
                                   "bytearray index")
            try:
                del self.data[idx]
            except IndexError:
                raise oefmt(space.w_IndexError,
                            "bytearray deletion index out of range")

    def descr_append(self, space, w_item):
        self.data.append(getbytevalue(space, w_item))

    def descr_extend(self, space, w_other):
        if isinstance(w_other, W_BytearrayObject):
            self.data += w_other.data
        else:
            self.data += makebytesdata_w(space, w_other)
        return self

    def descr_insert(self, space, w_idx, w_other):
        where = space.int_w(w_idx)
        length = len(self.data)
        index = get_positive_index(where, length)
        val = getbytevalue(space, w_other)
        self.data.insert(index, val)
        return space.w_None

    @unwrap_spec(w_idx=WrappedDefault(-1))
    def descr_pop(self, space, w_idx):
        index = space.int_w(w_idx)
        try:
            result = self.data.pop(index)
        except IndexError:
            if not self.data:
                raise oefmt(space.w_IndexError, "pop from empty bytearray")
            raise oefmt(space.w_IndexError, "pop index out of range")
        return space.wrap(ord(result))

    def descr_remove(self, space, w_char):
        char = space.int_w(space.index(w_char))
        try:
            self.data.remove(chr(char))
        except ValueError:
            raise oefmt(space.w_ValueError, "value not found in bytearray")

    def descr_add(self, space, w_other):
        if isinstance(w_other, W_BytearrayObject):
            return self._new(self.data + w_other.data)

        if isinstance(w_other, W_BytesObject):
            return self._add(self._op_val(space, w_other))

        try:
            buffer = _get_buffer(space, w_other)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise
        return self._add(buffer)

    @specialize.argtype(1)
    def _add(self, other):
        return self._new(self.data + [other[i] for i in range(len(other))])

    def descr_reverse(self, space):
        self.data.reverse()

    def descr_clear(self, space):
        self.data = []

    def descr_copy(self, space):
        return self._new(self.data[:])


# ____________________________________________________________
# helpers for slow paths, moved out because they contain loops

def _make_data(s):
    return [s[i] for i in range(len(s))]

# ____________________________________________________________


def new_bytearray(space, w_bytearraytype, data):
    w_obj = space.allocate_instance(W_BytearrayObject, w_bytearraytype)
    W_BytearrayObject.__init__(w_obj, data)
    return w_obj


def _hex_digit_to_int(d):
    val = ord(d)
    if 47 < val < 58:
        return val - 48
    if 64 < val < 71:
        return val - 55
    if 96 < val < 103:
        return val - 87
    return -1

NON_HEX_MSG = "non-hexadecimal number found in fromhex() arg at position %d"

def _hexstring_to_array(space, s):
    data = []
    length = len(s)
    i = 0
    while True:
        while i < length and s[i] == ' ':
            i += 1
        if i >= length:
            break
        if i + 1 == length:
            raise oefmt(space.w_ValueError, NON_HEX_MSG, i)

        top = _hex_digit_to_int(s[i])
        if top == -1:
            raise oefmt(space.w_ValueError, NON_HEX_MSG, i)
        bot = _hex_digit_to_int(s[i + 1])
        if bot == -1:
            raise oefmt(space.w_ValueError, NON_HEX_MSG, i + 1)
        data.append(chr(top * 16 + bot))
        i += 2
    return data

HEXDIGITS = "0123456789abcdef"
PY_SIZE_T_MAX = 2**(rffi.sizeof(rffi.SIZE_T)*8)-1

def _array_to_hexstring(space, buf):
    length = buf.getlength()
    hexstring = StringBuilder(length*2)

    if length > PY_SIZE_T_MAX/2:
        raise OperationError(space.w_MemoryError)

    for i in range(length):
        byte = ord(buf.getitem(i))
        c = (byte >> 4 & 0xf)
        hexstring.append(HEXDIGITS[c])
        c = (byte & 0xf)
        hexstring.append(HEXDIGITS[c])

    return space.wrap(hexstring.build())

class BytearrayDocstrings:
    """bytearray(iterable_of_ints) -> bytearray
    bytearray(string, encoding[, errors]) -> bytearray
    bytearray(bytes_or_bytearray) -> mutable copy of bytes_or_bytearray
    bytearray(memory_view) -> bytearray

    Construct an mutable bytearray object from:
      - an iterable yielding integers in range(256)
      - a text string encoded using the specified encoding
      - a bytes or a bytearray object
      - any object implementing the buffer API.

    bytearray(int) -> bytearray.

    Construct a zero-initialized bytearray of the given length.

    """

    def __add__():
        """x.__add__(y) <==> x+y"""

    def __alloc__():
        """B.__alloc__() -> int

        Return the number of bytes actually allocated.
        """

    def __contains__():
        """x.__contains__(y) <==> y in x"""

    def __delitem__():
        """x.__delitem__(y) <==> del x[y]"""

    def __eq__():
        """x.__eq__(y) <==> x==y"""

    def __ge__():
        """x.__ge__(y) <==> x>=y"""

    def __getattribute__():
        """x.__getattribute__('name') <==> x.name"""

    def __getitem__():
        """x.__getitem__(y) <==> x[y]"""

    def __gt__():
        """x.__gt__(y) <==> x>y"""

    def __iadd__():
        """x.__iadd__(y) <==> x+=y"""

    def __imul__():
        """x.__imul__(y) <==> x*=y"""

    def __init__():
        """x.__init__(...) initializes x; see help(type(x)) for signature"""

    def __iter__():
        """x.__iter__() <==> iter(x)"""

    def __le__():
        """x.__le__(y) <==> x<=y"""

    def __len__():
        """x.__len__() <==> len(x)"""

    def __lt__():
        """x.__lt__(y) <==> x<y"""

    def __mul__():
        """x.__mul__(n) <==> x*n"""

    def __ne__():
        """x.__ne__(y) <==> x!=y"""

    def __reduce__():
        """Return state information for pickling."""

    def __repr__():
        """x.__repr__() <==> repr(x)"""

    def __rmul__():
        """x.__rmul__(n) <==> n*x"""

    def __setitem__():
        """x.__setitem__(i, y) <==> x[i]=y"""

    def __sizeof__():
        """B.__sizeof__() -> int

        Returns the size of B in memory, in bytes
        """

    def __str__():
        """x.__str__() <==> str(x)"""

    def append():
        """B.append(int) -> None

        Append a single item to the end of B.
        """

    def capitalize():
        """B.capitalize() -> copy of B

        Return a copy of B with only its first character capitalized (ASCII)
        and the rest lower-cased.
        """

    def center():
        """B.center(width[, fillchar]) -> copy of B

        Return B centered in a string of length width.  Padding is
        done using the specified fill character (default is a space).
        """

    def clear():
        """B.clear() -> None

        Remove all items from B.
        """

    def copy():
        """B.copy() -> bytearray

        Return a copy of B.
        """

    def count():
        """B.count(sub[, start[, end]]) -> int

        Return the number of non-overlapping occurrences of subsection sub in
        bytes B[start:end].  Optional arguments start and end are interpreted
        as in slice notation.
        """

    def decode():
        """B.decode(encoding=None, errors='strict') -> unicode

        Decode B using the codec registered for encoding. encoding defaults to
        the default encoding. errors may be given to set a different error
        handling scheme.  Default is 'strict' meaning that encoding errors
        raise a UnicodeDecodeError.  Other possible values are 'ignore' and
        'replace' as well as any other name registered with
        codecs.register_error that is able to handle UnicodeDecodeErrors.
        """

    def endswith():
        """B.endswith(suffix[, start[, end]]) -> bool

        Return True if B ends with the specified suffix, False otherwise.
        With optional start, test B beginning at that position.
        With optional end, stop comparing B at that position.
        suffix can also be a tuple of strings to try.
        """

    def expandtabs():
        """B.expandtabs([tabsize]) -> copy of B

        Return a copy of B where all tab characters are expanded using spaces.
        If tabsize is not given, a tab size of 8 characters is assumed.
        """

    def extend():
        """B.extend(iterable_of_ints) -> None

        Append all the elements from the iterator or sequence to the
        end of B.
        """

    def find():
        """B.find(sub[, start[, end]]) -> int

        Return the lowest index in B where subsection sub is found,
        such that sub is contained within B[start,end].  Optional
        arguments start and end are interpreted as in slice notation.

        Return -1 on failure.
        """

    def fromhex():
        r"""bytearray.fromhex(string) -> bytearray (static method)

        Create a bytearray object from a string of hexadecimal numbers.
        Spaces between two numbers are accepted.
        Example: bytearray.fromhex('B9 01EF') -> bytearray(b'\xb9\x01\xef').
        """

    def index():
        """B.index(sub[, start[, end]]) -> int

        Like B.find() but raise ValueError when the subsection is not found.
        """

    def insert():
        """B.insert(index, int) -> None

        Insert a single item into the bytearray before the given index.
        """

    def isalnum():
        """B.isalnum() -> bool

        Return True if all characters in B are alphanumeric
        and there is at least one character in B, False otherwise.
        """

    def isalpha():
        """B.isalpha() -> bool

        Return True if all characters in B are alphabetic
        and there is at least one character in B, False otherwise.
        """

    def isdigit():
        """B.isdigit() -> bool

        Return True if all characters in B are digits
        and there is at least one character in B, False otherwise.
        """

    def islower():
        """B.islower() -> bool

        Return True if all cased characters in B are lowercase and there is
        at least one cased character in B, False otherwise.
        """

    def isspace():
        """B.isspace() -> bool

        Return True if all characters in B are whitespace
        and there is at least one character in B, False otherwise.
        """

    def istitle():
        """B.istitle() -> bool

        Return True if B is a titlecased string and there is at least one
        character in B, i.e. uppercase characters may only follow uncased
        characters and lowercase characters only cased ones. Return False
        otherwise.
        """

    def isupper():
        """B.isupper() -> bool

        Return True if all cased characters in B are uppercase and there is
        at least one cased character in B, False otherwise.
        """

    def join():
        """B.join(iterable_of_bytes) -> bytearray

        Concatenate any number of str/bytearray objects, with B
        in between each pair, and return the result as a new bytearray.
        """

    def ljust():
        """B.ljust(width[, fillchar]) -> copy of B

        Return B left justified in a string of length width. Padding is
        done using the specified fill character (default is a space).
        """

    def lower():
        """B.lower() -> copy of B

        Return a copy of B with all ASCII characters converted to lowercase.
        """

    def lstrip():
        """B.lstrip([bytes]) -> bytearray

        Strip leading bytes contained in the argument
        and return the result as a new bytearray.
        If the argument is omitted, strip leading ASCII whitespace.
        """

    def partition():
        """B.partition(sep) -> (head, sep, tail)

        Search for the separator sep in B, and return the part before it,
        the separator itself, and the part after it.  If the separator is not
        found, returns B and two empty bytearray objects.
        """

    def pop():
        """B.pop([index]) -> int

        Remove and return a single item from B. If no index
        argument is given, will pop the last value.
        """

    def remove():
        """B.remove(int) -> None

        Remove the first occurrence of a value in B.
        """

    def replace():
        """B.replace(old, new[, count]) -> bytearray

        Return a copy of B with all occurrences of subsection
        old replaced by new.  If the optional argument count is
        given, only the first count occurrences are replaced.
        """

    def reverse():
        """B.reverse() -> None

        Reverse the order of the values in B in place.
        """

    def rfind():
        """B.rfind(sub[, start[, end]]) -> int

        Return the highest index in B where subsection sub is found,
        such that sub is contained within B[start,end].  Optional
        arguments start and end are interpreted as in slice notation.

        Return -1 on failure.
        """

    def rindex():
        """B.rindex(sub[, start[, end]]) -> int

        Like B.rfind() but raise ValueError when the subsection is not found.
        """

    def rjust():
        """B.rjust(width[, fillchar]) -> copy of B

        Return B right justified in a string of length width. Padding is
        done using the specified fill character (default is a space)
        """

    def rpartition():
        """B.rpartition(sep) -> (head, sep, tail)

        Search for the separator sep in B, starting at the end of B,
        and return the part before it, the separator itself, and the
        part after it.  If the separator is not found, returns two empty
        bytearray objects and B.
        """

    def rsplit():
        """B.rsplit(sep=None, maxsplit=-1) -> list of bytearrays

        Return a list of the sections in B, using sep as the delimiter,
        starting at the end of B and working to the front.
        If sep is not given, B is split on ASCII whitespace characters
        (space, tab, return, newline, formfeed, vertical tab).
        If maxsplit is given, at most maxsplit splits are done.
        """

    def rstrip():
        """B.rstrip([bytes]) -> bytearray

        Strip trailing bytes contained in the argument
        and return the result as a new bytearray.
        If the argument is omitted, strip trailing ASCII whitespace.
        """

    def split():
        """B.split(sep=None, maxsplit=-1) -> list of bytearrays

        Return a list of the sections in B, using sep as the delimiter.
        If sep is not given, B is split on ASCII whitespace characters
        (space, tab, return, newline, formfeed, vertical tab).
        If maxsplit is given, at most maxsplit splits are done.
        """

    def splitlines():
        """B.splitlines(keepends=False) -> list of lines

        Return a list of the lines in B, breaking at line boundaries.
        Line breaks are not included in the resulting list unless keepends
        is given and true.
        """

    def startswith():
        """B.startswith(prefix[, start[, end]]) -> bool

        Return True if B starts with the specified prefix, False otherwise.
        With optional start, test B beginning at that position.
        With optional end, stop comparing B at that position.
        prefix can also be a tuple of strings to try.
        """

    def strip():
        """B.strip([bytes]) -> bytearray

        Strip leading and trailing bytes contained in the argument
        and return the result as a new bytearray.
        If the argument is omitted, strip ASCII whitespace.
        """

    def swapcase():
        """B.swapcase() -> copy of B

        Return a copy of B with uppercase ASCII characters converted
        to lowercase ASCII and vice versa.
        """

    def title():
        """B.title() -> copy of B

        Return a titlecased version of B, i.e. ASCII words start with uppercase
        characters, all remaining cased characters have lowercase.
        """

    def translate():
        """B.translate(table[, deletechars]) -> bytearray

        Return a copy of B, where all characters occurring in the
        optional argument deletechars are removed, and the remaining
        characters have been mapped through the given translation
        table, which must be a bytes object of length 256.
        """

    def upper():
        """B.upper() -> copy of B

        Return a copy of B with all ASCII characters converted to uppercase.
        """

    def zfill():
        """B.zfill(width) -> copy of B

        Pad a numeric string B with zeros on the left, to fill a field
        of the specified width.  B is never truncated.
        """


W_BytearrayObject.typedef = TypeDef(
    "bytearray",
    __doc__ = BytearrayDocstrings.__doc__,
    __new__ = interp2app(W_BytearrayObject.descr_new),
    __hash__ = None,
    __reduce__ = interp2app(W_BytearrayObject.descr_reduce,
                            doc=BytearrayDocstrings.__reduce__.__doc__),
    fromhex = interp2app(W_BytearrayObject.descr_fromhex, as_classmethod=True,
                         doc=BytearrayDocstrings.fromhex.__doc__),
    maketrans = interp2app(W_BytearrayObject.descr_maketrans,
                           as_classmethod=True),

    __repr__ = interp2app(W_BytearrayObject.descr_repr,
                          doc=BytearrayDocstrings.__repr__.__doc__),
    __str__ = interp2app(W_BytearrayObject.descr_str,
                         doc=BytearrayDocstrings.__str__.__doc__),

    __eq__ = interp2app(W_BytearrayObject.descr_eq,
                        doc=BytearrayDocstrings.__eq__.__doc__),
    __ne__ = interp2app(W_BytearrayObject.descr_ne,
                        doc=BytearrayDocstrings.__ne__.__doc__),
    __lt__ = interp2app(W_BytearrayObject.descr_lt,
                        doc=BytearrayDocstrings.__lt__.__doc__),
    __le__ = interp2app(W_BytearrayObject.descr_le,
                        doc=BytearrayDocstrings.__le__.__doc__),
    __gt__ = interp2app(W_BytearrayObject.descr_gt,
                        doc=BytearrayDocstrings.__gt__.__doc__),
    __ge__ = interp2app(W_BytearrayObject.descr_ge,
                        doc=BytearrayDocstrings.__ge__.__doc__),

    __iter__ = interp2app(W_BytearrayObject.descr_iter,
                         doc=BytearrayDocstrings.__iter__.__doc__),
    __len__ = interp2app(W_BytearrayObject.descr_len,
                         doc=BytearrayDocstrings.__len__.__doc__),
    __contains__ = interp2app(W_BytearrayObject.descr_contains,
                              doc=BytearrayDocstrings.__contains__.__doc__),

    __add__ = interp2app(W_BytearrayObject.descr_add,
                         doc=BytearrayDocstrings.__add__.__doc__),
    __mul__ = interp2app(W_BytearrayObject.descr_mul,
                         doc=BytearrayDocstrings.__mul__.__doc__),
    __rmul__ = interp2app(W_BytearrayObject.descr_mul,
                          doc=BytearrayDocstrings.__rmul__.__doc__),

    __getitem__ = interp2app(W_BytearrayObject.descr_getitem,
                             doc=BytearrayDocstrings.__getitem__.__doc__),

    capitalize = interp2app(W_BytearrayObject.descr_capitalize,
                            doc=BytearrayDocstrings.capitalize.__doc__),
    center = interp2app(W_BytearrayObject.descr_center,
                        doc=BytearrayDocstrings.center.__doc__),
    count = interp2app(W_BytearrayObject.descr_count,
                       doc=BytearrayDocstrings.count.__doc__),
    decode = interp2app(W_BytearrayObject.descr_decode,
                        doc=BytearrayDocstrings.decode.__doc__),
    expandtabs = interp2app(W_BytearrayObject.descr_expandtabs,
                            doc=BytearrayDocstrings.expandtabs.__doc__),
    find = interp2app(W_BytearrayObject.descr_find,
                      doc=BytearrayDocstrings.find.__doc__),
    rfind = interp2app(W_BytearrayObject.descr_rfind,
                       doc=BytearrayDocstrings.rfind.__doc__),
    index = interp2app(W_BytearrayObject.descr_index,
                       doc=BytearrayDocstrings.index.__doc__),
    rindex = interp2app(W_BytearrayObject.descr_rindex,
                        doc=BytearrayDocstrings.rindex.__doc__),
    isalnum = interp2app(W_BytearrayObject.descr_isalnum,
                         doc=BytearrayDocstrings.isalnum.__doc__),
    isalpha = interp2app(W_BytearrayObject.descr_isalpha,
                         doc=BytearrayDocstrings.isalpha.__doc__),
    isdigit = interp2app(W_BytearrayObject.descr_isdigit,
                         doc=BytearrayDocstrings.isdigit.__doc__),
    islower = interp2app(W_BytearrayObject.descr_islower,
                         doc=BytearrayDocstrings.islower.__doc__),
    isspace = interp2app(W_BytearrayObject.descr_isspace,
                         doc=BytearrayDocstrings.isspace.__doc__),
    istitle = interp2app(W_BytearrayObject.descr_istitle,
                         doc=BytearrayDocstrings.istitle.__doc__),
    isupper = interp2app(W_BytearrayObject.descr_isupper,
                         doc=BytearrayDocstrings.isupper.__doc__),
    join = interp2app(W_BytearrayObject.descr_join,
                      doc=BytearrayDocstrings.join.__doc__),
    ljust = interp2app(W_BytearrayObject.descr_ljust,
                       doc=BytearrayDocstrings.ljust.__doc__),
    rjust = interp2app(W_BytearrayObject.descr_rjust,
                       doc=BytearrayDocstrings.rjust.__doc__),
    lower = interp2app(W_BytearrayObject.descr_lower,
                       doc=BytearrayDocstrings.lower.__doc__),
    partition = interp2app(W_BytearrayObject.descr_partition,
                           doc=BytearrayDocstrings.partition.__doc__),
    rpartition = interp2app(W_BytearrayObject.descr_rpartition,
                            doc=BytearrayDocstrings.rpartition.__doc__),
    replace = interp2app(W_BytearrayObject.descr_replace,
                         doc=BytearrayDocstrings.replace.__doc__),
    split = interp2app(W_BytearrayObject.descr_split,
                       doc=BytearrayDocstrings.split.__doc__),
    rsplit = interp2app(W_BytearrayObject.descr_rsplit,
                        doc=BytearrayDocstrings.rsplit.__doc__),
    splitlines = interp2app(W_BytearrayObject.descr_splitlines,
                            doc=BytearrayDocstrings.splitlines.__doc__),
    startswith = interp2app(W_BytearrayObject.descr_startswith,
                            doc=BytearrayDocstrings.startswith.__doc__),
    endswith = interp2app(W_BytearrayObject.descr_endswith,
                          doc=BytearrayDocstrings.endswith.__doc__),
    strip = interp2app(W_BytearrayObject.descr_strip,
                       doc=BytearrayDocstrings.strip.__doc__),
    lstrip = interp2app(W_BytearrayObject.descr_lstrip,
                        doc=BytearrayDocstrings.lstrip.__doc__),
    rstrip = interp2app(W_BytearrayObject.descr_rstrip,
                        doc=BytearrayDocstrings.rstrip.__doc__),
    swapcase = interp2app(W_BytearrayObject.descr_swapcase,
                          doc=BytearrayDocstrings.swapcase.__doc__),
    title = interp2app(W_BytearrayObject.descr_title,
                       doc=BytearrayDocstrings.title.__doc__),
    translate = interp2app(W_BytearrayObject.descr_translate,
                           doc=BytearrayDocstrings.translate.__doc__),
    upper = interp2app(W_BytearrayObject.descr_upper,
                       doc=BytearrayDocstrings.upper.__doc__),
    zfill = interp2app(W_BytearrayObject.descr_zfill,
                       doc=BytearrayDocstrings.zfill.__doc__),

    __init__ = interp2app(W_BytearrayObject.descr_init,
                          doc=BytearrayDocstrings.__init__.__doc__),

    __iadd__ = interp2app(W_BytearrayObject.descr_inplace_add,
                          doc=BytearrayDocstrings.__iadd__.__doc__),
    __imul__ = interp2app(W_BytearrayObject.descr_inplace_mul,
                          doc=BytearrayDocstrings.__imul__.__doc__),
    __setitem__ = interp2app(W_BytearrayObject.descr_setitem,
                             doc=BytearrayDocstrings.__setitem__.__doc__),
    __delitem__ = interp2app(W_BytearrayObject.descr_delitem,
                             doc=BytearrayDocstrings.__delitem__.__doc__),

    append = interp2app(W_BytearrayObject.descr_append,
                        doc=BytearrayDocstrings.append.__doc__),
    extend = interp2app(W_BytearrayObject.descr_extend,
                        doc=BytearrayDocstrings.extend.__doc__),
    insert = interp2app(W_BytearrayObject.descr_insert,
                        doc=BytearrayDocstrings.insert.__doc__),
    pop = interp2app(W_BytearrayObject.descr_pop,
                     doc=BytearrayDocstrings.pop.__doc__),
    remove = interp2app(W_BytearrayObject.descr_remove,
                        doc=BytearrayDocstrings.remove.__doc__),
    reverse = interp2app(W_BytearrayObject.descr_reverse,
                         doc=BytearrayDocstrings.reverse.__doc__),
    clear = interp2app(W_BytearrayObject.descr_clear,
                       doc=BytearrayDocstrings.clear.__doc__),
    copy = interp2app(W_BytearrayObject.descr_copy,
                         doc=BytearrayDocstrings.copy.__doc__),
)
W_BytearrayObject.typedef.flag_sequence_bug_compat = True


# XXX share the code again with the stuff in listobject.py
def _delitem_slice_helper(space, items, start, step, slicelength):
    if slicelength == 0:
        return

    if step < 0:
        start = start + step * (slicelength-1)
        step = -step

    if step == 1:
        assert start >= 0
        if slicelength > 0:
            del items[start:start+slicelength]
    else:
        n = len(items)
        i = start

        for discard in range(1, slicelength):
            j = i+1
            i += step
            while j < i:
                items[j-discard] = items[j]
                j += 1

        j = i+1
        while j < n:
            items[j-slicelength] = items[j]
            j += 1
        start = n - slicelength
        assert start >= 0 # annotator hint
        del items[start:]


def _setitem_slice_helper(space, items, start, step, slicelength, sequence2,
                          empty_elem):
    assert slicelength >= 0
    oldsize = len(items)
    len2 = len(sequence2)
    if step == 1:  # Support list resizing for non-extended slices
        delta = slicelength - len2
        if delta < 0:
            delta = -delta
            newsize = oldsize + delta
            # XXX support this in rlist!
            items += [empty_elem] * delta
            lim = start+len2
            i = newsize - 1
            while i >= lim:
                items[i] = items[i-delta]
                i -= 1
        elif delta == 0:
            pass
        else:
            assert start >= 0   # start<0 is only possible with slicelength==0
            del items[start:start+delta]
    elif len2 != slicelength:  # No resize for extended slices
        raise oefmt(space.w_ValueError,
                    "attempt to assign sequence of size %d to extended slice "
                    "of size %d", len2, slicelength)

    if sequence2 is items:
        if step > 0:
            # Always copy starting from the right to avoid
            # having to make a shallow copy in the case where
            # the source and destination lists are the same list.
            i = len2 - 1
            start += i*step
            while i >= 0:
                items[start] = sequence2[i]
                start -= step
                i -= 1
            return
        else:
            # Make a shallow copy to more easily handle the reversal case
            sequence2 = list(sequence2)
    for i in range(len2):
        items[start] = sequence2[i]
        start += step


class BytearrayBuffer(Buffer):
    _immutable_ = True

    def __init__(self, data, readonly):
        self.data = data
        self.readonly = readonly

    def getlength(self):
        return len(self.data)

    def getitem(self, index):
        return self.data[index]

    def setitem(self, index, char):
        self.data[index] = char

    def getslice(self, start, stop, step, size):
        if size == 0:
            return ""
        if step == 1:
            assert 0 <= start <= stop
            if start == 0 and stop == len(self.data):
                return "".join(self.data)
            return "".join(self.data[start:stop])
        return Buffer.getslice(self, start, stop, step, size)

    def setslice(self, start, string):
        # No bounds checks.
        for i in range(len(string)):
            self.data[start + i] = string[i]

    def get_raw_address(self):
        return nonmoving_raw_ptr_for_resizable_list(self.data)


@specialize.argtype(1)
def _memcmp(selfvalue, buffer, length):
    for i in range(length):
        if selfvalue[i] < buffer[i]:
            return -1
        if selfvalue[i] > buffer[i]:
            return 1
    return 0
