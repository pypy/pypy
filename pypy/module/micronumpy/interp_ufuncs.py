from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef, GetSetProperty, interp_attrproperty
from pypy.module.micronumpy import interp_boxes, interp_dtype, loop
from rpython.rlib import jit
from rpython.rlib.rarithmetic import LONG_BIT
from rpython.tool.sourcetools import func_with_new_name
from pypy.module.micronumpy.interp_support import unwrap_axis_arg
from pypy.module.micronumpy.strides import shape_agreement
from pypy.module.micronumpy.base import convert_to_array, W_NDimArray
from pypy.module.micronumpy.constants import *

def done_if_true(dtype, val):
    return dtype.itemtype.bool(val)

def done_if_false(dtype, val):
    return not dtype.itemtype.bool(val)


class W_Ufunc(W_Root):
    _immutable_fields_ = [
        "name", "promote_to_largest", "promote_to_float", "promote_bools",
        "identity", "int_only", "allow_bool", "allow_complex", "complex_to_float"
    ]

    def __init__(self, name, promote_to_largest, promote_to_float, promote_bools,
                 identity, int_only, allow_bool, allow_complex, complex_to_float):
        self.name = name
        self.promote_to_largest = promote_to_largest
        self.promote_to_float = promote_to_float
        self.promote_bools = promote_bools
        self.identity = identity
        self.int_only = int_only
        self.allow_bool = allow_bool
        self.allow_complex = allow_complex
        self.complex_to_float = complex_to_float

    def descr_get_name(self, space):
        return space.wrap(self.name)

    def descr_repr(self, space):
        return space.wrap("<ufunc '%s'>" % self.name)

    def descr_get_identity(self, space):
        if self.identity is None:
            return space.w_None
        return self.identity

    def descr_call(self, space, __args__):
        args_w, kwds_w = __args__.unpack()
        # it occurs to me that we don't support any datatypes that
        # require casting, change it later when we do
        kwds_w.pop('casting', None)
        w_subok = kwds_w.pop('subok', None)
        w_out = kwds_w.pop('out', space.w_None)
        # Setup a default value for out
        if space.is_w(w_out, space.w_None):
            out = None
        else:
            out = w_out
        if (w_subok is not None and space.is_true(w_subok)):
            raise OperationError(space.w_NotImplementedError,
                                 space.wrap("parameters unsupported"))
        if kwds_w or len(args_w) < self.argcount:
            raise OperationError(space.w_ValueError,
                space.wrap("invalid number of arguments")
            )
        elif (len(args_w) > self.argcount and out is not None) or \
             (len(args_w) > self.argcount + 1):
            raise OperationError(space.w_TypeError,
                space.wrap("invalid number of arguments")
            )
        # Override the default out value, if it has been provided in w_wargs
        if len(args_w) > self.argcount:
            out = args_w[-1]
        else:
            args_w = args_w + [out]
        if out is not None and not isinstance(out, W_NDimArray):
            raise OperationError(space.w_TypeError, space.wrap(
                                            'output must be an array'))
        return self.call(space, args_w)

    def descr_accumulate(self, space, w_obj, w_axis=None, w_dtype=None, w_out=None):
        if space.is_none(w_axis):
            w_axis = space.wrap(0)
        if space.is_none(w_out):
            out = None
        elif not isinstance(w_out, W_NDimArray):
            raise OperationError(space.w_TypeError, space.wrap(
                                                'output must be an array'))
        else:
            out = w_out
        return self.reduce(space, w_obj, w_axis, True, #keepdims must be true
                           out, w_dtype, cumulative=True)

    @unwrap_spec(skipna=bool, keepdims=bool)
    def descr_reduce(self, space, w_obj, w_axis=None, w_dtype=None,
                     skipna=False, keepdims=False, w_out=None):
        """reduce(...)
        reduce(a, axis=0)

        Reduces `a`'s dimension by one, by applying ufunc along one axis.

        Let :math:`a.shape = (N_0, ..., N_i, ..., N_{M-1})`.  Then
        :math:`ufunc.reduce(a, axis=i)[k_0, ..,k_{i-1}, k_{i+1}, .., k_{M-1}]` =
        the result of iterating `j` over :math:`range(N_i)`, cumulatively applying
        ufunc to each :math:`a[k_0, ..,k_{i-1}, j, k_{i+1}, .., k_{M-1}]`.
        For a one-dimensional array, reduce produces results equivalent to:
        ::

         r = op.identity # op = ufunc
         for i in xrange(len(A)):
           r = op(r, A[i])
         return r

        For example, add.reduce() is equivalent to sum().

        Parameters
        ----------
        a : array_like
            The array to act on.
        axis : int, optional
            The axis along which to apply the reduction.

        Examples
        --------
        >>> np.multiply.reduce([2,3,5])
        30

        A multi-dimensional array example:

        >>> X = np.arange(8).reshape((2,2,2))
        >>> X
        array([[[0, 1],
                [2, 3]],
               [[4, 5],
                [6, 7]]])
        >>> np.add.reduce(X, 0)
        array([[ 4,  6],
               [ 8, 10]])
        >>> np.add.reduce(X) # confirm: default axis value is 0
        array([[ 4,  6],
               [ 8, 10]])
        >>> np.add.reduce(X, 1)
        array([[ 2,  4],
               [10, 12]])
        >>> np.add.reduce(X, 2)
        array([[ 1,  5],
               [ 9, 13]])
        """
        from pypy.module.micronumpy.interp_numarray import W_NDimArray
        if w_axis is None:
            w_axis = space.wrap(0)
        if space.is_none(w_out):
            out = None
        elif not isinstance(w_out, W_NDimArray):
            raise OperationError(space.w_TypeError, space.wrap(
                'output must be an array'))
        else:
            out = w_out
        return self.reduce(space, w_obj, w_axis, keepdims, out, w_dtype)

    def reduce(self, space, w_obj, w_axis, keepdims=False, out=None, dtype=None,
               cumulative=False):
        if self.argcount != 2:
            raise OperationError(space.w_ValueError, space.wrap("reduce only "
                "supported for binary functions"))
        assert isinstance(self, W_Ufunc2)
        obj = convert_to_array(space, w_obj)
        if obj.get_dtype().is_flexible_type():
            raise OperationError(space.w_TypeError,
                      space.wrap('cannot perform reduce for flexible type'))
        obj_shape = obj.get_shape()
        if obj.is_scalar():
            return obj.get_scalar_value()
        shapelen = len(obj_shape)
        axis = unwrap_axis_arg(space, shapelen, w_axis)
        assert axis >= 0
        dtype = interp_dtype.decode_w_dtype(space, dtype)
        if dtype is None:
            if self.comparison_func:
                dtype = interp_dtype.get_dtype_cache(space).w_booldtype
            else:
                dtype = find_unaryop_result_dtype(
                    space, obj.get_dtype(),
                    promote_to_float=self.promote_to_float,
                    promote_to_largest=self.promote_to_largest,
                    promote_bools=self.promote_bools,
                )
        if self.identity is None:
            for i in range(shapelen):
                if space.is_none(w_axis) or i == axis:
                    if obj_shape[i] == 0:
                        raise oefmt(space.w_ValueError, "zero-size array to "
                                    "%s.reduce without identity", self.name)
        if shapelen > 1 and axis < shapelen:
            temp = None
            if cumulative:
                shape = obj_shape[:]
                temp_shape = obj_shape[:axis] + obj_shape[axis + 1:]
                if out:
                    dtype = out.get_dtype()
                temp = W_NDimArray.from_shape(space, temp_shape, dtype,
                                                w_instance=obj)
            elif keepdims:
                shape = obj_shape[:axis] + [1] + obj_shape[axis + 1:]
            else:
                shape = obj_shape[:axis] + obj_shape[axis + 1:]
            if out:
                # Test for shape agreement
                # XXX maybe we need to do broadcasting here, although I must
                #     say I don't understand the details for axis reduce
                if len(out.get_shape()) > len(shape):
                    raise oefmt(space.w_ValueError,
                                "output parameter for reduction operation %s "
                                "has too many dimensions", self.name)
                elif len(out.get_shape()) < len(shape):
                    raise oefmt(space.w_ValueError,
                                "output parameter for reduction operation %s "
                                "does not have enough dimensions", self.name)
                elif out.get_shape() != shape:
                    raise oefmt(space.w_ValueError,
                                "output parameter shape mismatch, expecting "
                                "[%s], got [%s]",
                                ",".join([str(x) for x in shape]),
                                ",".join([str(x) for x in out.get_shape()]),
                                )
                dtype = out.get_dtype()
            else:
                out = W_NDimArray.from_shape(space, shape, dtype, w_instance=obj)
            return loop.do_axis_reduce(space, shape, self.func, obj, dtype, axis, out,
                                       self.identity, cumulative, temp)
        if cumulative:
            if out:
                if out.get_shape() != [obj.get_size()]:
                    raise OperationError(space.w_ValueError, space.wrap(
                        "out of incompatible size"))
            else:
                out = W_NDimArray.from_shape(space, [obj.get_size()], dtype, w_instance=obj)
            loop.compute_reduce_cumulative(space, obj, out, dtype, self.func,
                                            self.identity)
            return out
        if out:
            if len(out.get_shape())>0:
                raise oefmt(space.w_ValueError,
                            "output parameter for reduction operation %s has "
                            "too many dimensions", self.name)
            dtype = out.get_dtype()
        res = loop.compute_reduce(space, obj, dtype, self.func, self.done_func,
                                  self.identity)
        if out:
            out.set_scalar_value(res)
            return out
        if keepdims:
            shape = [1] * len(obj_shape)
            out = W_NDimArray.from_shape(space, [1] * len(obj_shape), dtype, w_instance=obj)
            out.implementation.setitem(0, res)
            return out
        return res

    def descr_outer(self, space, __args__):
        return self._outer(space, __args__)

    def _outer(self, space, __args__):
        raise OperationError(space.w_ValueError, space.wrap(
            "outer product only supported for binary functions"))

