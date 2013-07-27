"""The builtin bytearray implementation"""

from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.interpreter.buffer import RWBuffer
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault
from pypy.interpreter.signature import Signature
from pypy.objspace.std import bytesobject
from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.inttype import wrapint
from pypy.objspace.std.model import W_Object, registerimplementation
from pypy.objspace.std.multimethod import FailedToImplement
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.objspace.std.sliceobject import W_SliceObject, normalize_simple_slice
from pypy.objspace.std.stdtypedef import StdTypeDef, SMM
from pypy.objspace.std.stringmethods import StringMethods
from pypy.objspace.std.unicodeobject import W_UnicodeObject
from pypy.objspace.std.util import get_positive_index
from rpython.rlib.objectmodel import newlist_hint, resizelist_hint
from rpython.rlib.rstring import StringBuilder


def _make_data(s):
    return [s[i] for i in range(len(s))]

class W_BytearrayObject(W_Object, StringMethods):
    def __init__(w_self, data):
        w_self.data = data

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%s)" % (w_self.__class__.__name__, ''.join(w_self.data))

    def _new(self, value):
        return W_BytearrayObject(_make_data(value))

    def _len(self):
        return len(self.data)

    def _val(self, space):
        return space.bufferstr_w(self)

    def _op_val(self, space, w_other):
        return space.bufferstr_new_w(w_other)

    def _chr(self, char):
        assert len(char) == 1
        return str(char)[0]

    _empty = ''
    _builder = StringBuilder

    def _newlist_unwrapped(self, space, res):
        return space.newlist([W_BytearrayObject(_make_data(i)) for i in res])

    def _isupper(self, ch):
        return ch.isupper()

    def _islower(self, ch):
        return ch.islower()

    def _istitle(self, ch):
        return ch.istitle()

    def _isspace(self, ch):
        return ch.isspace()

    def _isalpha(self, ch):
        return ch.isalpha()

    def _isalnum(self, ch):
        return ch.isalnum()

    def _isdigit(self, ch):
        return ch.isdigit()

    _iscased = _isalpha

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

    def _join_return_one(self, space, w_obj):
        return space.is_w(space.type(w_obj), space.w_unicode)

    def _join_check_item(self, space, w_obj):
        if (space.is_w(space.type(w_obj), space.w_str) or
            space.is_w(space.type(w_obj), space.w_bytearray)):
            return 0
        return 1

    def ord(self, space):
        if len(self.data) != 1:
            msg = "ord() expected a character, but string of length %d found"
            raise operationerrfmt(space.w_TypeError, msg, len(self.data))
        return space.wrap(ord(self.data[0]))

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
            result = self.data.remove(chr(char))
        except ValueError:
            raise OperationError(space.w_ValueError, space.wrap(
                "value not found in bytearray"))

    def descr_reverse(self, space):
        self.data.reverse()

W_BytearrayObject.EMPTY = W_BytearrayObject([])


bytearray_append  = SMM('append', 2)
bytearray_extend  = SMM('extend', 2)
bytearray_insert  = SMM('insert', 3,
                    doc="B.insert(index, int) -> None\n\n"
                    "Insert a single item into the bytearray before "
                    "the given index.")

bytearray_pop  = SMM('pop', 2, defaults=(-1,),
                    doc="B.pop([index]) -> int\n\nRemove and return a "
                    "single item from B. If no index\nargument is given, "
                    "will pop the last value.")

bytearray_remove  = SMM('remove', 2,
                    doc="B.remove(int) -> None\n\n"
                    "Remove the first occurance of a value in B.")

bytearray_reverse  = SMM('reverse', 1,
                    doc="B.reverse() -> None\n\n"
                    "Reverse the order of the values in B in place.")

bytearray_strip  = SMM('strip', 2, defaults=(None,),
                    doc="B.strip([bytes]) -> bytearray\n\nStrip leading "
                    "and trailing bytes contained in the argument.\nIf "
                    "the argument is omitted, strip ASCII whitespace.")

bytearray_lstrip  = SMM('lstrip', 2, defaults=(None,),
                    doc="B.lstrip([bytes]) -> bytearray\n\nStrip leading "
                    "bytes contained in the argument.\nIf the argument is "
                    "omitted, strip leading ASCII whitespace.")

bytearray_rstrip  = SMM('rstrip', 2, defaults=(None,),
                    doc="'B.rstrip([bytes]) -> bytearray\n\nStrip trailing "
                    "bytes contained in the argument.\nIf the argument is "
                    "omitted, strip trailing ASCII whitespace.")

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


