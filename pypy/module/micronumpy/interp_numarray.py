
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import operationerrfmt, OperationError
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.module.micronumpy import interp_dtype, interp_ufuncs, support
from pypy.module.micronumpy.arrayimpl import create_implementation, create_slice
from pypy.module.micronumpy.strides import find_shape_and_elems,\
     get_shape_from_iterable
from pypy.module.micronumpy.interp_support import unwrap_axis_arg
from pypy.module.micronumpy.appbridge import get_appbridge_cache
from pypy.tool.sourcetools import func_with_new_name
from pypy.rlib import jit
from pypy.rlib.objectmodel import instantiate
from pypy.rlib.rstring import StringBuilder

def _find_shape(space, w_size):
    if space.isinstance_w(w_size, space.w_int):
        return [space.int_w(w_size)]
    shape = []
    for w_item in space.fixedview(w_size):
        shape.append(space.int_w(w_item))
    return shape

def scalar_w(space, dtype, w_object):
    arr = W_NDimArray([], dtype)
    arr.implementation.set_scalar_value(dtype.coerce(space, w_object))
    return arr

def slice_w(start, strides, backstrides, shape, parent):
    arr = instantiate(W_NDimArray)
    arr.implementation = create_slice(start, strides, backstrides, shape,
                                      parent)
    return arr

