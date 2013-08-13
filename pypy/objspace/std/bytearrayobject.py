"""The builtin bytearray implementation"""

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.buffer import RWBuffer
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault
from pypy.interpreter.signature import Signature
from pypy.objspace.std.sliceobject import W_SliceObject
from pypy.objspace.std.stdtypedef import StdTypeDef
from pypy.objspace.std.stringmethods import StringMethods
from pypy.objspace.std.util import get_positive_index
from rpython.rlib.objectmodel import newlist_hint, resizelist_hint
from rpython.rlib.rstring import StringBuilder


def _make_data(s):
    return [s[i] for i in range(len(s))]

class W_BytearrayObject(W_Root, StringMethods):
    def __init__(w_self, data):
        w_self.data = data

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%s)" % (w_self.__class__.__name__, ''.join(w_self.data))

    def _new(self, value):
        return W_BytearrayObject(_make_data(value))

    def _new_from_list(self, value):
        return W_BytearrayObject(value)

    def _empty(self):
        return W_BytearrayObject([])

    def _len(self):
        return len(self.data)

    def _val(self, space):
        return space.bufferstr_w(self)

    def _op_val(self, space, w_other):
        return space.bufferstr_new_w(w_other)

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
            msg = "ord() expected a character, but string of length %d found"
            raise operationerrfmt(space.w_TypeError, msg, len(self.data))
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
        "bytearray.fromhex(string) -> bytearray\n"
        "\n"
        "Create a bytearray object from a string of hexadecimal numbers.\n"
        "Spaces between two numbers are accepted.\n"
        "Example: bytearray.fromhex('B9 01EF') -> bytearray(b'\\xb9\\x01\\xef')."
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
            if i+1 == length:
                raise OperationError(space.w_ValueError, space.wrap(
                    "non-hexadecimal number found in fromhex() arg at position %d" % i))

            top = _hex_digit_to_int(hexstring[i])
            if top == -1:
                raise OperationError(space.w_ValueError, space.wrap(
                    "non-hexadecimal number found in fromhex() arg at position %d" % i))
            bot = _hex_digit_to_int(hexstring[i+1])
            if bot == -1:
                raise OperationError(space.w_ValueError, space.wrap(
                    "non-hexadecimal number found in fromhex() arg at position %d" % (i+1,)))
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
            encoding, errors = _get_encoding_and_errors(space, w_encoding, w_errors)

            # if w_source is an integer this correctly raises a TypeError
            # the CPython error message is: "encoding or errors without a string argument"
            # ours is: "expected unicode, got int object"
            w_source = encode_object(space, w_source, encoding, errors)

        # Is it an int?
        try:
            count = space.int_w(w_source)
        except OperationError, e:
            if not e.match(space, space.w_TypeError):
                raise
        else:
            if count < 0:
                raise OperationError(space.w_ValueError,
                                     space.wrap("bytearray negative count"))
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
                buf.append("0123456789abcdef"[n>>4])
                buf.append("0123456789abcdef"[n&0xF])
            else:
                buf.append(c)

        buf.append("')")

        return space.wrap(buf.build())

    def descr_str(self, space):
        return space.wrap(''.join(self.data))

    def descr_buffer(self, space):
        return BytearrayBuffer(self.data)

    def descr_inplace_add(self, space, w_other):
        if isinstance(w_other, W_BytearrayObject):
            self.data += w_other.data
        else:
            self.data += self._op_val(space, w_other)
        return self

    def descr_inplace_mul(self, space, w_times):
        try:
            times = space.getindex_w(w_times, space.w_OverflowError)
        except OperationError, e:
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
            idx = space.getindex_w(w_index, space.w_IndexError, "bytearray index")
            try:
                self.data[idx] = getbytevalue(space, w_other)
            except IndexError:
                raise OperationError(space.w_IndexError,
                                     space.wrap("bytearray index out of range"))

    def descr_delitem(self, space, w_idx):
        if isinstance(w_idx, W_SliceObject):
            start, stop, step, slicelength = w_idx.indices4(space,
                                                            len(self.data))
            _delitem_slice_helper(space, self.data, start, step, slicelength)
        else:
            idx = space.getindex_w(w_idx, space.w_IndexError, "bytearray index")
            try:
                del self.data[idx]
            except IndexError:
                raise OperationError(space.w_IndexError,
                                     space.wrap("bytearray deletion index out of range"))

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
                raise OperationError(space.w_IndexError, space.wrap(
                    "pop from empty bytearray"))
            raise OperationError(space.w_IndexError, space.wrap(
                "pop index out of range"))
        return space.wrap(ord(result))

    def descr_remove(self, space, w_char):
        char = space.int_w(space.index(w_char))
        try:
            self.data.remove(chr(char))
        except ValueError:
            raise OperationError(space.w_ValueError, space.wrap(
                "value not found in bytearray"))

    def descr_reverse(self, space):
        self.data.reverse()

