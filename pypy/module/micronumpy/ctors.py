from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import unwrap_spec, WrappedDefault
from rpython.rlib.rstring import strip_spaces
from rpython.rtyper.lltypesystem import lltype, rffi
from pypy.module.micronumpy import descriptor, loop, ufuncs
from pypy.module.micronumpy.base import W_NDimArray, convert_to_array
from pypy.module.micronumpy.converters import shape_converter
from pypy.module.micronumpy.strides import find_shape_and_elems


def build_scalar(space, w_dtype, w_state):
    if not isinstance(w_dtype, descriptor.W_Dtype):
        raise oefmt(space.w_TypeError,
                    "argument 1 must be numpy.dtype, not %T", w_dtype)
    if w_dtype.elsize == 0:
        raise oefmt(space.w_ValueError, "itemsize cannot be zero")
    if not space.isinstance_w(w_state, space.w_str):
        raise oefmt(space.w_TypeError, "initializing object must be a string")
    if space.len_w(w_state) != w_dtype.elsize:
        raise oefmt(space.w_ValueError, "initialization string is too small")
    state = rffi.str2charp(space.str_w(w_state))
    box = w_dtype.itemtype.box_raw_data(state)
    lltype.free(state, flavor="raw")
    return box


@unwrap_spec(ndmin=int, copy=bool, subok=bool)
def array(space, w_object, w_dtype=None, copy=True, w_order=None, subok=False,
          ndmin=0):
    # for anything that isn't already an array, try __array__ method first
    if not isinstance(w_object, W_NDimArray):
        w___array__ = space.lookup(w_object, "__array__")
        if w___array__ is not None:
            if space.is_none(w_dtype):
                w_dtype = space.w_None
            w_array = space.get_and_call_function(w___array__, w_object, w_dtype)
            if isinstance(w_array, W_NDimArray):
                # feed w_array back into array() for other properties
                return array(space, w_array, w_dtype, False, w_order, subok, ndmin)
            else:
                raise oefmt(space.w_ValueError,
                            "object __array__ method not producing an array")

    dtype = descriptor.decode_w_dtype(space, w_dtype)

    if space.is_none(w_order):
        order = 'C'
    else:
        order = space.str_w(w_order)
        if order != 'C':  # or order != 'F':
            raise oefmt(space.w_ValueError, "Unknown order: %s", order)

    # arrays with correct dtype
    if isinstance(w_object, W_NDimArray) and \
            (space.is_none(w_dtype) or w_object.get_dtype() is dtype):
        shape = w_object.get_shape()
        if copy:
            w_ret = w_object.descr_copy(space)
        else:
            if ndmin <= len(shape):
                return w_object
            new_impl = w_object.implementation.set_shape(space, w_object, shape)
            w_ret = W_NDimArray(new_impl)
        if ndmin > len(shape):
            shape = [1] * (ndmin - len(shape)) + shape
            w_ret.implementation = w_ret.implementation.set_shape(space,
                                                                  w_ret, shape)
        return w_ret

    # not an array or incorrect dtype
    shape, elems_w = find_shape_and_elems(space, w_object, dtype)
    if dtype is None or (dtype.is_str_or_unicode() and dtype.elsize < 1):
        for w_elem in elems_w:
            if isinstance(w_elem, W_NDimArray) and w_elem.is_scalar():
                w_elem = w_elem.get_scalar_value()
            dtype = ufuncs.find_dtype_for_scalar(space, w_elem, dtype)
        if dtype is None:
            dtype = descriptor.get_dtype_cache(space).w_float64dtype
        elif dtype.is_str_or_unicode() and dtype.elsize < 1:
            # promote S0 -> S1, U0 -> U1
            dtype = descriptor.variable_dtype(space, dtype.char + '1')

    if ndmin > len(shape):
        shape = [1] * (ndmin - len(shape)) + shape
    w_arr = W_NDimArray.from_shape(space, shape, dtype, order=order)
    arr_iter = w_arr.create_iter()
    for w_elem in elems_w:
        arr_iter.setitem(dtype.coerce(space, w_elem))
        arr_iter.next()
    return w_arr


def zeros(space, w_shape, w_dtype=None, w_order=None):
    dtype = space.interp_w(descriptor.W_Dtype,
        space.call_function(space.gettypefor(descriptor.W_Dtype), w_dtype))
    if dtype.is_str_or_unicode() and dtype.elsize < 1:
        dtype = descriptor.variable_dtype(space, dtype.char + '1')
    shape = shape_converter(space, w_shape, dtype)
    return W_NDimArray.from_shape(space, shape, dtype=dtype)


@unwrap_spec(subok=bool)
def empty_like(space, w_a, w_dtype=None, w_order=None, subok=True):
    w_a = convert_to_array(space, w_a)
    if w_dtype is None:
        dtype = w_a.get_dtype()
    else:
        dtype = space.interp_w(descriptor.W_Dtype,
            space.call_function(space.gettypefor(descriptor.W_Dtype), w_dtype))
        if dtype.is_str_or_unicode() and dtype.elsize < 1:
            dtype = descriptor.variable_dtype(space, dtype.char + '1')
    return W_NDimArray.from_shape(space, w_a.get_shape(), dtype=dtype,
                                  w_instance=w_a if subok else None)


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
        space.call_function(space.gettypefor(descriptor.W_Dtype), w_dtype))
    length = len(s)
    if sep == '':
        return _fromstring_bin(space, s, count, length, dtype)
    else:
        return _fromstring_text(space, s, count, sep, length, dtype)
