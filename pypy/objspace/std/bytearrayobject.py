"""The builtin bytearray implementation"""

from rpython.rlib.objectmodel import (
    import_from_mixin, newlist_hint, resizelist_hint)
from rpython.rlib.rstring import StringBuilder

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.buffer import RWBuffer
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import WrappedDefault, interp2app, unwrap_spec
from pypy.interpreter.signature import Signature
from pypy.objspace.std.sliceobject import W_SliceObject
from pypy.objspace.std.stdtypedef import StdTypeDef
from pypy.objspace.std.stringmethods import StringMethods
from pypy.objspace.std.util import get_positive_index

NON_HEX_MSG = "non-hexadecimal number found in fromhex() arg at position %d"


class W_BytearrayObject(W_Root):
    import_from_mixin(StringMethods)

    def __init__(w_self, data):
        w_self.data = data

    def __repr__(w_self):
        """representation for debugging purposes"""
        return "%s(%s)" % (w_self.__class__.__name__, ''.join(w_self.data))

    def buffer_w(self, space, flags):
        return BytearrayBuffer(self.data)

    def readbuf_w(self, space):
        return BytearrayBuffer(self.data)

    def writebuf_w(self, space):
        return BytearrayBuffer(self.data)

    def charbuf_w(self, space):
        return ''.join(self.data)

    def _new(self, value):
        return W_BytearrayObject(_make_data(value))

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
        return space.buffer_w(self, space.BUF_SIMPLE).as_str()

    def _op_val(self, space, w_other):
        return space.buffer_w(w_other, space.BUF_SIMPLE).as_str()

    def _chr(self, char):
        assert len(char) == 1
        return str(char)[0]

    _builder = StringBuilder

    def _newlist_unwrapped(self, space, res):
        return space.newlist([W_BytearrayObject(_make_data(i)) for i in res])

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
        if (space.isinstance_w(w_obj, space.w_str) or
            space.isinstance_w(w_obj, space.w_bytearray)):
            return 0
        return 1

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
        hexstring = space.str_w(w_hexstring)
        hexstring = hexstring.lower()
        data = []
        length = len(hexstring)
        i = -2
        while True:
            i += 2
            while i < length and hexstring[i] == ' ':
                i += 1
            if i >= length:
                break
            if i + 1 == length:
                raise oefmt(space.w_ValueError, NON_HEX_MSG, i)

            top = _hex_digit_to_int(hexstring[i])
            if top == -1:
                raise oefmt(space.w_ValueError, NON_HEX_MSG, i)
            bot = _hex_digit_to_int(hexstring[i+1])
            if bot == -1:
                raise oefmt(space.w_ValueError, NON_HEX_MSG, i + 1)
            data.append(chr(top*16 + bot))

        # in CPython bytearray.fromhex is a staticmethod, so
        # we ignore w_type and always return a bytearray
        return new_bytearray(space, space.w_bytearray, data)

    def descr_init(self, space, __args__):
        # this is on the silly side
        w_source, w_encoding, w_errors = __args__.parse_obj(
                None, 'bytearray', init_signature, init_defaults)

        if w_source is None:
            w_source = space.wrap('')
        if w_encoding is None:
            w_encoding = space.w_None
        if w_errors is None:
            w_errors = space.w_None

        # Unicode argument
        if not space.is_w(w_encoding, space.w_None):
            from pypy.objspace.std.unicodeobject import (
                _get_encoding_and_errors, encode_object
            )
            encoding, errors = _get_encoding_and_errors(space, w_encoding,
                                                        w_errors)

            # if w_source is an integer this correctly raises a
            # TypeError the CPython error message is: "encoding or
            # errors without a string argument" ours is: "expected
            # unicode, got int object"
            w_source = encode_object(space, w_source, encoding, errors)

        # Is it an int?
        try:
            count = space.int_w(w_source)
        except OperationError as e:
            if not e.match(space, space.w_TypeError):
                raise
        else:
            if count < 0:
                raise oefmt(space.w_ValueError, "bytearray negative count")
            self.data = ['\0'] * count
            return

        data = makebytearraydata_w(space, w_source)
        self.data = data

    def descr_repr(self, space):
        s = self.data

        # Good default if there are no replacements.
        buf = StringBuilder(len("bytearray(b'')") + len(s))

        buf.append("bytearray(b'")

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

        buf.append("')")

        return space.wrap(buf.build())

    def descr_str(self, space):
        return space.wrap(''.join(self.data))

    def descr_eq(self, space, w_other):
        try:
            res = self._val(space) == self._op_val(space, w_other)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise
        return space.newbool(res)

    def descr_ne(self, space, w_other):
        try:
            res = self._val(space) != self._op_val(space, w_other)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
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

    def descr_iter(self, space):
        return space.newseqiter(self)

    def descr_inplace_add(self, space, w_other):
        if isinstance(w_other, W_BytearrayObject):
            self.data += w_other.data
        else:
            self.data += self._op_val(space, w_other)
        return self

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
            sequence2 = makebytearraydata_w(space, w_other)
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
            self.data += makebytearraydata_w(space, w_other)
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

    _StringMethods_descr_contains = descr_contains
    def descr_contains(self, space, w_sub):
        if space.isinstance_w(w_sub, space.w_int):
            char = space.int_w(w_sub)
            return _descr_contains_bytearray(self.data, space, char)
        return self._StringMethods_descr_contains(space, w_sub)

    def descr_reverse(self, space):
        self.data.reverse()