class W_Ufunc1(W_Ufunc):
    _immutable_fields_ = ["func", "bool_result"]
    argcount = 1

    def __init__(self, func, name, promote_to_largest=False, promote_to_float=False,
            promote_bools=False, identity=None, bool_result=False, int_only=False,
            allow_bool=True, allow_complex=True, complex_to_float=False):
        W_Ufunc.__init__(self, name, promote_to_largest, promote_to_float, promote_bools,
                         identity, int_only, allow_bool, allow_complex, complex_to_float)
        self.func = func
        self.bool_result = bool_result

    def call(self, space, args_w):
        w_obj = args_w[0]
        out = None
        if len(args_w) > 1:
            out = args_w[1]
            if space.is_w(out, space.w_None):
                out = None
        w_obj = convert_to_array(space, w_obj)
        dtype = w_obj.get_dtype()
        if dtype.is_flexible_type():
            raise OperationError(space.w_TypeError,
                      space.wrap('Not implemented for this type'))
        if (self.int_only and not dtype.is_int_type() or
                not self.allow_bool and dtype.is_bool_type() or
                not self.allow_complex and dtype.is_complex_type()):
            raise OperationError(space.w_TypeError, space.wrap(
                "ufunc %s not supported for the input type" % self.name))
        calc_dtype = find_unaryop_result_dtype(space,
                                  w_obj.get_dtype(),
                                  promote_to_float=self.promote_to_float,
                                  promote_bools=self.promote_bools)
        if out is not None:
            if not isinstance(out, W_NDimArray):
                raise OperationError(space.w_TypeError, space.wrap(
                                                'output must be an array'))
            res_dtype = out.get_dtype()
            #if not w_obj.get_dtype().can_cast_to(res_dtype):
            #    raise oefmt(space.w_TypeError,
            #        "Cannot cast ufunc %s output from dtype('%s') to dtype('%s') with casting rule 'same_kind'", self.name, w_obj.get_dtype().name, res_dtype.name)
        elif self.bool_result:
            res_dtype = interp_dtype.get_dtype_cache(space).w_booldtype
        else:
            res_dtype = calc_dtype
            if self.complex_to_float and calc_dtype.is_complex_type():
                if calc_dtype.name == 'complex64':
                    res_dtype = interp_dtype.get_dtype_cache(space).w_float32dtype
                else:
                    res_dtype = interp_dtype.get_dtype_cache(space).w_float64dtype
        if w_obj.is_scalar():
            w_val = self.func(calc_dtype,
                              w_obj.get_scalar_value().convert_to(space, calc_dtype))
            if out is None:
                return w_val
            if out.is_scalar():
                out.set_scalar_value(w_val)
            else:
                out.fill(space, res_dtype.coerce(space, w_val))
            return out
        shape = shape_agreement(space, w_obj.get_shape(), out,
                                broadcast_down=False)
        return loop.call1(space, shape, self.func, calc_dtype, res_dtype,
                          w_obj, out)


