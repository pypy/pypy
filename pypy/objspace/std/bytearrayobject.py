"""The builtin bytearray implementation"""

from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.interpreter.buffer import RWBuffer
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.signature import Signature
from pypy.objspace.std.bytesobject import (
    W_StringObject, str_decode,
    str_count, str_index, str_rindex, str_find, str_rfind, str_replace,
    str_startswith, str_endswith, str_islower, str_isupper, str_isalpha,
    str_isalnum, str_isdigit, str_isspace, str_istitle,
    str_upper, str_lower, str_title, str_swapcase, str_capitalize,
    str_expandtabs, str_ljust, str_rjust, str_center, str_zfill,
    str_join, str_split, str_rsplit, str_partition, str_rpartition,
    str_splitlines, str_translate)
from pypy.objspace.std import bytesobject
from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.inttype import wrapint
from pypy.objspace.std.model import W_Object, registerimplementation
from pypy.objspace.std.multimethod import FailedToImplement
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.sliceobject import W_SliceObject, normalize_simple_slice
from pypy.objspace.std.stdtypedef import StdTypeDef, SMM
from pypy.objspace.std.stringmethods import StringMethods
from pypy.objspace.std.unicodeobject import W_UnicodeObject
from pypy.objspace.std.util import get_positive_index
from rpython.rlib.objectmodel import newlist_hint, resizelist_hint
from rpython.rlib.rstring import StringBuilder


class W_BytearrayObject(W_Object, StringMethods):
    def __init__(w_self, data):
        w_self.data = data

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%s)" % (w_self.__class__.__name__, ''.join(w_self.data))

    def _new(self, value):
        return W_BytearrayObject(value)

    def _self_value(self):
        return self.data


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

#    __repr__ = interp2app(W_BytearrayObject.descr_repr),
#    __str__ = interp2app(W_BytearrayObject.descr_str),

#    __eq__ = interp2app(W_BytearrayObject.descr_eq),
#    __ne__ = interp2app(W_BytearrayObject.descr_ne),
#    __lt__ = interp2app(W_BytearrayObject.descr_lt),
#    __le__ = interp2app(W_BytearrayObject.descr_le),
#    __gt__ = interp2app(W_BytearrayObject.descr_gt),
#    __ge__ = interp2app(W_BytearrayObject.descr_ge),

#    __len__ = interp2app(W_BytearrayObject.descr_len),
#    __iter__ = interp2app(W_BytearrayObject.descr_iter),
#    __contains__ = interp2app(W_BytearrayObject.descr_contains),

#    __add__ = interp2app(W_BytearrayObject.descr_add),
    __mul__ = interp2app(W_BytearrayObject.descr_mul),
    __rmul__ = interp2app(W_BytearrayObject.descr_mul),

#    __getitem__ = interp2app(W_BytearrayObject.descr_getitem),

#    capitalize = interp2app(W_BytearrayObject.descr_capitalize),
#    center = interp2app(W_BytearrayObject.descr_center),
#    count = interp2app(W_BytearrayObject.descr_count),
#    decode = interp2app(W_BytearrayObject.descr_decode),
#    expandtabs = interp2app(W_BytearrayObject.descr_expandtabs),
#    find = interp2app(W_BytearrayObject.descr_find),
#    rfind = interp2app(W_BytearrayObject.descr_rfind),
#    index = interp2app(W_BytearrayObject.descr_index),
#    rindex = interp2app(W_BytearrayObject.descr_rindex),
#    isalnum = interp2app(W_BytearrayObject.descr_isalnum),
#    isalpha = interp2app(W_BytearrayObject.descr_isalpha),
#    isdigit = interp2app(W_BytearrayObject.descr_isdigit),
#    islower = interp2app(W_BytearrayObject.descr_islower),
#    isspace = interp2app(W_BytearrayObject.descr_isspace),
#    istitle = interp2app(W_BytearrayObject.descr_istitle),
#    isupper = interp2app(W_BytearrayObject.descr_isupper),
#    join = interp2app(W_BytearrayObject.descr_join),
#    ljust = interp2app(W_BytearrayObject.descr_ljust),
#    rjust = interp2app(W_BytearrayObject.descr_rjust),
#    lower = interp2app(W_BytearrayObject.descr_lower),
#    partition = interp2app(W_BytearrayObject.descr_partition),
#    rpartition = interp2app(W_BytearrayObject.descr_rpartition),
#    replace = interp2app(W_BytearrayObject.descr_replace),
#    split = interp2app(W_BytearrayObject.descr_split),
#    rsplit = interp2app(W_BytearrayObject.descr_rsplit),
#    splitlines = interp2app(W_BytearrayObject.descr_splitlines),
#    startswith = interp2app(W_BytearrayObject.descr_startswith),
#    endswith = interp2app(W_BytearrayObject.descr_endswith),
#    strip = interp2app(W_BytearrayObject.descr_strip),
#    lstrip = interp2app(W_BytearrayObject.descr_lstrip),
#    rstrip = interp2app(W_BytearrayObject.descr_rstrip),
#    swapcase = interp2app(W_BytearrayObject.descr_swapcase),
#    title = interp2app(W_BytearrayObject.descr_title),
#    translate = interp2app(W_BytearrayObject.descr_translate),
#    upper = interp2app(W_BytearrayObject.descr_upper),
#    zfill = interp2app(W_BytearrayObject.descr_zfill),
)
bytearray_typedef.registermethods(globals())

