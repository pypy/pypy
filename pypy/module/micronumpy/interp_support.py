from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import unwrap_spec
from pypy.module.micronumpy.interp_dtype import get_dtype_cache
from pypy.module.micronumpy import interp_dtype
from pypy.rpython.lltypesystem import lltype, rffi


FLOAT_SIZE = rffi.sizeof(lltype.Float)

@unwrap_spec(s=str, count=int, sep=str)
def fromstring(space, s, w_dtype=None, count=-1, sep=''):
    from pypy.module.micronumpy.interp_numarray import W_NDimArray
    
    dtype = space.interp_w(interp_dtype.W_Dtype,
        space.call_function(space.gettypefor(interp_dtype.W_Dtype), w_dtype)
    )
    itemsize = abs(space.int_w(dtype.descr_get_itemsize(space)))
    length = len(s)

    A = []
    num = 0
    ptr = 0
    
    while (num < count or count == -1) and ptr < len(s):
        if sep == '':
            if length - ptr < itemsize:
                raise OperationError(space.w_ValueError, space.wrap(
                    "string length %d not divisable by item size %d" % (length, itemsize)))
            val = dtype.itemtype.runpack_str(s[ptr:ptr+itemsize])
            ptr += itemsize
        else:
            nextptr = s.find(sep, ptr)
            if nextptr < 0:
                nextptr = length
            val = dtype.coerce(space, space.wrap(s[ptr:nextptr]))
            ptr = nextptr + 1
        
        num += 1
        A.append(val)
    
    if count > num:
        raise OperationError(space.w_ValueError, space.wrap(
            "string is smaller than requested size"))
    
    a = W_NDimArray(num, [num], dtype=dtype)
    for i, val in enumerate(A):
        a.dtype.setitem(a.storage, i, val)
        
    return space.wrap(a)
