from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.objspace.std.model import registerimplementation, W_Object
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.inttype import wrapint
from pypy.objspace.std.multimethod import FailedToImplement
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.rlib.rarithmetic import intmask
from pypy.rlib.rstring import StringBuilder
from pypy.rlib.debug import check_annotation
from pypy.objspace.std import stringobject
from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.listobject import get_positive_index
from pypy.objspace.std.listtype import get_list_index
from pypy.objspace.std.sliceobject import W_SliceObject, normalize_simple_slice
from pypy.objspace.std.stringobject import W_StringObject
from pypy.objspace.std.tupleobject import W_TupleObject
from pypy.objspace.std.unicodeobject import W_UnicodeObject
from pypy.objspace.std import slicetype
from pypy.interpreter import gateway
from pypy.interpreter.argument import Signature
from pypy.interpreter.buffer import RWBuffer
from pypy.objspace.std.bytearraytype import (
    makebytearraydata_w, getbytevalue,
    new_bytearray
)
from pypy.tool.sourcetools import func_with_new_name


class W_BytearrayObject(W_Object):
    from pypy.objspace.std.bytearraytype import bytearray_typedef as typedef

    def __init__(w_self, data):
        w_self.data = data

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%s)" % (w_self.__class__.__name__, ''.join(w_self.data))

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
    newdata = [data[start + i*step] for i in range(slicelength)]
    return W_BytearrayObject(newdata)

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
    return stringobject.contains__String_String(space, w_str2, w_str)

def contains__Bytearray_ANY(space, w_bytearray, w_sub):
    # XXX slow - copies, needs rewriting
    w_str = space.wrap(space.bufferstr_new_w(w_sub))
    w_str2 = str__Bytearray(space, w_bytearray)
    return stringobject.contains__String_String(space, w_str2, w_str)

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

def mul_bytearray_times(space, w_bytearray, w_times):
    try:
        times = space.getindex_w(w_times, space.w_OverflowError)
    except OperationError, e:
        if e.match(space, space.w_TypeError):
            raise FailedToImplement
        raise
    data = w_bytearray.data
    return W_BytearrayObject(data * times)

def mul__Bytearray_ANY(space, w_bytearray, w_times):
    return mul_bytearray_times(space, w_bytearray, w_times)

def mul__ANY_Bytearray(space, w_times, w_bytearray):
    return mul_bytearray_times(space, w_bytearray, w_times)

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
    w_res = stringobject.str_translate__String_ANY_ANY(space, w_str_copy,
                                                       w_table, w_deletechars)
    return String2Bytearray(space, w_res)

# Mostly copied from repr__String, but without the "smart quote"
# functionality.
def repr__Bytearray(space, w_bytearray):
    s = w_bytearray.data

    buf = StringBuilder(50)

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

def _convert_idx_params(space, w_self, w_start, w_stop):
    start = slicetype._Eval_SliceIndex(space, w_start)
    stop = slicetype._Eval_SliceIndex(space, w_stop)
    length = len(w_self.data)
    if start < 0:
        start += length
        if start < 0:
            start = 0
    if stop < 0:
        stop += length
        if stop < 0:
            stop = 0
    return start, stop, length

def str_count__Bytearray_Int_ANY_ANY(space, w_bytearray, w_char, w_start, w_stop):
    char = w_char.intval
    start, stop, length = _convert_idx_params(space, w_bytearray, w_start, w_stop)
    count = 0
    for i in range(start, min(stop, length)):
        c = w_bytearray.data[i]
        if ord(c) == char:
            count += 1
    return space.wrap(count)

def str_count__Bytearray_ANY_ANY_ANY(space, w_bytearray, w_char, w_start, w_stop):
    w_char = space.wrap(space.bufferstr_new_w(w_char))
    w_str = str__Bytearray(space, w_bytearray)
    return stringobject.str_count__String_String_ANY_ANY(space, w_str, w_char,
                                                         w_start, w_stop)

def str_index__Bytearray_ANY_ANY_ANY(space, w_bytearray, w_char, w_start, w_stop):
    w_char = space.wrap(space.bufferstr_new_w(w_char))
    w_str = str__Bytearray(space, w_bytearray)
    return stringobject.str_index__String_String_ANY_ANY(space, w_str, w_char,
                                                         w_start, w_stop)

def str_rindex__Bytearray_ANY_ANY_ANY(space, w_bytearray, w_char, w_start, w_stop):
    w_char = space.wrap(space.bufferstr_new_w(w_char))
    w_str = str__Bytearray(space, w_bytearray)
    return stringobject.str_rindex__String_String_ANY_ANY(space, w_str, w_char,
                                                         w_start, w_stop)

def str_find__Bytearray_ANY_ANY_ANY(space, w_bytearray, w_char, w_start, w_stop):
    w_char = space.wrap(space.bufferstr_new_w(w_char))
    w_str = str__Bytearray(space, w_bytearray)
    return stringobject.str_find__String_String_ANY_ANY(space, w_str, w_char,
                                                         w_start, w_stop)

