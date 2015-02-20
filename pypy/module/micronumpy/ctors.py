from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import unwrap_spec, WrappedDefault
from rpython.rlib.buffer import SubBuffer
from rpython.rlib.rstring import strip_spaces
from rpython.rtyper.lltypesystem import lltype, rffi
from pypy.module.micronumpy import descriptor, loop, support
from pypy.module.micronumpy.base import (
    W_NDimArray, convert_to_array, W_NumpyObject)
from pypy.module.micronumpy.converters import shape_converter


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


def try_array_method(space, w_object, w_dtype=None):
    w___array__ = space.lookup(w_object, "__array__")
    if w___array__ is None:
        return None
    if w_dtype is None:
        w_dtype = space.w_None
    w_array = space.get_and_call_function(w___array__, w_object, w_dtype)
    if isinstance(w_array, W_NDimArray):
        return w_array
    else:
        raise oefmt(space.w_ValueError,
                    "object __array__ method not producing an array")


@unwrap_spec(ndmin=int, copy=bool, subok=bool)
def array(space, w_object, w_dtype=None, copy=True, w_order=None, subok=False,
          ndmin=0):
    w_res = _array(space, w_object, w_dtype, copy, w_order, subok)
    shape = w_res.get_shape()
    if len(shape) < ndmin:
        shape = [1] * (ndmin - len(shape)) + shape
        impl = w_res.implementation.set_shape(space, w_res, shape)
        if w_res is w_object:
            return W_NDimArray(impl)
        else:
            w_res.implementation = impl
    return w_res

def _array(space, w_object, w_dtype=None, copy=True, w_order=None, subok=False):
    from pypy.module.micronumpy import strides

    # for anything that isn't already an array, try __array__ method first
    if not isinstance(w_object, W_NDimArray):
        w_array = try_array_method(space, w_object, w_dtype)
        if w_array is not None:
            # continue with w_array, but do further operations in place
            w_object = w_array
            copy = False

    dtype = descriptor.decode_w_dtype(space, w_dtype)

    if space.is_none(w_order):
        order = 'C'
    else:
        order = space.str_w(w_order)
        if order == 'K':
            order = 'C'
        if order != 'C':  # or order != 'F':
            raise oefmt(space.w_ValueError, "Unknown order: %s", order)

    if isinstance(w_object, W_NDimArray):
        if (dtype is None or w_object.get_dtype() is dtype):
            if copy and (subok or type(w_object) is W_NDimArray):
                return w_object.descr_copy(space, w_order)
            elif not copy and (subok or type(w_object) is W_NDimArray):
                return w_object
        # we have a ndarray, but need to copy or change dtype or create W_NDimArray
        if dtype is None:
            dtype = w_object.get_dtype()
        if dtype != w_object.get_dtype():
            # silently reject the copy value
            copy = True
        if copy:
            shape = w_object.get_shape()
            _elems_w = w_object.reshape(space, space.wrap(-1))
            elems_w = [None] * w_object.get_size()
            for i in range(len(elems_w)):
                elems_w[i] = _elems_w.descr_getitem(space, space.wrap(i))
        elif subok:
            raise oefmt(space.w_NotImplementedError, 
                "array(...copy=False, subok=True) not implemented yet")
        else:
            sz = support.product(w_object.get_shape()) * dtype.elsize
            return W_NDimArray.from_shape_and_storage(space,
                w_object.get_shape(),w_object.implementation.storage,
                dtype, storage_bytes=sz, w_base=w_object)
    else:
        # not an array
        shape, elems_w = strides.find_shape_and_elems(space, w_object, dtype)
    if dtype is None or (dtype.is_str_or_unicode() and dtype.elsize < 1):
        dtype = strides.find_dtype_for_seq(space, elems_w, dtype)
        if dtype is None:
            dtype = descriptor.get_dtype_cache(space).w_float64dtype
        elif dtype.is_str_or_unicode() and dtype.elsize < 1:
            # promote S0 -> S1, U0 -> U1
            dtype = descriptor.variable_dtype(space, dtype.char + '1')

    w_arr = W_NDimArray.from_shape(space, shape, dtype, order=order)
    if len(elems_w) == 1:
        w_arr.set_scalar_value(dtype.coerce(space, elems_w[0]))
    else:
        loop.assign(space, w_arr, elems_w)
    return w_arr