class W_NDimArray(Wrappable):
    def __init__(self, shape, dtype, buffer=0, offset=0, strides=None,
                 order='C'):
        if strides is not None or offset != 0 or buffer != 0:
            raise Exception("unsupported args")
        self.implementation = create_implementation(shape, dtype, order)

    @jit.unroll_safe
    def descr_get_shape(self, space):
        shape = self.get_shape()
        return space.newtuple([space.wrap(i) for i in shape])

    def get_shape(self):
        return self.implementation.get_shape()

    def descr_set_shape(self, space, w_new_shape):
        self.implementation = self.implementation.set_shape(
            _find_shape(space, w_new_shape))

    def get_dtype(self):
        return self.implementation.dtype

    def descr_get_dtype(self, space):
        return self.implementation.dtype

    def descr_get_ndim(self, space):
        return space.wrap(len(self.get_shape()))

    def descr_getitem(self, space, w_idx):
        if (isinstance(w_idx, W_NDimArray) and w_idx.get_shape() == self.get_shape() and
            w_idx.get_dtype().is_bool_type()):
            return self.getitem_filter(space, w_idx)
        try:
            return self.implementation.descr_getitem(space, w_idx)
        except OperationError:
            raise OperationError(space.w_IndexError, space.wrap("wrong index"))

    def descr_setitem(self, space, w_idx, w_value):
        if (isinstance(w_idx, W_NDimArray) and w_idx.shape == self.shape and
            w_idx.get_dtype().is_bool_type()):
            return self.setitem_filter(space, w_idx,
                                       support.convert_to_array(space, w_value))
        self.implementation.descr_setitem(space, w_idx, w_value)

    def descr_len(self, space):
        shape = self.get_shape()
        if len(shape):
            return space.wrap(shape[0])
        raise OperationError(space.w_TypeError, space.wrap(
            "len() of unsized object"))

    def descr_repr(self, space):
        #cache = get_appbridge_cache(space)
        #if cache.w_array_repr is None:
        return space.wrap(self.dump_data())
        #return space.call_function(cache.w_array_repr, self)

    def dump_data(self):
        i = self.create_iter(self.get_shape())
        first = True
        dtype = self.get_dtype()
        s = StringBuilder()
        s.append('array([')
        while not i.done():
            if first:
                first = False
            else:
                s.append(', ')
            s.append(dtype.itemtype.str_format(i.getitem()))
            i.next()
        s.append('])')
        return s.build()

    def create_iter(self, shape):
        return self.implementation.create_iter(shape)

    def is_scalar(self):
        return self.implementation.is_scalar()

    def fill(self, box):
        self.implementation.fill(box)

    def descr_get_size(self, space):
        return space.wrap(self.get_size())

    def get_size(self):
        return self.implementation.get_size()

    def get_scalar_value(self):
        return self.implementation.get_scalar_value()

    def descr_copy(self, space):
        arr = instantiate(W_NDimArray)
        arr.implementation = self.implementation.copy()
        return arr

    def descr_reshape(self, space, args_w):
        """reshape(...)
        a.reshape(shape)

        Returns an array containing the same data with a new shape.

        Refer to `numpypy.reshape` for full documentation.

        See Also
        --------
        numpypy.reshape : equivalent function
        """
        if len(args_w) == 1:
            w_shape = args_w[0]
        else:
            w_shape = space.newtuple(args_w)
        new_shape = get_shape_from_iterable(space, self.get_size(), w_shape)
        new_impl = self.implementation.reshape(space, new_shape)
        if new_impl is not None:
            self.implementation = new_impl
            return self
        else:
            # Create copy with contiguous data
            arr = self.descr_copy(space)
            arr.implementation = arr.implementation.reshape(space, new_shape)
        return arr

    def descr_get_transpose(self, space):
        arr = instantiate(W_NDimArray)
        arr.implementation = self.implementation.transpose()
        return arr

    # --------------------- binary operations ----------------------------

    def _binop_impl(ufunc_name):
        def impl(self, space, w_other, w_out=None):
            return getattr(interp_ufuncs.get(space), ufunc_name).call(space,
                                                        [self, w_other, w_out])
        return func_with_new_name(impl, "binop_%s_impl" % ufunc_name)

    descr_add = _binop_impl("add")
    descr_sub = _binop_impl("subtract")
    descr_mul = _binop_impl("multiply")
    descr_div = _binop_impl("divide")
    descr_truediv = _binop_impl("true_divide")
    descr_floordiv = _binop_impl("floor_divide")
    descr_mod = _binop_impl("mod")
    descr_pow = _binop_impl("power")
    descr_lshift = _binop_impl("left_shift")
    descr_rshift = _binop_impl("right_shift")
    descr_and = _binop_impl("bitwise_and")
    descr_or = _binop_impl("bitwise_or")
    descr_xor = _binop_impl("bitwise_xor")

    def descr_divmod(self, space, w_other):
        w_quotient = self.descr_div(space, w_other)
        w_remainder = self.descr_mod(space, w_other)
        return space.newtuple([w_quotient, w_remainder])

    descr_eq = _binop_impl("equal")
    descr_ne = _binop_impl("not_equal")
    descr_lt = _binop_impl("less")
    descr_le = _binop_impl("less_equal")
    descr_gt = _binop_impl("greater")
    descr_ge = _binop_impl("greater_equal")

    def _binop_right_impl(ufunc_name):
        def impl(self, space, w_other, w_out=None):
            w_other = scalar_w(space,
                interp_ufuncs.find_dtype_for_scalar(space, w_other,
                                                    self.get_dtype()),
                w_other
            )
            return getattr(interp_ufuncs.get(space), ufunc_name).call(space, [w_other, self, w_out])
        return func_with_new_name(impl, "binop_right_%s_impl" % ufunc_name)

    descr_radd = _binop_right_impl("add")

    # ----------------------- reduce -------------------------------

    def _reduce_ufunc_impl(ufunc_name, promote_to_largest=False):
        def impl(self, space, w_axis=None, w_out=None):
            if space.is_w(w_out, space.w_None) or not w_out:
                out = None
            elif not isinstance(w_out, W_NDimArray):
                raise OperationError(space.w_TypeError, space.wrap( 
                        'output must be an array'))
            else:
                out = w_out
            return getattr(interp_ufuncs.get(space), ufunc_name).reduce(space,
                                        self, True, promote_to_largest, w_axis,
                                                                   False, out)
        return func_with_new_name(impl, "reduce_%s_impl" % ufunc_name)

    descr_sum = _reduce_ufunc_impl("add")
    descr_sum_promote = _reduce_ufunc_impl("add", True)
    descr_prod = _reduce_ufunc_impl("multiply", True)
    descr_max = _reduce_ufunc_impl("maximum")
    descr_min = _reduce_ufunc_impl("minimum")
    descr_all = _reduce_ufunc_impl('logical_and')
    descr_any = _reduce_ufunc_impl('logical_or')

    def descr_mean(self, space, w_axis=None, w_out=None):
        if space.is_w(w_axis, space.w_None):
            w_denom = space.wrap(support.product(self.shape))
        else:
            axis = unwrap_axis_arg(space, len(self.shape), w_axis)
            w_denom = space.wrap(self.shape[axis])
        return space.div(self.descr_sum_promote(space, w_axis, w_out), w_denom)