def str_rfind__Bytearray_ANY_ANY_ANY(space, w_bytearray, w_char, w_start, w_stop):
    w_char = space.wrap(space.bufferstr_new_w(w_char))
    w_str = str__Bytearray(space, w_bytearray)
    return stringobject.str_rfind__String_String_ANY_ANY(space, w_str, w_char,
                                                         w_start, w_stop)

def str_startswith__Bytearray_ANY_ANY_ANY(space, w_bytearray, w_prefix, w_start, w_stop):
    w_prefix = space.wrap(space.bufferstr_new_w(w_prefix))
    w_str = str__Bytearray(space, w_bytearray)
    return stringobject.str_startswith__String_String_ANY_ANY(space, w_str, w_prefix,
                                                              w_start, w_stop)

def str_startswith__Bytearray_Tuple_ANY_ANY(space, w_bytearray, w_prefix, w_start, w_stop):
    w_str = str__Bytearray(space, w_bytearray)
    w_prefix = space.newtuple([space.wrap(space.bufferstr_new_w(w_entry)) for w_entry in
                               space.unpackiterable(w_prefix)])
    return stringobject.str_startswith__String_Tuple_ANY_ANY(space, w_str, w_prefix,
                                                              w_start, w_stop)

def str_endswith__Bytearray_ANY_ANY_ANY(space, w_bytearray, w_suffix, w_start, w_stop):
    w_suffix = space.wrap(space.bufferstr_new_w(w_suffix))
    w_str = str__Bytearray(space, w_bytearray)
    return stringobject.str_endswith__String_String_ANY_ANY(space, w_str, w_suffix,
                                                              w_start, w_stop)

def str_endswith__Bytearray_Tuple_ANY_ANY(space, w_bytearray, w_suffix, w_start, w_stop):
    w_str = str__Bytearray(space, w_bytearray)
    w_suffix = space.newtuple([space.wrap(space.bufferstr_new_w(w_entry)) for w_entry in
                               space.unpackiterable(w_suffix)])
    return stringobject.str_endswith__String_Tuple_ANY_ANY(space, w_str, w_suffix,
                                                              w_start, w_stop)

def str_join__Bytearray_ANY(space, w_self, w_list):
    list_w = space.listview(w_list)
    if not list_w:
        return W_BytearrayObject([])
    data = w_self.data
    newdata = []
    for i in range(len(list_w)):
        w_s = list_w[i]
        if not (space.is_true(space.isinstance(w_s, space.w_str)) or
                space.is_true(space.isinstance(w_s, space.w_bytearray))):
            raise operationerrfmt(
                space.w_TypeError,
                "sequence item %d: expected string, %s "
                "found", i, space.type(w_s).getname(space, '?'))

        if data and i != 0:
            newdata.extend(data)
        newdata.extend([c for c in space.bufferstr_new_w(w_s)])
    return W_BytearrayObject(newdata)

def str_decode__Bytearray_ANY_ANY(space, w_bytearray, w_encoding, w_errors):
    w_str = str__Bytearray(space, w_bytearray)
    return stringobject.str_decode__String_ANY_ANY(space, w_str, w_encoding, w_errors)

def str_islower__Bytearray(space, w_bytearray):
    w_str = str__Bytearray(space, w_bytearray)
    return stringobject.str_islower__String(space, w_str)

def str_isupper__Bytearray(space, w_bytearray):
    w_str = str__Bytearray(space, w_bytearray)
    return stringobject.str_isupper__String(space, w_str)

def str_isalpha__Bytearray(space, w_bytearray):
    w_str = str__Bytearray(space, w_bytearray)
    return stringobject.str_isalpha__String(space, w_str)

def str_isalnum__Bytearray(space, w_bytearray):
    w_str = str__Bytearray(space, w_bytearray)
    return stringobject.str_isalnum__String(space, w_str)

def str_isdigit__Bytearray(space, w_bytearray):
    w_str = str__Bytearray(space, w_bytearray)
    return stringobject.str_isdigit__String(space, w_str)

def str_istitle__Bytearray(space, w_bytearray):
    w_str = str__Bytearray(space, w_bytearray)
    return stringobject.str_istitle__String(space, w_str)

def str_isspace__Bytearray(space, w_bytearray):
    w_str = str__Bytearray(space, w_bytearray)
    return stringobject.str_isspace__String(space, w_str)

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
            raise OperationError(space.w_OverflowError, space.wrap(
                "cannot pop an empty bytearray"))
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
    w_res = stringobject.str_replace__String_ANY_ANY_ANY(space, w_str, w_str1,
                                                         w_str2, w_max)
    return String2Bytearray(space, w_res)

def str_upper__Bytearray(space, w_bytearray):
    w_str = str__Bytearray(space, w_bytearray)
    w_res = stringobject.str_upper__String(space, w_str)
    return String2Bytearray(space, w_res)

