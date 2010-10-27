from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.objspace.std.model import registerimplementation, W_Object
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.inttype import wrapint
from pypy.objspace.std.multimethod import FailedToImplement
from pypy.rlib.rarithmetic import intmask
from pypy.rlib.rstring import StringBuilder
from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.stringobject import W_StringObject
from pypy.objspace.std.unicodeobject import W_UnicodeObject
from pypy.objspace.std.sliceobject import W_SliceObject, normalize_simple_slice
from pypy.objspace.std import slicetype
from pypy.interpreter import gateway
from pypy.interpreter.buffer import RWBuffer

class W_BytearrayObject(W_Object):
    from pypy.objspace.std.bytearraytype import bytearray_typedef as typedef

    def __init__(w_self, data):
        w_self.data = list(data)

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%s)" % (w_self.__class__.__name__, ''.join(w_self.data))

    def unwrap(w_bytearray, space):
        return bytearray(w_self.data)

registerimplementation(W_BytearrayObject)


def len__Bytearray(space, w_bytearray):
    result = len(w_bytearray.data)
    return wrapint(space, result)

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

def getslice__Bytearray_ANY_ANY(space, w_bytearray, w_start, w_stop):
    length = len(w_bytearray.data)
    start, stop = normalize_simple_slice(space, length, w_start, w_stop)
    return W_BytearrayObject(w_bytearray.data[start:stop])

def contains__Bytearray_Int(space, w_bytearray, w_char):
    char = w_char.intval
    if not 0 <= char < 256:
        raise OperationError(space.w_ValueError,
                             space.wrap("byte must be in range(0, 256)"))
    for c in w_bytearray.data:
        if ord(c) == char:
            return space.w_True
    return space.w_False

def add__Bytearray_Bytearray(space, w_bytearray1, w_bytearray2):
    data1 = w_bytearray1.data
    data2 = w_bytearray2.data
    return W_BytearrayObject(data1 + data2)

def mul_bytearray_times(space, w_bytearray, w_times):
    try:
        times = space.getindex_w(w_times, space.w_OverflowError)
    except OperationError, e:
        if e.match(space, space.w_TypeError):
            raise FailedToImplement
        raise
    if times == 1 and space.type(w_bytearray) == space.w_bytearray:
        return w_bytearray
    data = w_bytearray.data
    return W_BytearrayObject(data * times)

def mul__Bytearray_ANY(space, w_bytearray, w_times):
    return mul_bytearray_times(space, w_bytearray, w_times)

def mul__ANY_Bytearray(space, w_times, w_bytearray):
    return mul_bytearray_times(space, w_bytearray, w_times)

def eq__Bytearray_Bytearray(space, w_bytearray1, w_bytearray2):
    data1 = w_bytearray1.data
    data2 = w_bytearray2.data
    if len(data1) != len(data2):
        return space.w_False
    for i in range(len(data1)):
        if data1[i] != data2[i]:
            return space.w_False
    return space.w_True

# bytearray-to-string delegation
def delegate_Bytearray2String(space, w_bytearray):
    return str__Bytearray(space, w_bytearray)

def String2Bytearray(space, w_str):
    data = [c for c in space.str_w(w_str)]
    return W_BytearrayObject(data)

def eq__Bytearray_String(space, w_bytearray, w_other):
    return space.eq(delegate_Bytearray2String(space, w_bytearray), w_other)

def eq__Bytearray_Unicode(space, w_bytearray, w_other):
    return space.w_False

def eq__Unicode_Bytearray(space, w_other, w_bytearray):
    return space.w_False

def ne__Bytearray_String(space, w_bytearray, w_other):
    return space.ne(delegate_Bytearray2String(space, w_bytearray), w_other)

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
    return W_StringObject(''.join(w_bytearray.data))

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