def descr__new__(space, w_bytearraytype, __args__):
    return new_bytearray(space,w_bytearraytype, [])


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

def descr_bytearray__reduce__(space, w_self):
    assert isinstance(w_self, W_BytearrayObject)
    w_dict = w_self.getdict(space)
    if w_dict is None:
        w_dict = space.w_None
    return space.newtuple([
        space.type(w_self), space.newtuple([
            space.wrap(''.join(w_self.data).decode('latin-1')),
            space.wrap('latin-1')]),
        w_dict])

def _hex_digit_to_int(d):
    val = ord(d)
    if 47 < val < 58:
        return val - 48
    if 96 < val < 103:
        return val - 87
    return -1

def descr_fromhex(space, w_type, w_hexstring):
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

# ____________________________________________________________

bytearray_typedef = W_BytearrayObject.typedef = StdTypeDef(
    "bytearray",
    __doc__ = '''bytearray() -> an empty bytearray
bytearray(sequence) -> bytearray initialized from sequence\'s items

If the argument is a bytearray, the return value is the same object.''',
    __new__ = interp2app(descr__new__),
    __hash__ = None,
    __reduce__ = interp2app(descr_bytearray__reduce__),
    fromhex = interp2app(descr_fromhex, as_classmethod=True),

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
registerimplementation(W_BytearrayObject)

init_signature = Signature(['source', 'encoding', 'errors'], None, None)
init_defaults = [None, None, None]

def len__Bytearray(space, w_bytearray):
    result = len(w_bytearray.data)
    return wrapint(space, result)

def ord__Bytearray(space, w_bytearray):
    if len(w_bytearray.data) != 1:
        raise OperationError(space.w_TypeError,
                             space.wrap("expected a character, but string"
                            "of length %s found" % len(w_bytearray.data)))
    return space.wrap(ord(w_bytearray.data[0]))

def getitem__Bytearray_ANY(space, w_bytearray, w_index):
    # getindex_w should get a second argument space.w_IndexError,
    # but that doesn't exist the first time this is called.
    try:
        w_IndexError = space.w_IndexError
    except AttributeError:
        w_IndexError = None
    index = space.getindex_w(w_index, w_IndexError, "bytearray index")
    try:
        return space.newint(ord(w_bytearray.data[index]))
    except IndexError:
        raise OperationError(space.w_IndexError,
                             space.wrap("bytearray index out of range"))

def getitem__Bytearray_Slice(space, w_bytearray, w_slice):
    data = w_bytearray.data
    length = len(data)
    start, stop, step, slicelength = w_slice.indices4(space, length)
    assert slicelength >= 0
    if step == 1 and 0 <= start <= stop:
        newdata = data[start:stop]
    else:
        newdata = _getitem_slice_multistep(data, start, step, slicelength)
    return W_BytearrayObject(newdata)

def _getitem_slice_multistep(data, start, step, slicelength):
    return [data[start + i*step] for i in range(slicelength)]

def contains__Bytearray_Int(space, w_bytearray, w_char):
    char = space.int_w(w_char)
    if not 0 <= char < 256:
        raise OperationError(space.w_ValueError,
                             space.wrap("byte must be in range(0, 256)"))
    for c in w_bytearray.data:
        if ord(c) == char:
            return space.w_True
    return space.w_False

def contains__Bytearray_String(space, w_bytearray, w_str):
    # XXX slow - copies, needs rewriting
    w_str2 = str__Bytearray(space, w_bytearray)
    return bytesobject.contains__String_String(space, w_str2, w_str)

def contains__Bytearray_ANY(space, w_bytearray, w_sub):
    # XXX slow - copies, needs rewriting
    w_str = space.wrap(space.bufferstr_new_w(w_sub))
    w_str2 = str__Bytearray(space, w_bytearray)
    return bytesobject.contains__String_String(space, w_str2, w_str)

def add__Bytearray_Bytearray(space, w_bytearray1, w_bytearray2):
    data1 = w_bytearray1.data
    data2 = w_bytearray2.data
    return W_BytearrayObject(data1 + data2)

def add__Bytearray_ANY(space, w_bytearray1, w_other):
    data1 = w_bytearray1.data
    data2 = [c for c in space.bufferstr_new_w(w_other)]
    return W_BytearrayObject(data1 + data2)

def add__String_Bytearray(space, w_str, w_bytearray):
    data2 = w_bytearray.data
    data1 = [c for c in space.str_w(w_str)]
    return W_BytearrayObject(data1 + data2)

def eq__Bytearray_Bytearray(space, w_bytearray1, w_bytearray2):
    data1 = w_bytearray1.data
    data2 = w_bytearray2.data
    if len(data1) != len(data2):
        return space.w_False
    for i in range(len(data1)):
        if data1[i] != data2[i]:
            return space.w_False
    return space.w_True

def eq__Bytearray_String(space, w_bytearray, w_other):
    return space.eq(str__Bytearray(space, w_bytearray), w_other)

def eq__Bytearray_Unicode(space, w_bytearray, w_other):
    return space.w_False

def eq__Unicode_Bytearray(space, w_other, w_bytearray):
    return space.w_False

def ne__Bytearray_String(space, w_bytearray, w_other):
    return space.ne(str__Bytearray(space, w_bytearray), w_other)

def ne__Bytearray_Unicode(space, w_bytearray, w_other):
    return space.w_True

def ne__Unicode_Bytearray(space, w_other, w_bytearray):
    return space.w_True

def _min(a, b):
    if a < b:
        return a
    return b

def lt__Bytearray_Bytearray(space, w_bytearray1, w_bytearray2):
    data1 = w_bytearray1.data
    data2 = w_bytearray2.data
    ncmp = _min(len(data1), len(data2))
    # Search for the first index where items are different
    for p in range(ncmp):
        if data1[p] != data2[p]:
            return space.newbool(data1[p] < data2[p])
    # No more items to compare -- compare sizes
    return space.newbool(len(data1) < len(data2))

def gt__Bytearray_Bytearray(space, w_bytearray1, w_bytearray2):
    data1 = w_bytearray1.data
    data2 = w_bytearray2.data
    ncmp = _min(len(data1), len(data2))
    # Search for the first index where items are different
    for p in range(ncmp):
        if data1[p] != data2[p]:
            return space.newbool(data1[p] > data2[p])
    # No more items to compare -- compare sizes
    return space.newbool(len(data1) > len(data2))

def str_count__Bytearray_ANY_ANY_ANY(space, w_bytearray, w_char, w_start, w_stop):
    w_char = space.wrap(space.bufferstr_new_w(w_char))
    w_str = str__Bytearray(space, w_bytearray)
    return bytesobject.str_count__String_String_ANY_ANY(space, w_str, w_char,
                                                         w_start, w_stop)

def str_index__Bytearray_ANY_ANY_ANY(space, w_bytearray, w_char, w_start, w_stop):
    w_char = space.wrap(space.bufferstr_new_w(w_char))
    w_str = str__Bytearray(space, w_bytearray)
    return bytesobject.str_index__String_String_ANY_ANY(space, w_str, w_char,
                                                         w_start, w_stop)

def str_rindex__Bytearray_ANY_ANY_ANY(space, w_bytearray, w_char, w_start, w_stop):
    w_char = space.wrap(space.bufferstr_new_w(w_char))
    w_str = str__Bytearray(space, w_bytearray)
    return bytesobject.str_rindex__String_String_ANY_ANY(space, w_str, w_char,
                                                         w_start, w_stop)

def str_find__Bytearray_ANY_ANY_ANY(space, w_bytearray, w_char, w_start, w_stop):
    w_char = space.wrap(space.bufferstr_new_w(w_char))
    w_str = str__Bytearray(space, w_bytearray)
    return bytesobject.str_find__String_String_ANY_ANY(space, w_str, w_char,
                                                         w_start, w_stop)

def str_rfind__Bytearray_ANY_ANY_ANY(space, w_bytearray, w_char, w_start, w_stop):
    w_char = space.wrap(space.bufferstr_new_w(w_char))
    w_str = str__Bytearray(space, w_bytearray)
    return bytesobject.str_rfind__String_String_ANY_ANY(space, w_str, w_char,
                                                         w_start, w_stop)

def str_startswith__Bytearray_ANY_ANY_ANY(space, w_bytearray, w_prefix, w_start, w_stop):
    if space.isinstance_w(w_prefix, space.w_tuple):
        w_str = str__Bytearray(space, w_bytearray)
        w_prefix = space.newtuple([space.wrap(space.bufferstr_new_w(w_entry)) for w_entry in
                                   space.fixedview(w_prefix)])
        return bytesobject.str_startswith__String_ANY_ANY_ANY(space, w_str, w_prefix,
                                                                  w_start, w_stop)

    w_prefix = space.wrap(space.bufferstr_new_w(w_prefix))
    w_str = str__Bytearray(space, w_bytearray)
    return bytesobject.str_startswith__String_String_ANY_ANY(space, w_str, w_prefix,
                                                              w_start, w_stop)

def str_endswith__Bytearray_ANY_ANY_ANY(space, w_bytearray, w_suffix, w_start, w_stop):
    if space.isinstance_w(w_suffix, space.w_tuple):
        w_str = str__Bytearray(space, w_bytearray)
        w_suffix = space.newtuple([space.wrap(space.bufferstr_new_w(w_entry)) for w_entry in
                                   space.fixedview(w_suffix)])
        return bytesobject.str_endswith__String_ANY_ANY_ANY(space, w_str, w_suffix,
                                                                  w_start, w_stop)
    w_suffix = space.wrap(space.bufferstr_new_w(w_suffix))
    w_str = str__Bytearray(space, w_bytearray)
    return bytesobject.str_endswith__String_String_ANY_ANY(space, w_str, w_suffix,
                                                              w_start, w_stop)

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

def str_decode__Bytearray_ANY_ANY(space, w_bytearray, w_encoding, w_errors):
    w_str = str__Bytearray(space, w_bytearray)
    return bytesobject.str_decode__String_ANY_ANY(space, w_str, w_encoding, w_errors)

def str_islower__Bytearray(space, w_bytearray):
    w_str = str__Bytearray(space, w_bytearray)
    return bytesobject.str_islower__String(space, w_str)

def str_isupper__Bytearray(space, w_bytearray):
    w_str = str__Bytearray(space, w_bytearray)
    return bytesobject.str_isupper__String(space, w_str)

def str_isalpha__Bytearray(space, w_bytearray):
    w_str = str__Bytearray(space, w_bytearray)
    return bytesobject.str_isalpha__String(space, w_str)

def str_isalnum__Bytearray(space, w_bytearray):
    w_str = str__Bytearray(space, w_bytearray)
    return bytesobject.str_isalnum__String(space, w_str)

def str_isdigit__Bytearray(space, w_bytearray):
    w_str = str__Bytearray(space, w_bytearray)
    return bytesobject.str_isdigit__String(space, w_str)

def str_istitle__Bytearray(space, w_bytearray):
    w_str = str__Bytearray(space, w_bytearray)
    return bytesobject.str_istitle__String(space, w_str)

def str_isspace__Bytearray(space, w_bytearray):
    w_str = str__Bytearray(space, w_bytearray)
    return bytesobject.str_isspace__String(space, w_str)

_space_chars = ''.join([chr(c) for c in [9, 10, 11, 12, 13, 32]])

def bytearray_strip__Bytearray_None(space, w_bytearray, w_chars):
    return _strip(space, w_bytearray, _space_chars, 1, 1)

def bytearray_strip__Bytearray_ANY(space, w_bytearray, w_chars):
    return _strip(space, w_bytearray, space.bufferstr_new_w(w_chars), 1, 1)

def bytearray_lstrip__Bytearray_None(space, w_bytearray, w_chars):
    return _strip(space, w_bytearray, _space_chars, 1, 0)

def bytearray_lstrip__Bytearray_ANY(space, w_bytearray, w_chars):
    return _strip(space, w_bytearray, space.bufferstr_new_w(w_chars), 1, 0)

def bytearray_rstrip__Bytearray_None(space, w_bytearray, w_chars):
    return _strip(space, w_bytearray, _space_chars, 0, 1)

def bytearray_rstrip__Bytearray_ANY(space, w_bytearray, w_chars):
    return _strip(space, w_bytearray, space.bufferstr_new_w(w_chars), 0, 1)

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

def _strip(space, w_bytearray, u_chars, left, right):
    # note: mostly copied from bytesobject._strip
    # should really be shared
    u_self = w_bytearray.data

    lpos = 0
    rpos = len(u_self)

    if left:
        while lpos < rpos and u_self[lpos] in u_chars:
            lpos += 1

    if right:
        while rpos > lpos and u_self[rpos - 1] in u_chars:
            rpos -= 1
        assert rpos >= 0

    return new_bytearray(space, space.w_bytearray, u_self[lpos:rpos])

# __________________________________________________________
# Buffer interface

class BytearrayBuffer(RWBuffer):
    def __init__(self, data):
        self.data = data

    def getlength(self):
        return len(self.data)

    def getitem(self, index):
        return self.data[index]

    def setitem(self, index, char):
        self.data[index] = char

def buffer__Bytearray(space, self):
    b = BytearrayBuffer(self.data)
    return space.wrap(b)