class W_Ufunc2(W_Ufunc):
    _immutable_fields_ = ["func", "comparison_func", "done_func"]
    argcount = 2

    def __init__(self, func, name, promote_to_largest=False, promote_to_float=False,
            promote_bools=False, identity=None, comparison_func=False, int_only=False,
            allow_bool=True, allow_complex=True, complex_to_float=False):
        W_Ufunc.__init__(self, name, promote_to_largest, promote_to_float, promote_bools,
                         identity, int_only, allow_bool, allow_complex, complex_to_float)
        self.func = func
        self.comparison_func = comparison_func
        if name == 'logical_and':
            self.done_func = done_if_false
        elif name == 'logical_or':
            self.done_func = done_if_true
        else:
            self.done_func = None

    def are_common_types(self, dtype1, dtype2):
        if dtype1.is_complex_type() and dtype2.is_complex_type():
            return True
        elif not (dtype1.is_complex_type() or dtype2.is_complex_type()) and \
                (dtype1.is_int_type() and dtype2.is_int_type() or dtype1.is_float_type() and dtype2.is_float_type()) and \
                not (dtype1.is_bool_type() or dtype2.is_bool_type()):
            return True
        return False

    @jit.unroll_safe
    def call(self, space, args_w):
        if len(args_w) > 2:
            [w_lhs, w_rhs, w_out] = args_w
        else:
            [w_lhs, w_rhs] = args_w
            w_out = None
        w_lhs = convert_to_array(space, w_lhs)
        w_rhs = convert_to_array(space, w_rhs)
        w_ldtype = w_lhs.get_dtype()
        w_rdtype = w_rhs.get_dtype()
        if w_ldtype.is_str_type() and w_rdtype.is_str_type() and \
           self.comparison_func:
            pass
        elif (w_ldtype.is_str_type() or w_rdtype.is_str_type()) and \
            self.comparison_func and w_out is None:
            return space.wrap(False)
        elif (w_ldtype.is_flexible_type() or \
                w_rdtype.is_flexible_type()):
            raise OperationError(space.w_TypeError, space.wrap(
                 'unsupported operand dtypes %s and %s for "%s"' % \
                 (w_rdtype.get_name(), w_ldtype.get_name(),
                  self.name)))

        if self.are_common_types(w_ldtype, w_rdtype):
            if not w_lhs.is_scalar() and w_rhs.is_scalar():
                w_rdtype = w_ldtype
            elif w_lhs.is_scalar() and not w_rhs.is_scalar():
                w_ldtype = w_rdtype
        calc_dtype = find_binop_result_dtype(space,
            w_ldtype, w_rdtype,
            promote_to_float=self.promote_to_float,
            promote_bools=self.promote_bools)
        if (self.int_only and (not w_ldtype.is_int_type() or
                               not w_rdtype.is_int_type() or
                               not calc_dtype.is_int_type()) or
                not self.allow_bool and (w_ldtype.is_bool_type() or
                                         w_rdtype.is_bool_type()) or
                not self.allow_complex and (w_ldtype.is_complex_type() or
                                            w_rdtype.is_complex_type())):
            raise OperationError(space.w_TypeError, space.wrap(
                "ufunc '%s' not supported for the input types" % self.name))
        if space.is_none(w_out):
            out = None
        elif not isinstance(w_out, W_NDimArray):
            raise OperationError(space.w_TypeError, space.wrap(
                    'output must be an array'))
        else:
            out = w_out
            calc_dtype = out.get_dtype()
        if self.comparison_func:
            res_dtype = interp_dtype.get_dtype_cache(space).w_booldtype
        else:
            res_dtype = calc_dtype
        if w_lhs.is_scalar() and w_rhs.is_scalar():
            arr = self.func(calc_dtype,
                w_lhs.get_scalar_value().convert_to(space, calc_dtype),
                w_rhs.get_scalar_value().convert_to(space, calc_dtype)
            )
            if isinstance(out, W_NDimArray):
                if out.is_scalar():
                    out.set_scalar_value(arr)
                else:
                    out.fill(space, arr)
            else:
                out = arr
            return out
        new_shape = shape_agreement(space, w_lhs.get_shape(), w_rhs)
        new_shape = shape_agreement(space, new_shape, out, broadcast_down=False)
        return loop.call2(space, new_shape, self.func, calc_dtype,
                          res_dtype, w_lhs, w_rhs, out)