def str_index__Bytearray_Int_ANY_ANY(space, w_bytearray, w_char, w_start, w_stop):
    char = w_char.intval
    start, stop, length = _convert_idx_params(space, w_bytearray, w_start, w_stop)
    for i in range(start, min(stop, length)):
        c = w_bytearray.data[i]
        if ord(c) == char:
            return space.wrap(i)
    raise OperationError(space.w_ValueError,
                         space.wrap("bytearray.index(x): x not in bytearray"))

def str_join__Bytearray_ANY(space, w_self, w_list):
    list_w = space.listview(w_list)
    if not list_w:
        return W_BytearrayObject([])
    data = w_self.data
    reslen = 0
    for i in range(len(list_w)):
        w_s = list_w[i]
        if not (space.is_true(space.isinstance(w_s, space.w_str)) or
                space.is_true(space.isinstance(w_s, space.w_bytearray))):
            raise operationerrfmt(
                space.w_TypeError,
                "sequence item %d: expected string, %s "
                "found", i, space.type(w_s).getname(space, '?'))
        reslen += len(space.str_w(w_s))
    newdata = []
    for i in range(len(list_w)):
        if data and i != 0:
            newdata.extend(data)
        newdata.extend([c for c in space.str_w(list_w[i])])
    return W_BytearrayObject(newdata)

# These methods could just delegate to the string implementation,
# but they have to return a bytearray.
def str_replace__Bytearray_ANY_ANY_ANY(space, w_bytearray, w_str1, w_str2, w_max):
    w_str = delegate_Bytearray2String(space, w_bytearray)
    w_res = space.call_method(w_str, "replace", w_str1, w_str2, w_max)
    return String2Bytearray(space, w_res)

def str_upper__Bytearray(space, w_bytearray):
    w_str = delegate_Bytearray2String(space, w_bytearray)
    w_res = space.call_method(w_str, "upper")
    return String2Bytearray(space, w_res)

def str_lower__Bytearray(space, w_bytearray):
    w_str = delegate_Bytearray2String(space, w_bytearray)
    w_res = space.call_method(w_str, "lower")
    return String2Bytearray(space, w_res)

def str_title__Bytearray(space, w_bytearray):
    w_str = delegate_Bytearray2String(space, w_bytearray)
    w_res = space.call_method(w_str, "title")
    return String2Bytearray(space, w_res)

def str_swapcase__Bytearray(space, w_bytearray):
    w_str = delegate_Bytearray2String(space, w_bytearray)
    w_res = space.call_method(w_str, "swapcase")
    return String2Bytearray(space, w_res)

def str_capitalize__Bytearray(space, w_bytearray):
    w_str = delegate_Bytearray2String(space, w_bytearray)
    w_res = space.call_method(w_str, "capitalize")
    return String2Bytearray(space, w_res)

def str_lstrip__Bytearray_ANY(space, w_bytearray, w_chars):
    w_str = delegate_Bytearray2String(space, w_bytearray)
    w_res = space.call_method(w_str, "lstrip", w_chars)
    return String2Bytearray(space, w_res)

def str_rstrip__Bytearray_ANY(space, w_bytearray, w_chars):
    w_str = delegate_Bytearray2String(space, w_bytearray)
    w_res = space.call_method(w_str, "rstrip", w_chars)
    return String2Bytearray(space, w_res)

def str_strip__Bytearray_ANY(space, w_bytearray, w_chars):
    w_str = delegate_Bytearray2String(space, w_bytearray)
    w_res = space.call_method(w_str, "strip", w_chars)
    return String2Bytearray(space, w_res)

def str_ljust__Bytearray_ANY_ANY(space, w_bytearray, w_width, w_fillchar):
    w_str = delegate_Bytearray2String(space, w_bytearray)
    w_res = space.call_method(w_str, "ljust", w_width, w_fillchar)
    return String2Bytearray(space, w_res)

def str_rjust__Bytearray_ANY_ANY(space, w_bytearray, w_width, w_fillchar):
    w_str = delegate_Bytearray2String(space, w_bytearray)
    w_res = space.call_method(w_str, "rjust", w_width, w_fillchar)
    return String2Bytearray(space, w_res)