# ____________________________________________________________
# helpers for slow paths, moved out because they contain loops

def _make_data(s):
    return [s[i] for i in range(len(s))]


def _descr_contains_bytearray(data, space, char):
    if not 0 <= char < 256:
        raise oefmt(space.w_ValueError, "byte must be in range(0, 256)")
    for c in data:
        if ord(c) == char:
            return space.w_True
    return space.w_False

# ____________________________________________________________


def getbytevalue(space, w_value):
    if space.isinstance_w(w_value, space.w_str):
        string = space.str_w(w_value)
        if len(string) != 1:
            raise oefmt(space.w_ValueError, "string must be of size 1")
        return string[0]

    value = space.getindex_w(w_value, None)
    if not 0 <= value < 256:
        # this includes the OverflowError in case the long is too large
        raise oefmt(space.w_ValueError, "byte must be in range(0, 256)")
    return chr(value)


def new_bytearray(space, w_bytearraytype, data):
    w_obj = space.allocate_instance(W_BytearrayObject, w_bytearraytype)
    W_BytearrayObject.__init__(w_obj, data)
    return w_obj


def makebytearraydata_w(space, w_source):
    # String-like argument
    try:
        buf = space.buffer_w(w_source, space.BUF_FULL_RO)
    except OperationError as e:
        if not e.match(space, space.w_TypeError):
            raise
    else:
        return [c for c in buf.as_str()]

    # sequence of bytes
    w_iter = space.iter(w_source)
    length_hint = space.length_hint(w_source, 0)
    data = newlist_hint(length_hint)
    extended = 0
    while True:
        try:
            w_item = space.next(w_iter)
        except OperationError as e:
            if not e.match(space, space.w_StopIteration):
                raise
            break
        value = getbytevalue(space, w_item)
        data.append(value)
        extended += 1
    if extended < length_hint:
        resizelist_hint(data, extended)
    return data


def _hex_digit_to_int(d):
    val = ord(d)
    if 47 < val < 58:
        return val - 48
    if 96 < val < 103:
        return val - 87
    return -1


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


W_BytearrayObject.typedef = StdTypeDef(
    "bytearray",
    __doc__ = BytearrayDocstrings.__doc__,
    __new__ = interp2app(W_BytearrayObject.descr_new),
    __hash__ = None,
    __reduce__ = interp2app(W_BytearrayObject.descr_reduce,
                            doc=BytearrayDocstrings.__reduce__.__doc__),
    fromhex = interp2app(W_BytearrayObject.descr_fromhex, as_classmethod=True,
                         doc=BytearrayDocstrings.fromhex.__doc__),

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
)

init_signature = Signature(['source', 'encoding', 'errors'], None, None)
init_defaults = [None, None, None]


# XXX consider moving to W_BytearrayObject or remove
def str_join__Bytearray_ANY(space, w_self, w_list):
    list_w = space.listview(w_list)
    if not list_w:
        return W_BytearrayObject([])
    data = w_self.data
    newdata = []
    for i in range(len(list_w)):
        w_s = list_w[i]
        if not (space.isinstance_w(w_s, space.w_str) or
                space.isinstance_w(w_s, space.w_bytearray)):
            raise oefmt(space.w_TypeError,
                        "sequence item %d: expected string, %T found", i, w_s)

        if data and i != 0:
            newdata.extend(data)
        newdata.extend([c for c in space.buffer_w(w_s).as_str()])
    return W_BytearrayObject(newdata)

_space_chars = ''.join([chr(c) for c in [9, 10, 11, 12, 13, 32]])


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


class BytearrayBuffer(RWBuffer):
    def __init__(self, data):
        self.data = data

    def getlength(self):
        return len(self.data)

    def getitem(self, index):
        return self.data[index]

    def setitem(self, index, char):
        self.data[index] = char