W_Ufunc.typedef = TypeDef("ufunc",
    __module__ = "numpy",

    __call__ = interp2app(W_Ufunc.descr_call),
    __repr__ = interp2app(W_Ufunc.descr_repr),
    __name__ = GetSetProperty(W_Ufunc.descr_get_name),

    identity = GetSetProperty(W_Ufunc.descr_get_identity),
    accumulate = interp2app(W_Ufunc.descr_accumulate),
    nin = interp_attrproperty("argcount", cls=W_Ufunc),

    reduce = interp2app(W_Ufunc.descr_reduce),
    outer = interp2app(W_Ufunc.descr_outer),
)


def find_binop_result_dtype(space, dt1, dt2, promote_to_float=False,
        promote_bools=False):
    if dt2 is None:
        return dt1
    # dt1.num should be <= dt2.num
    if dt1.num > dt2.num:
        dt1, dt2 = dt2, dt1
    # Some operations promote op(bool, bool) to return int8, rather than bool
    if promote_bools and (dt1.kind == dt2.kind == NPY_GENBOOLLTR):
        return interp_dtype.get_dtype_cache(space).w_int8dtype

    # Everything numeric promotes to complex
    if dt2.is_complex_type() or dt1.is_complex_type():
        if dt2.num == NPY_HALF:
            dt1, dt2 = dt2, dt1
        if dt2.num == NPY_CFLOAT:
            if dt1.num == NPY_DOUBLE:
                return interp_dtype.get_dtype_cache(space).w_complex128dtype
            elif dt1.num == NPY_LONGDOUBLE:
                return interp_dtype.get_dtype_cache(space).w_complexlongdtype
            return interp_dtype.get_dtype_cache(space).w_complex64dtype
        elif dt2.num == NPY_CDOUBLE:
            if dt1.num == NPY_LONGDOUBLE:
                return interp_dtype.get_dtype_cache(space).w_complexlongdtype
            return interp_dtype.get_dtype_cache(space).w_complex128dtype
        elif dt2.num == NPY_CLONGDOUBLE:
            return interp_dtype.get_dtype_cache(space).w_complexlongdtype
        else:
            raise OperationError(space.w_TypeError, space.wrap("Unsupported types"))

    if promote_to_float:
        return find_unaryop_result_dtype(space, dt2, promote_to_float=True)
    # If they're the same kind, choose the greater one.
    if dt1.kind == dt2.kind and not dt2.is_flexible_type():
        if dt2.num == NPY_HALF:
            return dt1
        return dt2

    # Everything promotes to float, and bool promotes to everything.
    if dt2.kind == NPY_FLOATINGLTR or dt1.kind == NPY_GENBOOLLTR:
        if dt2.num == NPY_HALF and dt1.itemtype.get_element_size() == 2:
            return interp_dtype.get_dtype_cache(space).w_float32dtype
        if dt2.num == NPY_HALF and dt1.itemtype.get_element_size() >= 4:
            return interp_dtype.get_dtype_cache(space).w_float64dtype
        if dt2.num == NPY_FLOAT and dt1.itemtype.get_element_size() >= 4:
            return interp_dtype.get_dtype_cache(space).w_float64dtype
        return dt2

    # for now this means mixing signed and unsigned
    if dt2.kind == NPY_SIGNEDLTR:
        # if dt2 has a greater number of bytes, then just go with it
        if dt1.itemtype.get_element_size() < dt2.itemtype.get_element_size():
            return dt2
        # we need to promote both dtypes
        dtypenum = dt2.num + 2
    elif dt2.num == NPY_ULONGLONG or (LONG_BIT == 64 and dt2.num == NPY_ULONG):
        # UInt64 + signed = Float64
        dtypenum = NPY_DOUBLE
    elif dt2.is_flexible_type():
        # For those operations that get here (concatenate, stack),
        # flexible types take precedence over numeric type
        if dt2.is_record_type():
            return dt2
        if dt1.is_str_or_unicode():
            if dt2.get_size() >= dt1.get_size():
                return dt2
            return dt1
        return dt2
    else:
        # increase to the next signed type
        dtypenum = dt2.num + 1
    newdtype = interp_dtype.get_dtype_cache(space).dtypes_by_num[dtypenum]

    if (newdtype.itemtype.get_element_size() > dt2.itemtype.get_element_size() or
            newdtype.kind == NPY_FLOATINGLTR):
        return newdtype
    else:
        # we only promoted to long on 32-bit or to longlong on 64-bit
        # this is really for dealing with the Long and Ulong dtypes
        dtypenum += 2
        return interp_dtype.get_dtype_cache(space).dtypes_by_num[dtypenum]