@unwrap_spec(offset=int)
def descr_new_array(space, w_subtype, w_shape, w_dtype=None, w_buffer=None,
                    offset=0, w_strides=None, w_order=None):
    dtype = space.interp_w(interp_dtype.W_Dtype,
          space.call_function(space.gettypefor(interp_dtype.W_Dtype), w_dtype))
    shape = _find_shape(space, w_shape)
    return W_NDimArray(shape, dtype)

W_NDimArray.typedef = TypeDef(
    "ndarray",
    __new__ = interp2app(descr_new_array),

    __len__ = interp2app(W_NDimArray.descr_len),
    __getitem__ = interp2app(W_NDimArray.descr_getitem),
    __setitem__ = interp2app(W_NDimArray.descr_setitem),

    __repr__ = interp2app(W_NDimArray.descr_repr),

    __add__ = interp2app(W_NDimArray.descr_add),
    __mul__ = interp2app(W_NDimArray.descr_mul),
    __div__ = interp2app(W_NDimArray.descr_div),
    __truediv__ = interp2app(W_NDimArray.descr_truediv),
    __floordiv__ = interp2app(W_NDimArray.descr_floordiv),
    __mod__ = interp2app(W_NDimArray.descr_mod),
    __divmod__ = interp2app(W_NDimArray.descr_divmod),
    __pow__ = interp2app(W_NDimArray.descr_pow),
    __lshift__ = interp2app(W_NDimArray.descr_lshift),
    __rshift__ = interp2app(W_NDimArray.descr_rshift),
    __and__ = interp2app(W_NDimArray.descr_and),
    __or__ = interp2app(W_NDimArray.descr_or),
    __xor__ = interp2app(W_NDimArray.descr_xor),

    __radd__ = interp2app(W_NDimArray.descr_radd),

    __eq__ = interp2app(W_NDimArray.descr_eq),
    __ne__ = interp2app(W_NDimArray.descr_ne),
    __lt__ = interp2app(W_NDimArray.descr_lt),
    __le__ = interp2app(W_NDimArray.descr_le),
    __gt__ = interp2app(W_NDimArray.descr_gt),
    __ge__ = interp2app(W_NDimArray.descr_ge),

    dtype = GetSetProperty(W_NDimArray.descr_get_dtype),
    shape = GetSetProperty(W_NDimArray.descr_get_shape,
                           W_NDimArray.descr_set_shape),
    ndim = GetSetProperty(W_NDimArray.descr_get_ndim),
    size = GetSetProperty(W_NDimArray.descr_get_size),

    mean = interp2app(W_NDimArray.descr_mean),
    sum = interp2app(W_NDimArray.descr_sum),
    prod = interp2app(W_NDimArray.descr_prod),
    max = interp2app(W_NDimArray.descr_max),
    min = interp2app(W_NDimArray.descr_min),
    #argmax = interp2app(W_NDimArray.descr_argmax),
    #argmin = interp2app(W_NDimArray.descr_argmin),
    all = interp2app(W_NDimArray.descr_all),
    any = interp2app(W_NDimArray.descr_any),
    #dot = interp2app(W_NDimArray.descr_dot),
    #var = interp2app(W_NDimArray.descr_var),
    #std = interp2app(W_NDimArray.descr_std),

    copy = interp2app(W_NDimArray.descr_copy),
    reshape = interp2app(W_NDimArray.descr_reshape),
    T = GetSetProperty(W_NDimArray.descr_get_transpose),
)