def getbytevalue(space, w_value):
    if space.isinstance_w(w_value, space.w_str):
        string = space.str_w(w_value)
        if len(string) != 1:
            raise OperationError(space.w_ValueError, space.wrap(
                "string must be of size 1"))
        return string[0]

    value = space.getindex_w(w_value, None)
    if not 0 <= value < 256:
        # this includes the OverflowError in case the long is too large
        raise OperationError(space.w_ValueError, space.wrap(
            "byte must be in range(0, 256)"))
    return chr(value)

def new_bytearray(space, w_bytearraytype, data):
    w_obj = space.allocate_instance(W_BytearrayObject, w_bytearraytype)
    W_BytearrayObject.__init__(w_obj, data)
    return w_obj


def makebytearraydata_w(space, w_source):
    # String-like argument
    try:
        string = space.bufferstr_new_w(w_source)
    except OperationError, e:
        if not e.match(space, space.w_TypeError):
            raise
    else:
        return [c for c in string]

    # sequence of bytes
    w_iter = space.iter(w_source)
    length_hint = space.length_hint(w_source, 0)
    data = newlist_hint(length_hint)
    extended = 0
    while True:
        try:
            w_item = space.next(w_iter)
        except OperationError, e:
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


W_BytearrayObject.typedef = StdTypeDef(
    "bytearray",
    __doc__ = '''bytearray() -> an empty bytearray
bytearray(sequence) -> bytearray initialized from sequence\'s items

If the argument is a bytearray, the return value is the same object.''',
    __new__ = interp2app(W_BytearrayObject.descr_new),
    __hash__ = None,
    __reduce__ = interp2app(W_BytearrayObject.descr_reduce),
    fromhex = interp2app(W_BytearrayObject.descr_fromhex, as_classmethod=True),

    __repr__ = interp2app(W_BytearrayObject.descr_repr),
    __str__ = interp2app(W_BytearrayObject.descr_str),

    __eq__ = interp2app(W_BytearrayObject.descr_eq),
    __ne__ = interp2app(W_BytearrayObject.descr_ne),
    __lt__ = interp2app(W_BytearrayObject.descr_lt),
    __le__ = interp2app(W_BytearrayObject.descr_le),
    __gt__ = interp2app(W_BytearrayObject.descr_gt),
    __ge__ = interp2app(W_BytearrayObject.descr_ge),

    __len__ = interp2app(W_BytearrayObject.descr_len),
    __contains__ = interp2app(W_BytearrayObject.descr_contains),

    __add__ = interp2app(W_BytearrayObject.descr_add),
    __mul__ = interp2app(W_BytearrayObject.descr_mul),
    __rmul__ = interp2app(W_BytearrayObject.descr_mul),

    __getitem__ = interp2app(W_BytearrayObject.descr_getitem),

    capitalize = interp2app(W_BytearrayObject.descr_capitalize),
    center = interp2app(W_BytearrayObject.descr_center),
    count = interp2app(W_BytearrayObject.descr_count),
    decode = interp2app(W_BytearrayObject.descr_decode),
    expandtabs = interp2app(W_BytearrayObject.descr_expandtabs),
    find = interp2app(W_BytearrayObject.descr_find),
    rfind = interp2app(W_BytearrayObject.descr_rfind),
    index = interp2app(W_BytearrayObject.descr_index),
    rindex = interp2app(W_BytearrayObject.descr_rindex),
    isalnum = interp2app(W_BytearrayObject.descr_isalnum),
    isalpha = interp2app(W_BytearrayObject.descr_isalpha),
    isdigit = interp2app(W_BytearrayObject.descr_isdigit),
    islower = interp2app(W_BytearrayObject.descr_islower),
    isspace = interp2app(W_BytearrayObject.descr_isspace),
    istitle = interp2app(W_BytearrayObject.descr_istitle),
    isupper = interp2app(W_BytearrayObject.descr_isupper),
    join = interp2app(W_BytearrayObject.descr_join),
    ljust = interp2app(W_BytearrayObject.descr_ljust),
    rjust = interp2app(W_BytearrayObject.descr_rjust),
    lower = interp2app(W_BytearrayObject.descr_lower),
    partition = interp2app(W_BytearrayObject.descr_partition),
    rpartition = interp2app(W_BytearrayObject.descr_rpartition),
    replace = interp2app(W_BytearrayObject.descr_replace),
    split = interp2app(W_BytearrayObject.descr_split),
    rsplit = interp2app(W_BytearrayObject.descr_rsplit),
    splitlines = interp2app(W_BytearrayObject.descr_splitlines),
    startswith = interp2app(W_BytearrayObject.descr_startswith),
    endswith = interp2app(W_BytearrayObject.descr_endswith),
    strip = interp2app(W_BytearrayObject.descr_strip),
    lstrip = interp2app(W_BytearrayObject.descr_lstrip),
    rstrip = interp2app(W_BytearrayObject.descr_rstrip),
    swapcase = interp2app(W_BytearrayObject.descr_swapcase),
    title = interp2app(W_BytearrayObject.descr_title),
    translate = interp2app(W_BytearrayObject.descr_translate),
    upper = interp2app(W_BytearrayObject.descr_upper),
    zfill = interp2app(W_BytearrayObject.descr_zfill),

    __init__ = interp2app(W_BytearrayObject.descr_init),
    __buffer__ = interp2app(W_BytearrayObject.descr_buffer),

    __iadd__ = interp2app(W_BytearrayObject.descr_inplace_add),
    __imul__ = interp2app(W_BytearrayObject.descr_inplace_mul),
    __setitem__ = interp2app(W_BytearrayObject.descr_setitem),
    __delitem__ = interp2app(W_BytearrayObject.descr_delitem),

    append = interp2app(W_BytearrayObject.descr_append),
    extend = interp2app(W_BytearrayObject.descr_extend),
    insert = interp2app(W_BytearrayObject.descr_insert),
    pop = interp2app(W_BytearrayObject.descr_pop),
    remove = interp2app(W_BytearrayObject.descr_remove),
    reverse = interp2app(W_BytearrayObject.descr_reverse),
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
            msg = "sequence item %d: expected string, %T found"
            raise operationerrfmt(space.w_TypeError, msg, i, w_s)

        if data and i != 0:
            newdata.extend(data)
        newdata.extend([c for c in space.bufferstr_new_w(w_s)])
    return W_BytearrayObject(newdata)

_space_chars = ''.join([chr(c) for c in [9, 10, 11, 12, 13, 32]])

#XXX share the code again with the stuff in listobject.py
def _delitem_slice_helper(space, items, start, step, slicelength):
    if slicelength==0:
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
        raise operationerrfmt(space.w_ValueError, "attempt to "
              "assign sequence of size %d to extended slice of size %d",
              len2, slicelength)

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