def str_center__Bytearray_ANY_ANY(space, w_bytearray, w_width, w_fillchar):
    w_str = delegate_Bytearray2String(space, w_bytearray)
    w_res = space.call_method(w_str, "center", w_width, w_fillchar)
    return String2Bytearray(space, w_res)

def str_zfill__Bytearray_ANY(space, w_bytearray, w_width):
    w_str = delegate_Bytearray2String(space, w_bytearray)
    w_res = space.call_method(w_str, "zfill", w_width)
    return String2Bytearray(space, w_res)

def str_expandtabs__Bytearray_ANY(space, w_bytearray, w_tabsize):
    w_str = delegate_Bytearray2String(space, w_bytearray)
    w_res = space.call_method(w_str, "expandtabs", w_tabsize)
    return String2Bytearray(space, w_res)

def str_split__Bytearray_ANY_ANY(space, w_bytearray, w_by, w_maxsplit=-1):
    w_str = delegate_Bytearray2String(space, w_bytearray)
    w_list = space.call_method(w_str, "split", w_by, w_maxsplit)
    list_w = space.listview(w_list)
    for i in range(len(list_w)):
        list_w[i] = String2Bytearray(space, list_w[i])
    return w_list

def str_rsplit__Bytearray_ANY_ANY(space, w_bytearray, w_by, w_maxsplit=-1):
    w_str = delegate_Bytearray2String(space, w_bytearray)
    w_list = space.call_method(w_str, "rsplit", w_by, w_maxsplit)
    list_w = space.listview(w_list)
    for i in range(len(list_w)):
        list_w[i] = String2Bytearray(space, list_w[i])
    return w_list

def str_partition__Bytearray_ANY(space, w_bytearray, w_sub):
    w_str = delegate_Bytearray2String(space, w_bytearray)
    w_tuple = space.call_method(w_str, "partition", w_sub)
    w_a, w_b, w_c = space.fixedview(w_tuple, 3)
    return space.newtuple([
        String2Bytearray(space, w_a),
        String2Bytearray(space, w_b),
        String2Bytearray(space, w_c)])

def str_rpartition__Bytearray_ANY(space, w_bytearray, w_sub):
    w_str = delegate_Bytearray2String(space, w_bytearray)
    w_tuple = space.call_method(w_str, "rpartition", w_sub)
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
    w_bytearray.data += [c for c in space.str_w(w_other)]

def inplace_add__Bytearray_Bytearray(space, w_bytearray1, w_bytearray2):
    list_extend__Bytearray_Bytearray(space, w_bytearray1, w_bytearray2)
    return w_bytearray1

def inplace_add__Bytearray_ANY(space, w_bytearray1, w_iterable2):
    list_extend__Bytearray_ANY(space, w_bytearray1, w_iterable2)
    return w_bytearray1

def delslice__Bytearray_ANY_ANY(space, w_bytearray, w_start, w_stop):
    length = len(w_bytearray.data)
    start, stop = normalize_simple_slice(space, length, w_start, w_stop)
    if start == stop:
        return
    del w_bytearray.data[start:stop]

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
    if step != 1:
        raise OperationError(space.w_NotImplementedError,
                             space.wrap("fixme: only step=1 for the moment"))
    _setitem_helper(w_bytearray, start, stop, slicelength,
                    space.str_w(w_other))

def _setitem_helper(w_bytearray, start, stop, slicelength, data):
    assert start >= 0
    assert stop >= 0
    step = 1
    len2 = len(data)
    delta = slicelength - len2
    if delta < 0:
        delta = -delta
        newsize = len(w_bytearray.data) + delta
        w_bytearray.data += ['\0'] * delta
        lim = start + len2
        i = newsize - 1
        while i >= lim:
            w_bytearray.data[i] = w_bytearray.data[i-delta]
            i -= 1
    elif start >= 0:
        del w_bytearray.data[start:start+delta]
    else:
        assert delta == 0
    for i in range(len2):
        w_bytearray.data[start] = data[i]
        start += step

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