def str_lower__Bytearray(space, w_bytearray):
    w_str = str__Bytearray(space, w_bytearray)
    w_res = stringobject.str_lower__String(space, w_str)
    return String2Bytearray(space, w_res)

def str_title__Bytearray(space, w_bytearray):
    w_str = str__Bytearray(space, w_bytearray)
    w_res = stringobject.str_title__String(space, w_str)
    return String2Bytearray(space, w_res)

def str_swapcase__Bytearray(space, w_bytearray):
    w_str = str__Bytearray(space, w_bytearray)
    w_res = stringobject.str_swapcase__String(space, w_str)
    return String2Bytearray(space, w_res)

def str_capitalize__Bytearray(space, w_bytearray):
    w_str = str__Bytearray(space, w_bytearray)
    w_res = stringobject.str_capitalize__String(space, w_str)
    return String2Bytearray(space, w_res)

def str_ljust__Bytearray_ANY_ANY(space, w_bytearray, w_width, w_fillchar):
    w_str = str__Bytearray(space, w_bytearray)
    w_res = stringobject.str_ljust__String_ANY_ANY(space, w_str, w_width,
                                                   w_fillchar)
    return String2Bytearray(space, w_res)

def str_rjust__Bytearray_ANY_ANY(space, w_bytearray, w_width, w_fillchar):
    w_str = str__Bytearray(space, w_bytearray)
    w_res = stringobject.str_rjust__String_ANY_ANY(space, w_str, w_width,
                                                   w_fillchar)
    return String2Bytearray(space, w_res)

def str_center__Bytearray_ANY_ANY(space, w_bytearray, w_width, w_fillchar):
    w_str = str__Bytearray(space, w_bytearray)
    w_res = stringobject.str_center__String_ANY_ANY(space, w_str, w_width,
                                                    w_fillchar)
    return String2Bytearray(space, w_res)

def str_zfill__Bytearray_ANY(space, w_bytearray, w_width):
    w_str = str__Bytearray(space, w_bytearray)
    w_res = stringobject.str_zfill__String_ANY(space, w_str, w_width)
    return String2Bytearray(space, w_res)

def str_expandtabs__Bytearray_ANY(space, w_bytearray, w_tabsize):
    w_str = str__Bytearray(space, w_bytearray)
    w_res = stringobject.str_expandtabs__String_ANY(space, w_str, w_tabsize)
    return String2Bytearray(space, w_res)

def str_splitlines__Bytearray_ANY(space, w_bytearray, w_keepends):
    w_str = str__Bytearray(space, w_bytearray)
    w_result = stringobject.str_splitlines__String_ANY(space, w_str, w_keepends)
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
    w_tuple = stringobject.str_partition__String_String(space, w_str, w_sub)
    w_a, w_b, w_c = space.fixedview(w_tuple, 3)
    return space.newtuple([
        String2Bytearray(space, w_a),
        String2Bytearray(space, w_b),
        String2Bytearray(space, w_c)])

def str_rpartition__Bytearray_ANY(space, w_bytearray, w_sub):
    w_str = str__Bytearray(space, w_bytearray)
    w_sub = space.wrap(space.bufferstr_new_w(w_sub))
    w_tuple = stringobject.str_rpartition__String_String(space, w_str, w_sub)
    w_a, w_b, w_c = space.fixedview(w_tuple, 3)
    return space.newtuple([
        String2Bytearray(space, w_a),
        String2Bytearray(space, w_b),
        String2Bytearray(space, w_c)])

# __________________________________________________________
# Mutability methods

def list_append__Bytearray_ANY(space, w_bytearray, w_item):
    from pypy.objspace.std.bytearraytype import getbytevalue
    w_bytearray.data.append(getbytevalue(space, w_item))

def list_extend__Bytearray_Bytearray(space, w_bytearray, w_other):
    w_bytearray.data += w_other.data

def list_extend__Bytearray_ANY(space, w_bytearray, w_other):
    w_bytearray.data += makebytearraydata_w(space, w_other)

def inplace_add__Bytearray_Bytearray(space, w_bytearray1, w_bytearray2):
    list_extend__Bytearray_Bytearray(space, w_bytearray1, w_bytearray2)
    return w_bytearray1

def inplace_add__Bytearray_ANY(space, w_bytearray1, w_iterable2):
    w_bytearray1.data += space.bufferstr_new_w(w_iterable2)
    return w_bytearray1

def setitem__Bytearray_ANY_ANY(space, w_bytearray, w_index, w_item):
    from pypy.objspace.std.bytearraytype import getbytevalue
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
    idx = get_list_index(space, w_idx)
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
        assert slicelength >= 0
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
        elif start >= 0:
            del items[start:start+delta]
        else:
            assert delta==0   # start<0 is only possible with slicelength==0
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
    # note: mostly copied from stringobject._strip
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

from pypy.objspace.std import bytearraytype
register_all(vars(), bytearraytype)
