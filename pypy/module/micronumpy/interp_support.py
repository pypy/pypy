from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import unwrap_spec
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.module.micronumpy import interp_dtype
from pypy.objspace.std.strutil import strip_spaces


FLOAT_SIZE = rffi.sizeof(lltype.Float)

def _fromstring_text(space, s, count, sep, length, dtype):
    from pypy.module.micronumpy.interp_numarray import W_NDimArray

    sep_stripped = strip_spaces(sep)
    skip_bad_vals = True if len(sep_stripped) == 0 else False

    A = []
    num_items = 0
    ptr = 0
    
    while (num_items < count or count == -1) and ptr < len(s):
        nextptr = s.find(sep, ptr)
        if nextptr < 0:
            nextptr = length
        piece = strip_spaces(s[ptr:nextptr])
        if len(piece) > 0 or not skip_bad_vals:
            if len(piece) == 0 and not skip_bad_vals:
                val = dtype.itemtype.default_fromstring(space)
            else:
                try:
                    val = dtype.coerce(space, space.wrap(piece))
                except OperationError, e:
                    if not e.match(space, space.w_ValueError):
                        raise
                    gotit = False
                    while not gotit and len(piece) > 0:
                        piece = piece[:-1]
                        try:
                            val = dtype.coerce(space, space.wrap(piece))
                            gotit = True
                        except OperationError, e:
                            if not e.match(space, space.w_ValueError):
                                raise
                    if not gotit:
                        val = dtype.itemtype.default_fromstring(space)
                    nextptr = length
            A.append(val)
            num_items += 1
        ptr = nextptr + 1
    
    if count > num_items:
        raise OperationError(space.w_ValueError, space.wrap(
            "string is smaller than requested size"))

    a = W_NDimArray(num_items, [num_items], dtype=dtype)
    for i, val in enumerate(A):
        a.dtype.setitem(a.storage, i, val)
    
    return space.wrap(a)

def _fromstring_bin(space, s, count, length, dtype):
    from pypy.module.micronumpy.interp_numarray import W_NDimArray
    
    itemsize = dtype.itemtype.get_element_size()
    if count == -1:
        count = length / itemsize
    if length % itemsize != 0:
        raise OperationError(space.w_ValueError, space.wrap(
            "string length %d not divisable by item size %d" % (length, itemsize)))
    if count * itemsize > length:
        raise OperationError(space.w_ValueError, space.wrap(
            "string is smaller than requested size"))
        
    a = W_NDimArray(count, [count], dtype=dtype)
    for i in range(count):
        val = dtype.itemtype.runpack_str(s[i*itemsize:i*itemsize + itemsize])
        a.dtype.setitem(a.storage, i, val)
        
    return space.wrap(a)

@unwrap_spec(s=str, count=int, sep=str)
def fromstring(space, s, w_dtype=None, count=-1, sep=''):
    dtype = space.interp_w(interp_dtype.W_Dtype,
        space.call_function(space.gettypefor(interp_dtype.W_Dtype), w_dtype)
    )
    length = len(s)
    if sep == '':
        return _fromstring_bin(space, s, count, length, dtype)
    else:
        return _fromstring_text(space, s, count, sep, length, dtype)