def decode_w_dtype(space, w_dtype):
    if w_dtype is None or space.is_w(w_dtype, space.w_None):
        return None
    return space.interp_w(interp_dtype.W_Dtype,
          space.call_function(space.gettypefor(interp_dtype.W_Dtype), w_dtype))

@unwrap_spec(ndmin=int, copy=bool, subok=bool)
def array(space, w_object, w_dtype=None, copy=True, w_order=None, subok=False,
          ndmin=0):
    if not space.issequence_w(w_object):
        if w_dtype is None or space.is_w(w_dtype, space.w_None):
            w_dtype = interp_ufuncs.find_dtype_for_scalar(space, w_object)
        dtype = space.interp_w(interp_dtype.W_Dtype,
          space.call_function(space.gettypefor(interp_dtype.W_Dtype), w_dtype))
        return scalar_w(space, dtype, w_object)
    if w_order is None or space.is_w(w_order, space.w_None):
        order = 'C'
    else:
        order = space.str_w(w_order)
        if order != 'C':  # or order != 'F':
            raise operationerrfmt(space.w_ValueError, "Unknown order: %s",
                                  order)
    if isinstance(w_object, W_NDimArray):
        if (not space.is_w(w_dtype, space.w_None) and
            w_object.dtype is not w_dtype):
            raise operationerrfmt(space.w_NotImplementedError,
                                  "copying over different dtypes unsupported")
        if copy:
            return w_object.descr_copy(space)
        return w_object
    dtype = decode_w_dtype(space, w_dtype)
    shape, elems_w = find_shape_and_elems(space, w_object, dtype)
    if dtype is None:
        for w_elem in elems_w:
            dtype = interp_ufuncs.find_dtype_for_scalar(space, w_elem,
                                                        dtype)
            if dtype is interp_dtype.get_dtype_cache(space).w_float64dtype:
                break
        if dtype is None:
            dtype = interp_dtype.get_dtype_cache(space).w_float64dtype
    if ndmin > len(shape):
        shape = [1] * (ndmin - len(shape)) + shape
    arr = W_NDimArray(shape, dtype, order=order)
    arr_iter = arr.create_iter(arr.get_shape())
    for w_elem in elems_w:
        arr_iter.setitem(dtype.coerce(space, w_elem))
        arr_iter.next()
    return arr

@unwrap_spec(order=str)
def zeros(space, w_shape, w_dtype=None, order='C'):
    dtype = space.interp_w(interp_dtype.W_Dtype,
        space.call_function(space.gettypefor(interp_dtype.W_Dtype), w_dtype)
    )
    shape = _find_shape(space, w_shape)
    if not shape:
        return scalar_w(space, dtype, space.wrap(0))
    return space.wrap(W_NDimArray(shape, dtype=dtype, order=order))

@unwrap_spec(order=str)
def ones(space, w_shape, w_dtype=None, order='C'):
    dtype = space.interp_w(interp_dtype.W_Dtype,
        space.call_function(space.gettypefor(interp_dtype.W_Dtype), w_dtype)
    )
    shape = _find_shape(space, w_shape)
    if not shape:
        return scalar_w(space, dtype, space.wrap(0))
    arr = W_NDimArray(shape, dtype=dtype, order=order)
    one = dtype.box(1)
    arr.fill(one)
    return space.wrap(arr)


def dot(space):
    pass

def isna(space):
    pass

def concatenate(space):
    pass

def repeat(space):
    pass

def count_reduce_items(space):
    pass
