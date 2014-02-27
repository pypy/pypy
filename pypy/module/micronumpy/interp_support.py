from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import unwrap_spec, WrappedDefault
from rpython.rtyper.lltypesystem import lltype, rffi
from pypy.module.micronumpy import descriptor, loop
from rpython.rlib.rstring import strip_spaces
from rpython.rlib.rarithmetic import maxint
from pypy.module.micronumpy.base import W_NDimArray

FLOAT_SIZE = rffi.sizeof(lltype.Float)

def _fromstring_text(space, s, count, sep, length, dtype):
    sep_stripped = strip_spaces(sep)
    skip_bad_vals = len(sep_stripped) == 0

    items = []
    num_items = 0
    idx = 0

    while (num_items < count or count == -1) and idx < len(s):
        nextidx = s.find(sep, idx)
        if nextidx < 0:
            nextidx = length
        piece = strip_spaces(s[idx:nextidx])
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
                    nextidx = length
            items.append(val)
            num_items += 1
        idx = nextidx + 1

    if count > num_items:
        raise OperationError(space.w_ValueError, space.wrap(
            "string is smaller than requested size"))

    a = W_NDimArray.from_shape(space, [num_items], dtype=dtype)
    ai = a.create_iter()
    for val in items:
        ai.setitem(val)
        ai.next()

    return space.wrap(a)

def _fromstring_bin(space, s, count, length, dtype):
    itemsize = dtype.elsize
    assert itemsize >= 0
    if count == -1:
        count = length / itemsize
    if length % itemsize != 0:
        raise oefmt(space.w_ValueError,
                    "string length %d not divisable by item size %d",
                    length, itemsize)
    if count * itemsize > length:
        raise OperationError(space.w_ValueError, space.wrap(
            "string is smaller than requested size"))

    a = W_NDimArray.from_shape(space, [count], dtype=dtype)
    loop.fromstring_loop(space, a, dtype, itemsize, s)
    return space.wrap(a)

@unwrap_spec(s=str, count=int, sep=str, w_dtype=WrappedDefault(None))
def fromstring(space, s, w_dtype=None, count=-1, sep=''):
    dtype = space.interp_w(descriptor.W_Dtype,
        space.call_function(space.gettypefor(descriptor.W_Dtype), w_dtype)
    )
    length = len(s)
    if sep == '':
        return _fromstring_bin(space, s, count, length, dtype)
    else:
        return _fromstring_text(space, s, count, sep, length, dtype)

def unwrap_axis_arg(space, shapelen, w_axis):
    if space.is_none(w_axis):
        axis = maxint
    else:
        axis = space.int_w(w_axis)
        if axis < -shapelen or axis >= shapelen:
            raise oefmt(space.w_ValueError,
                        "axis entry %d is out of bounds [%d, %d)",
                        axis, -shapelen, shapelen)
        if axis < 0:
            axis += shapelen
    return axis