def numpify(space, w_object):
    """Convert the object to a W_NumpyObject"""
    # XXX: code duplication with _array()
    from pypy.module.micronumpy import strides
    if isinstance(w_object, W_NumpyObject):
        return w_object
    # for anything that isn't already an array, try __array__ method first
    w_array = try_array_method(space, w_object)
    if w_array is not None:
        return w_array

    shape, elems_w = strides.find_shape_and_elems(space, w_object, None)
    dtype = strides.find_dtype_for_seq(space, elems_w, None)
    if dtype is None:
        dtype = descriptor.get_dtype_cache(space).w_float64dtype
    elif dtype.is_str_or_unicode() and dtype.elsize < 1:
        # promote S0 -> S1, U0 -> U1
        dtype = descriptor.variable_dtype(space, dtype.char + '1')

    if len(elems_w) == 1:
        return dtype.coerce(space, elems_w[0])
    else:
        w_arr = W_NDimArray.from_shape(space, shape, dtype)
        loop.assign(space, w_arr, elems_w)
        return w_arr


def _zeros_or_empty(space, w_shape, w_dtype, w_order, zero):
    dtype = space.interp_w(descriptor.W_Dtype,
        space.call_function(space.gettypefor(descriptor.W_Dtype), w_dtype))
    if dtype.is_str_or_unicode() and dtype.elsize < 1:
        dtype = descriptor.variable_dtype(space, dtype.char + '1')
    shape = shape_converter(space, w_shape, dtype)
    for dim in shape:
        if dim < 0:
            raise OperationError(space.w_ValueError, space.wrap(
                "negative dimensions are not allowed"))
    try:
        support.product(shape)
    except OverflowError:
        raise OperationError(space.w_ValueError, space.wrap(
            "array is too big."))
    return W_NDimArray.from_shape(space, shape, dtype=dtype, zero=zero)

def empty(space, w_shape, w_dtype=None, w_order=None):
    return _zeros_or_empty(space, w_shape, w_dtype, w_order, zero=False)

def zeros(space, w_shape, w_dtype=None, w_order=None):
    return _zeros_or_empty(space, w_shape, w_dtype, w_order, zero=True)


@unwrap_spec(subok=bool)
def empty_like(space, w_a, w_dtype=None, w_order=None, subok=True):
    w_a = convert_to_array(space, w_a)
    if space.is_none(w_dtype):
        dtype = w_a.get_dtype()
    else:
        dtype = space.interp_w(descriptor.W_Dtype,
            space.call_function(space.gettypefor(descriptor.W_Dtype), w_dtype))
        if dtype.is_str_or_unicode() and dtype.elsize < 1:
            dtype = descriptor.variable_dtype(space, dtype.char + '1')
    return W_NDimArray.from_shape(space, w_a.get_shape(), dtype=dtype,
                                  w_instance=w_a if subok else None,
                                  zero=False)


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
    ai, state = a.create_iter()
    for val in items:
        ai.setitem(state, val)
        state = ai.next(state)

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


def _getbuffer(space, w_buffer):
    try:
        return space.writebuf_w(w_buffer)
    except OperationError as e:
        if not e.match(space, space.w_TypeError):
            raise
        return space.readbuf_w(w_buffer)


@unwrap_spec(count=int, offset=int)
def frombuffer(space, w_buffer, w_dtype=None, count=-1, offset=0):
    dtype = space.interp_w(descriptor.W_Dtype,
        space.call_function(space.gettypefor(descriptor.W_Dtype), w_dtype))
    if dtype.elsize == 0:
        raise oefmt(space.w_ValueError, "itemsize cannot be zero in type")

    try:
        buf = _getbuffer(space, w_buffer)
    except OperationError as e:
        if not e.match(space, space.w_TypeError):
            raise
        w_buffer = space.getattr(w_buffer, space.wrap('__buffer__'))
        buf = _getbuffer(space, w_buffer)

    ts = buf.getlength()
    if offset < 0 or offset > ts:
        raise oefmt(space.w_ValueError,
                    "offset must be non-negative and no greater than "
                    "buffer length (%d)", ts)

    s = ts - offset
    if offset:
        buf = SubBuffer(buf, offset, s)

    n = count
    itemsize = dtype.elsize
    assert itemsize > 0
    if n < 0:
        if s % itemsize != 0:
            raise oefmt(space.w_ValueError,
                        "buffer size must be a multiple of element size")
        n = s / itemsize
    else:
        if s < n * itemsize:
            raise oefmt(space.w_ValueError,
                        "buffer is smaller than requested size")

    try:
        storage = buf.get_raw_address()
    except ValueError:
        a = W_NDimArray.from_shape(space, [n], dtype=dtype)
        loop.fromstring_loop(space, a, dtype, itemsize, buf.as_str())
        return a
    else:
        writable = not buf.readonly
    return W_NDimArray.from_shape_and_storage(space, [n], storage, storage_bytes=s, 
                                dtype=dtype, w_base=w_buffer, writable=writable)