@jit.unroll_safe
def find_unaryop_result_dtype(space, dt, promote_to_float=False,
        promote_bools=False, promote_to_largest=False):
    if promote_to_largest:
        if dt.kind == NPY_GENBOOLLTR or dt.kind == NPY_SIGNEDLTR:
            if dt.get_size() * 8 < LONG_BIT:
                return interp_dtype.get_dtype_cache(space).w_longdtype
        elif dt.kind == NPY_UNSIGNEDLTR:
            if dt.get_size() * 8 < LONG_BIT:
                return interp_dtype.get_dtype_cache(space).w_ulongdtype
        else:
            assert dt.kind == NPY_FLOATINGLTR or dt.kind == NPY_COMPLEXLTR
        return dt
    if promote_bools and (dt.kind == NPY_GENBOOLLTR):
        return interp_dtype.get_dtype_cache(space).w_int8dtype
    if promote_to_float:
        if dt.kind == NPY_FLOATINGLTR or dt.kind == NPY_COMPLEXLTR:
            return dt
        if dt.num >= NPY_INT:
            return interp_dtype.get_dtype_cache(space).w_float64dtype
        for bytes, dtype in interp_dtype.get_dtype_cache(space).float_dtypes_by_num_bytes:
            if (dtype.kind == NPY_FLOATINGLTR and
                dtype.itemtype.get_element_size() > dt.itemtype.get_element_size()):
                return dtype
    return dt