registerimplementation(W_BytearrayObject)

init_signature = Signature(['source', 'encoding', 'errors'], None, None)
init_defaults = [None, None, None]

def init__Bytearray(space, w_bytearray, __args__):
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
        from pypy.objspace.std.unicodetype import (
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
        w_bytearray.data = ['\0'] * count
        return

    data = makebytearraydata_w(space, w_source)
    w_bytearray.data = data

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

def inplace_mul__Bytearray_ANY(space, w_bytearray, w_times):
    try:
        times = space.getindex_w(w_times, space.w_OverflowError)
    except OperationError, e:
        if e.match(space, space.w_TypeError):
            raise FailedToImplement
        raise
    w_bytearray.data *= times
    return w_bytearray

def eq__Bytearray_Bytearray(space, w_bytearray1, w_bytearray2):
    data1 = w_bytearray1.data
    data2 = w_bytearray2.data
    if len(data1) != len(data2):
        return space.w_False
    for i in range(len(data1)):
        if data1[i] != data2[i]:
            return space.w_False
    return space.w_True

def String2Bytearray(space, w_str):
    data = [c for c in space.str_w(w_str)]
    return W_BytearrayObject(data)

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

def str_translate__Bytearray_ANY_ANY(space, w_bytearray1, w_table, w_deletechars):
    # XXX slow, copies *twice* needs proper implementation
    w_str_copy = str__Bytearray(space, w_bytearray1)
    w_res = bytesobject.str_translate__String_ANY_ANY(space, w_str_copy,
                                                       w_table, w_deletechars)
    return String2Bytearray(space, w_res)

# Mostly copied from repr__String, but without the "smart quote"
# functionality.
def repr__Bytearray(space, w_bytearray):
    s = w_bytearray.data

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

def str__Bytearray(space, w_bytearray):
    return space.wrap(''.join(w_bytearray.data))

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
            raise operationerrfmt(
                space.w_TypeError,
                "sequence item %d: expected string, %s "
                "found", i, space.type(w_s).getname(space))

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

def bytearray_insert__Bytearray_Int_ANY(space, w_bytearray, w_idx, w_other):
    where = space.int_w(w_idx)
    length = len(w_bytearray.data)
    index = get_positive_index(where, length)
    val = getbytevalue(space, w_other)
    w_bytearray.data.insert(index, val)
    return space.w_None

def bytearray_pop__Bytearray_Int(space, w_bytearray, w_idx):
    index = space.int_w(w_idx)
    try:
        result = w_bytearray.data.pop(index)
    except IndexError:
        if not w_bytearray.data:
            raise OperationError(space.w_IndexError, space.wrap(
                "pop from empty bytearray"))
        raise OperationError(space.w_IndexError, space.wrap(
            "pop index out of range"))
    return space.wrap(ord(result))

def bytearray_remove__Bytearray_ANY(space, w_bytearray, w_char):
    char = space.int_w(space.index(w_char))
    try:
        result = w_bytearray.data.remove(chr(char))
    except ValueError:
        raise OperationError(space.w_ValueError, space.wrap(
            "value not found in bytearray"))

def bytearray_reverse__Bytearray(space, w_bytearray):
    w_bytearray.data.reverse()
    return space.w_None

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

# These methods could just delegate to the string implementation,
# but they have to return a bytearray.
def str_replace__Bytearray_ANY_ANY_ANY(space, w_bytearray, w_str1, w_str2, w_max):
    w_str = str__Bytearray(space, w_bytearray)
    w_res = bytesobject.str_replace__String_ANY_ANY_ANY(space, w_str, w_str1,
                                                         w_str2, w_max)
    return String2Bytearray(space, w_res)

def str_upper__Bytearray(space, w_bytearray):
    w_str = str__Bytearray(space, w_bytearray)
    w_res = bytesobject.str_upper__String(space, w_str)
    return String2Bytearray(space, w_res)

def str_lower__Bytearray(space, w_bytearray):
    w_str = str__Bytearray(space, w_bytearray)
    w_res = bytesobject.str_lower__String(space, w_str)
    return String2Bytearray(space, w_res)

def str_title__Bytearray(space, w_bytearray):
    w_str = str__Bytearray(space, w_bytearray)
    w_res = bytesobject.str_title__String(space, w_str)
    return String2Bytearray(space, w_res)

def str_swapcase__Bytearray(space, w_bytearray):
    w_str = str__Bytearray(space, w_bytearray)
    w_res = bytesobject.str_swapcase__String(space, w_str)
    return String2Bytearray(space, w_res)

def str_capitalize__Bytearray(space, w_bytearray):
    w_str = str__Bytearray(space, w_bytearray)
    w_res = bytesobject.str_capitalize__String(space, w_str)
    return String2Bytearray(space, w_res)

def str_ljust__Bytearray_ANY_ANY(space, w_bytearray, w_width, w_fillchar):
    w_str = str__Bytearray(space, w_bytearray)
    w_res = bytesobject.str_ljust__String_ANY_ANY(space, w_str, w_width,
                                                   w_fillchar)
    return String2Bytearray(space, w_res)

def str_rjust__Bytearray_ANY_ANY(space, w_bytearray, w_width, w_fillchar):
    w_str = str__Bytearray(space, w_bytearray)
    w_res = bytesobject.str_rjust__String_ANY_ANY(space, w_str, w_width,
                                                   w_fillchar)
    return String2Bytearray(space, w_res)

def str_center__Bytearray_ANY_ANY(space, w_bytearray, w_width, w_fillchar):
    w_str = str__Bytearray(space, w_bytearray)
    w_res = bytesobject.str_center__String_ANY_ANY(space, w_str, w_width,
                                                    w_fillchar)
    return String2Bytearray(space, w_res)

def str_zfill__Bytearray_ANY(space, w_bytearray, w_width):
    w_str = str__Bytearray(space, w_bytearray)
    w_res = bytesobject.str_zfill__String_ANY(space, w_str, w_width)
    return String2Bytearray(space, w_res)

def str_expandtabs__Bytearray_ANY(space, w_bytearray, w_tabsize):
    w_str = str__Bytearray(space, w_bytearray)
    w_res = bytesobject.str_expandtabs__String_ANY(space, w_str, w_tabsize)
    return String2Bytearray(space, w_res)

def str_splitlines__Bytearray_ANY(space, w_bytearray, w_keepends):
    w_str = str__Bytearray(space, w_bytearray)
    w_result = bytesobject.str_splitlines__String_ANY(space, w_str, w_keepends)
    return space.newlist([
        new_bytearray(space, space.w_bytearray, makebytearraydata_w(space, w_entry))
                        for w_entry in space.unpackiterable(w_result)
    ])

def str_split__Bytearray_ANY_ANY(space, w_bytearray, w_by, w_maxsplit=-1):
    w_str = str__Bytearray(space, w_bytearray)
    if not space.is_w(w_by, space.w_None):
        w_by = space.wrap(space.bufferstr_new_w(w_by))
    w_list = space.call_method(w_str, "split", w_by, w_maxsplit)
    length = space.int_w(space.len(w_list))
    for i in range(length):
        w_i = space.wrap(i)
        space.setitem(w_list, w_i, String2Bytearray(space, space.getitem(w_list, w_i)))
    return w_list

def str_rsplit__Bytearray_ANY_ANY(space, w_bytearray, w_by, w_maxsplit=-1):
    w_str = str__Bytearray(space, w_bytearray)
    if not space.is_w(w_by, space.w_None):
        w_by = space.wrap(space.bufferstr_new_w(w_by))
    w_list = space.call_method(w_str, "rsplit", w_by, w_maxsplit)
    length = space.int_w(space.len(w_list))
    for i in range(length):
        w_i = space.wrap(i)
        space.setitem(w_list, w_i, String2Bytearray(space, space.getitem(w_list, w_i)))
    return w_list

def str_partition__Bytearray_ANY(space, w_bytearray, w_sub):
    w_str = str__Bytearray(space, w_bytearray)
    w_sub = space.wrap(space.bufferstr_new_w(w_sub))
    w_tuple = bytesobject.str_partition__String_String(space, w_str, w_sub)
    w_a, w_b, w_c = space.fixedview(w_tuple, 3)
    return space.newtuple([
        String2Bytearray(space, w_a),
        String2Bytearray(space, w_b),
        String2Bytearray(space, w_c)])

def str_rpartition__Bytearray_ANY(space, w_bytearray, w_sub):
    w_str = str__Bytearray(space, w_bytearray)
    w_sub = space.wrap(space.bufferstr_new_w(w_sub))
    w_tuple = bytesobject.str_rpartition__String_String(space, w_str, w_sub)
    w_a, w_b, w_c = space.fixedview(w_tuple, 3)
    return space.newtuple([
        String2Bytearray(space, w_a),
        String2Bytearray(space, w_b),
        String2Bytearray(space, w_c)])

# __________________________________________________________
# Mutability methods

def bytearray_append__Bytearray_ANY(space, w_bytearray, w_item):
    w_bytearray.data.append(getbytevalue(space, w_item))

def bytearray_extend__Bytearray_Bytearray(space, w_bytearray, w_other):
    w_bytearray.data += w_other.data

def bytearray_extend__Bytearray_ANY(space, w_bytearray, w_other):
    w_bytearray.data += makebytearraydata_w(space, w_other)

def inplace_add__Bytearray_Bytearray(space, w_bytearray1, w_bytearray2):
    bytearray_extend__Bytearray_Bytearray(space, w_bytearray1, w_bytearray2)
    return w_bytearray1

def inplace_add__Bytearray_ANY(space, w_bytearray1, w_iterable2):
    w_bytearray1.data += space.bufferstr_new_w(w_iterable2)
    return w_bytearray1

def setitem__Bytearray_ANY_ANY(space, w_bytearray, w_index, w_item):
    idx = space.getindex_w(w_index, space.w_IndexError, "bytearray index")
    try:
        w_bytearray.data[idx] = getbytevalue(space, w_item)
    except IndexError:
        raise OperationError(space.w_IndexError,
                             space.wrap("bytearray index out of range"))

def setitem__Bytearray_Slice_ANY(space, w_bytearray, w_slice, w_other):
    oldsize = len(w_bytearray.data)
    start, stop, step, slicelength = w_slice.indices4(space, oldsize)
    sequence2 = makebytearraydata_w(space, w_other)
    _setitem_slice_helper(space, w_bytearray.data, start, step, slicelength, sequence2, empty_elem='\x00')

def delitem__Bytearray_ANY(space, w_bytearray, w_idx):
    idx = space.getindex_w(w_idx, space.w_IndexError, "bytearray index")
    try:
        del w_bytearray.data[idx]
    except IndexError:
        raise OperationError(space.w_IndexError,
                             space.wrap("bytearray deletion index out of range"))
    return space.w_None

def delitem__Bytearray_Slice(space, w_bytearray, w_slice):
    start, stop, step, slicelength = w_slice.indices4(space,
                                                      len(w_bytearray.data))
    _delitem_slice_helper(space, w_bytearray.data, start, step, slicelength)

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

register_all(vars(), globals())
