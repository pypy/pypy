from pypy.interpreter.error import OperationError
from pypy.objspace.std.model import registerimplementation, W_Object
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.inttype import wrapint
from pypy.objspace.std.multimethod import FailedToImplement
from pypy.rlib.rarithmetic import intmask
from pypy.rlib.rstring import StringBuilder
from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.sliceobject import W_SliceObject, normalize_simple_slice
from pypy.objspace.std import slicetype
from pypy.interpreter import gateway

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

def bytearray_count__Bytearray_Int(space, w_bytearray, w_char):
    char = w_char.intval
    count = 0
    for c in w_bytearray.data:
        if ord(c) == char:
            count += 1
    return space.wrap(count)

def bytearray_index__Bytearray_Int_ANY_ANY(space, w_bytearray, w_char, w_start, w_stop):
    char = w_char.intval
    start = slicetype._Eval_SliceIndex(space, w_start)
    stop = slicetype._Eval_SliceIndex(space, w_stop)
    length = len(w_bytearray.data)
    if start < 0:
        start += length
        if start < 0:
            start = 0
    if stop < 0:
        stop += length
        if stop < 0:
            stop = 0
    for i in range(start, min(stop, length)):
        c = w_bytearray.data[i]
        if ord(c) == char:
            return space.wrap(i)
    raise OperationError(space.w_ValueError,
                         space.wrap("bytearray.index(x): x not in bytearray"))

from pypy.objspace.std import bytearraytype
register_all(vars(), bytearraytype)