def find_dtype_for_scalar(space, w_obj, current_guess=None):
    bool_dtype = interp_dtype.get_dtype_cache(space).w_booldtype
    long_dtype = interp_dtype.get_dtype_cache(space).w_longdtype
    int64_dtype = interp_dtype.get_dtype_cache(space).w_int64dtype
    uint64_dtype = interp_dtype.get_dtype_cache(space).w_uint64dtype
    complex_dtype = interp_dtype.get_dtype_cache(space).w_complex128dtype
    float_dtype = interp_dtype.get_dtype_cache(space).w_float64dtype
    if isinstance(w_obj, interp_boxes.W_GenericBox):
        dtype = w_obj.get_dtype(space)
        return find_binop_result_dtype(space, dtype, current_guess)

    if space.isinstance_w(w_obj, space.w_bool):
        return find_binop_result_dtype(space, bool_dtype, current_guess)
    elif space.isinstance_w(w_obj, space.w_int):
        return find_binop_result_dtype(space, long_dtype, current_guess)
    elif space.isinstance_w(w_obj, space.w_long):
        try:
            space.int_w(w_obj)
        except OperationError, e:
            if e.match(space, space.w_OverflowError):
                return find_binop_result_dtype(space, uint64_dtype,
                                               current_guess)
            raise
        return find_binop_result_dtype(space, int64_dtype, current_guess)
    elif space.isinstance_w(w_obj, space.w_float):
        return find_binop_result_dtype(space, float_dtype, current_guess)
    elif space.isinstance_w(w_obj, space.w_complex):
        return complex_dtype
    elif space.isinstance_w(w_obj, space.w_str):
        if current_guess is None:
            return interp_dtype.variable_dtype(space,
                                               'S%d' % space.len_w(w_obj))
        elif current_guess.num == NPY_STRING:
            if current_guess.get_size() < space.len_w(w_obj):
                return interp_dtype.variable_dtype(space,
                                                   'S%d' % space.len_w(w_obj))
        return current_guess
    raise oefmt(space.w_NotImplementedError,
                'unable to create dtype from objects, "%T" instance not '
                'supported', w_obj)

def ufunc_dtype_caller(space, ufunc_name, op_name, argcount, comparison_func,
                       bool_result):
    dtype_cache = interp_dtype.get_dtype_cache(space)
    if argcount == 1:
        def impl(res_dtype, value):
            res = getattr(res_dtype.itemtype, op_name)(value)
            if bool_result:
                return dtype_cache.w_booldtype.box(res)
            return res
    elif argcount == 2:
        def impl(res_dtype, lvalue, rvalue):
            res = getattr(res_dtype.itemtype, op_name)(lvalue, rvalue)
            if comparison_func:
                return dtype_cache.w_booldtype.box(res)
            return res
    return func_with_new_name(impl, ufunc_name)


class UfuncState(object):
    def __init__(self, space):
        "NOT_RPYTHON"
        for ufunc_def in [
            ("add", "add", 2, {"identity": 0, "promote_to_largest": True}),
            ("subtract", "sub", 2),
            ("multiply", "mul", 2, {"identity": 1, "promote_to_largest": True}),
            ("bitwise_and", "bitwise_and", 2, {"identity": 1,
                                               "int_only": True}),
            ("bitwise_or", "bitwise_or", 2, {"identity": 0,
                                             "int_only": True}),
            ("bitwise_xor", "bitwise_xor", 2, {"int_only": True}),
            ("invert", "invert", 1, {"int_only": True}),
            ("floor_divide", "floordiv", 2, {"promote_bools": True}),
            ("divide", "div", 2, {"promote_bools": True}),
            ("true_divide", "div", 2, {"promote_to_float": True}),
            ("mod", "mod", 2, {"promote_bools": True, 'allow_complex': False}),
            ("power", "pow", 2, {"promote_bools": True}),
            ("left_shift", "lshift", 2, {"int_only": True}),
            ("right_shift", "rshift", 2, {"int_only": True}),

            ("equal", "eq", 2, {"comparison_func": True}),
            ("not_equal", "ne", 2, {"comparison_func": True}),
            ("less", "lt", 2, {"comparison_func": True}),
            ("less_equal", "le", 2, {"comparison_func": True}),
            ("greater", "gt", 2, {"comparison_func": True}),
            ("greater_equal", "ge", 2, {"comparison_func": True}),
            ("isnan", "isnan", 1, {"bool_result": True}),
            ("isinf", "isinf", 1, {"bool_result": True}),
            ("isfinite", "isfinite", 1, {"bool_result": True}),

            ('logical_and', 'logical_and', 2, {'comparison_func': True,
                                               'identity': 1}),
            ('logical_or', 'logical_or', 2, {'comparison_func': True,
                                             'identity': 0}),
            ('logical_xor', 'logical_xor', 2, {'comparison_func': True}),
            ('logical_not', 'logical_not', 1, {'bool_result': True}),

            ("maximum", "max", 2),
            ("minimum", "min", 2),

            ("copysign", "copysign", 2, {"promote_to_float": True,
                                         "allow_complex": False}),

            ("positive", "pos", 1),
            ("negative", "neg", 1),
            ("absolute", "abs", 1, {"complex_to_float": True}),
            ("rint", "rint", 1),
            ("sign", "sign", 1, {"allow_bool": False}),
            ("signbit", "signbit", 1, {"bool_result": True,
                                       "allow_complex": False}),
            ("reciprocal", "reciprocal", 1),
            ("conjugate", "conj", 1),
            ("real", "real", 1, {"complex_to_float": True}),
            ("imag", "imag", 1, {"complex_to_float": True}),

            ("fabs", "fabs", 1, {"promote_to_float": True,
                                 "allow_complex": False}),
            ("fmax", "fmax", 2, {"promote_to_float": True}),
            ("fmin", "fmin", 2, {"promote_to_float": True}),
            ("fmod", "fmod", 2, {"promote_to_float": True,
                                 'allow_complex': False}),
            ("floor", "floor", 1, {"promote_to_float": True,
                                   "allow_complex": False}),
            ("ceil", "ceil", 1, {"promote_to_float": True,
                                   "allow_complex": False}),
            ("trunc", "trunc", 1, {"promote_to_float": True,
                                   "allow_complex": False}),
            ("exp", "exp", 1, {"promote_to_float": True}),
            ("exp2", "exp2", 1, {"promote_to_float": True}),
            ("expm1", "expm1", 1, {"promote_to_float": True}),

            ('sqrt', 'sqrt', 1, {'promote_to_float': True}),
            ('square', 'square', 1, {'promote_to_float': True}),

            ("sin", "sin", 1, {"promote_to_float": True}),
            ("cos", "cos", 1, {"promote_to_float": True}),
            ("tan", "tan", 1, {"promote_to_float": True}),
            ("arcsin", "arcsin", 1, {"promote_to_float": True}),
            ("arccos", "arccos", 1, {"promote_to_float": True}),
            ("arctan", "arctan", 1, {"promote_to_float": True}),
            ("arctan2", "arctan2", 2, {"promote_to_float": True,
                                       "allow_complex": False}),
            ("sinh", "sinh", 1, {"promote_to_float": True}),
            ("cosh", "cosh", 1, {"promote_to_float": True}),
            ("tanh", "tanh", 1, {"promote_to_float": True}),
            ("arcsinh", "arcsinh", 1, {"promote_to_float": True}),
            ("arccosh", "arccosh", 1, {"promote_to_float": True}),
            ("arctanh", "arctanh", 1, {"promote_to_float": True}),

            ("radians", "radians", 1, {"promote_to_float": True,
                                       "allow_complex": False}),
            ("degrees", "degrees", 1, {"promote_to_float": True,
                                       "allow_complex": False}),

            ("log", "log", 1, {"promote_to_float": True}),
            ("log2", "log2", 1, {"promote_to_float": True}),
            ("log10", "log10", 1, {"promote_to_float": True}),
            ("log1p", "log1p", 1, {"promote_to_float": True}),
            ("logaddexp", "logaddexp", 2, {"promote_to_float": True,
                                       "allow_complex": False}),
            ("logaddexp2", "logaddexp2", 2, {"promote_to_float": True,
                                       "allow_complex": False}),
        ]:
            self.add_ufunc(space, *ufunc_def)

    def add_ufunc(self, space, ufunc_name, op_name, argcount, extra_kwargs=None):
        if extra_kwargs is None:
            extra_kwargs = {}

        identity = extra_kwargs.get("identity")
        if identity is not None:
            identity = \
                 interp_dtype.get_dtype_cache(space).w_longdtype.box(identity)
        extra_kwargs["identity"] = identity

        func = ufunc_dtype_caller(space, ufunc_name, op_name, argcount,
            comparison_func=extra_kwargs.get("comparison_func", False),
            bool_result=extra_kwargs.get("bool_result", False),
        )
        if argcount == 1:
            ufunc = W_Ufunc1(func, ufunc_name, **extra_kwargs)
        elif argcount == 2:
            ufunc = W_Ufunc2(func, ufunc_name, **extra_kwargs)
        setattr(self, ufunc_name, ufunc)

def get(space):
    return space.fromcache(UfuncState)

