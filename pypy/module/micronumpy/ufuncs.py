from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault
from pypy.interpreter.typedef import TypeDef, GetSetProperty, interp_attrproperty
from pypy.interpreter.argument import Arguments
from rpython.rlib import jit
from rpython.rlib.rarithmetic import LONG_BIT, maxint
from rpython.tool.sourcetools import func_with_new_name
from pypy.module.micronumpy import boxes, descriptor, loop, constants as NPY
from pypy.module.micronumpy.base import convert_to_array, W_NDimArray
from pypy.module.micronumpy.ctors import numpify
from pypy.module.micronumpy.nditer import W_NDIter, coalesce_iter
from pypy.module.micronumpy.strides import shape_agreement
from pypy.module.micronumpy.support import _parse_signature
from rpython.rlib.rawstorage import (raw_storage_setitem, free_raw_storage,
             alloc_raw_storage)
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib.rarithmetic import LONG_BIT, _get_bitsize


def done_if_true(dtype, val):
    return dtype.itemtype.bool(val)


def done_if_false(dtype, val):
    return not dtype.itemtype.bool(val)

def _get_dtype(space, w_npyobj):
    if isinstance(w_npyobj, boxes.W_GenericBox):
        return w_npyobj.get_dtype(space)
    else:
        assert isinstance(w_npyobj, W_NDimArray)
        return w_npyobj.get_dtype()

class W_Ufunc(W_Root):
    _immutable_fields_ = [
        "name", "promote_to_largest", "promote_to_float", "promote_bools", "nin",
        "identity", "int_only", "allow_bool", "allow_complex",
        "complex_to_float", "nargs", "nout", "signature"
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
        # sig, extobj are used in generic ufuncs
        w_subok, w_out, sig, casting, extobj = self.parse_kwargs(space, kwds_w)
        if space.is_w(w_out, space.w_None):
            out = None
        else:
            out = w_out
        if (w_subok is not None and space.is_true(w_subok)):
            raise oefmt(space.w_NotImplementedError, "parameter subok unsupported")
        if kwds_w:
            # numpy compatible, raise with only the first of maybe many keys
            kw  = kwds_w.keys()[0]
            raise oefmt(space.w_TypeError,
                "'%s' is an invalid keyword to ufunc '%s'", kw, self.name)
        if len(args_w) < self.nin:
            raise oefmt(space.w_ValueError, "invalid number of arguments"
                ", expected %d got %d", len(args_w), self.nin)
        elif (len(args_w) > self.nin and out is not None) or \
             (len(args_w) > self.nin + 1):
            raise oefmt(space.w_TypeError, "invalid number of arguments")
        # Override the default out value, if it has been provided in w_wargs
        if len(args_w) > self.nin:
            if out:
                raise oefmt(space.w_ValueError, "cannot specify 'out' as both "
                    "a positional and keyword argument")
            out = args_w[-1]
        else:
            args_w = args_w + [out]
        if out is not None and not isinstance(out, W_NDimArray):
            raise OperationError(space.w_TypeError, space.wrap(
                                            'output must be an array'))
        return self.call(space, args_w, sig, casting, extobj)

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

    @unwrap_spec(keepdims=bool)
    def descr_reduce(self, space, w_obj, w_axis=None, w_dtype=None,
                     w_out=None, keepdims=False):
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
        from pypy.module.micronumpy.ndarray import W_NDimArray
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
        if self.nin != 2:
            raise oefmt(space.w_ValueError,
                        "reduce only supported for binary functions")
        assert isinstance(self, W_Ufunc2)
        obj = convert_to_array(space, w_obj)
        if obj.get_dtype().is_flexible():
            raise oefmt(space.w_TypeError,
                        "cannot perform reduce with flexible type")
        obj_shape = obj.get_shape()
        if obj.is_scalar():
            return obj.get_scalar_value()
        shapelen = len(obj_shape)
        if space.is_none(w_axis):
            axis = maxint
        else:
            if space.isinstance_w(w_axis, space.w_tuple) and space.len_w(w_axis) == 1:
                w_axis = space.getitem(w_axis, space.wrap(0))
            axis = space.int_w(w_axis)
            if axis < -shapelen or axis >= shapelen:
                raise oefmt(space.w_ValueError, "'axis' entry is out of bounds")
            if axis < 0:
                axis += shapelen
        assert axis >= 0
        dtype = descriptor.decode_w_dtype(space, dtype)
        if dtype is None:
            if self.comparison_func:
                dtype = descriptor.get_dtype_cache(space).w_booldtype
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
                        raise oefmt(space.w_ValueError,
                            "zero-size array to reduction operation %s "
                            "which has no identity", self.name)
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
                if out.ndims() > len(shape):
                    raise oefmt(space.w_ValueError,
                                "output parameter for reduction operation %s "
                                "has too many dimensions", self.name)
                elif out.ndims() < len(shape):
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
                out = W_NDimArray.from_shape(space, shape, dtype,
                                             w_instance=obj)
            if obj.get_size() == 0:
                if self.identity is not None:
                    out.fill(space, self.identity.convert_to(space, dtype))
                return out
            return loop.do_axis_reduce(space, shape, self.func, obj, dtype,
                                       axis, out, self.identity, cumulative,
                                       temp)
        if cumulative:
            if out:
                if out.get_shape() != [obj.get_size()]:
                    raise OperationError(space.w_ValueError, space.wrap(
                        "out of incompatible size"))
            else:
                out = W_NDimArray.from_shape(space, [obj.get_size()], dtype,
                                             w_instance=obj)
            loop.compute_reduce_cumulative(space, obj, out, dtype, self.func,
                                           self.identity)
            return out
        if out:
            if out.ndims() > 0:
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
            out = W_NDimArray.from_shape(space, [1] * len(obj_shape), dtype,
                                         w_instance=obj)
            out.implementation.setitem(0, res)
            return out
        return res

    def descr_outer(self, space, __args__):
        return self._outer(space, __args__)

    def _outer(self, space, __args__):
        raise OperationError(space.w_ValueError, space.wrap(
            "outer product only supported for binary functions"))

    def parse_kwargs(self, space, kwds_w):
        # we don't support casting, change it when we do
        casting = kwds_w.pop('casting', None)
        w_subok = kwds_w.pop('subok', None)
        w_out = kwds_w.pop('out', space.w_None)
        sig = None
        # TODO handle triple of extobj,
        # see _extract_pyvals in ufunc_object.c
        extobj_w = kwds_w.pop('extobj', get_extobj(space))
        if not space.isinstance_w(extobj_w, space.w_list) or space.len_w(extobj_w) != 3:
            raise oefmt(space.w_TypeError, "'extobj' must be a list of 3 values")
        return w_subok, w_out, sig, casting, extobj_w

def get_extobj(space):
        extobj_w = space.newlist([space.wrap(8192), space.wrap(0), space.w_None])
        return extobj_w

class W_Ufunc1(W_Ufunc):
    _immutable_fields_ = ["func", "bool_result"]
    nin = 1
    nout = 1
    nargs = 2
    signature = None

    def __init__(self, func, name, promote_to_largest=False, promote_to_float=False,
            promote_bools=False, identity=None, bool_result=False, int_only=False,
            allow_bool=True, allow_complex=True, complex_to_float=False):
        W_Ufunc.__init__(self, name, promote_to_largest, promote_to_float, promote_bools,
                         identity, int_only, allow_bool, allow_complex, complex_to_float)
        self.func = func
        self.bool_result = bool_result

    def call(self, space, args_w, sig, casting, extobj):
        w_obj = args_w[0]
        out = None
        if len(args_w) > 1:
            out = args_w[1]
            if space.is_w(out, space.w_None):
                out = None
        w_obj = numpify(space, w_obj)
        dtype = _get_dtype(space, w_obj)
        if dtype.is_flexible():
            raise OperationError(space.w_TypeError,
                      space.wrap('Not implemented for this type'))
        if (self.int_only and not dtype.is_int() or
                not self.allow_bool and dtype.is_bool() or
                not self.allow_complex and dtype.is_complex()):
            raise oefmt(space.w_TypeError,
                "ufunc %s not supported for the input type", self.name)
        calc_dtype = find_unaryop_result_dtype(space,
                                  dtype,
                                  promote_to_float=self.promote_to_float,
                                  promote_bools=self.promote_bools)
        if out is not None:
            if not isinstance(out, W_NDimArray):
                raise oefmt(space.w_TypeError, 'output must be an array')
            res_dtype = out.get_dtype()
            #if not w_obj.get_dtype().can_cast_to(res_dtype):
            #    raise oefmt(space.w_TypeError,
            #        "Cannot cast ufunc %s output from dtype('%s') to dtype('%s') with casting rule 'same_kind'", self.name, w_obj.get_dtype().name, res_dtype.name)
        elif self.bool_result:
            res_dtype = descriptor.get_dtype_cache(space).w_booldtype
        else:
            res_dtype = calc_dtype
            if self.complex_to_float and calc_dtype.is_complex():
                if calc_dtype.num == NPY.CFLOAT:
                    res_dtype = descriptor.get_dtype_cache(space).w_float32dtype
                else:
                    res_dtype = descriptor.get_dtype_cache(space).w_float64dtype
        if w_obj.is_scalar():
            w_val = self.func(calc_dtype,
                              w_obj.get_scalar_value().convert_to(space, calc_dtype))
            if out is None:
                return w_val
            w_val = res_dtype.coerce(space, w_val)
            if out.is_scalar():
                out.set_scalar_value(w_val)
            else:
                out.fill(space, w_val)
            return out
        assert isinstance(w_obj, W_NDimArray)
        shape = shape_agreement(space, w_obj.get_shape(), out,
                                broadcast_down=False)
        return loop.call1(space, shape, self.func, calc_dtype, res_dtype,
                          w_obj, out)


class W_Ufunc2(W_Ufunc):
    _immutable_fields_ = ["func", "comparison_func", "done_func"]
    nin = 2
    nout = 1
    nargs = 3
    signature = None

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
        if dtype1.is_bool() or dtype2.is_bool():
            return False
        if (dtype1.is_int() and dtype2.is_int() or
                dtype1.is_float() and dtype2.is_float() or
                dtype1.is_complex() and dtype2.is_complex()):
            return True
        return False

    @jit.unroll_safe
    def call(self, space, args_w, sig, casting, extobj):
        w_obj = args_w[0]
        if len(args_w) > 2:
            [w_lhs, w_rhs, w_out] = args_w
        else:
            [w_lhs, w_rhs] = args_w
            w_out = None
        w_lhs = numpify(space, w_lhs)
        w_rhs = numpify(space, w_rhs)
        w_ldtype = _get_dtype(space, w_lhs)
        w_rdtype = _get_dtype(space, w_rhs)
        if w_ldtype.is_str() and w_rdtype.is_str() and \
                self.comparison_func:
            pass
        elif (w_ldtype.is_str() or w_rdtype.is_str()) and \
                self.comparison_func and w_out is None:
            return space.wrap(False)
        elif w_ldtype.is_flexible() or w_rdtype.is_flexible():
            if self.comparison_func:
                if self.name == 'equal' or self.name == 'not_equal':
                    res = w_ldtype.eq(space, w_rdtype)
                    if not res:
                        return space.wrap(self.name == 'not_equal')
                else:
                    return space.w_NotImplemented
            else:
                raise oefmt(space.w_TypeError,
                            'unsupported operand dtypes %s and %s for "%s"',
                            w_rdtype.get_name(), w_ldtype.get_name(),
                            self.name)

        if self.are_common_types(w_ldtype, w_rdtype):
            if not w_lhs.is_scalar() and w_rhs.is_scalar():
                w_rdtype = w_ldtype
            elif w_lhs.is_scalar() and not w_rhs.is_scalar():
                w_ldtype = w_rdtype
        calc_dtype = find_binop_result_dtype(space,
            w_ldtype, w_rdtype,
            promote_to_float=self.promote_to_float,
            promote_bools=self.promote_bools)
        if (self.int_only and (not w_ldtype.is_int() or
                               not w_rdtype.is_int() or
                               not calc_dtype.is_int()) or
                not self.allow_bool and (w_ldtype.is_bool() or
                                         w_rdtype.is_bool()) or
                not self.allow_complex and (w_ldtype.is_complex() or
                                            w_rdtype.is_complex())):
            raise oefmt(space.w_TypeError,
                "ufunc '%s' not supported for the input types", self.name)
        if space.is_none(w_out):
            out = None
        elif not isinstance(w_out, W_NDimArray):
            raise oefmt(space.w_TypeError, 'output must be an array')
        else:
            out = w_out
            calc_dtype = out.get_dtype()
        if self.comparison_func:
            res_dtype = descriptor.get_dtype_cache(space).w_booldtype
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
        if isinstance(w_lhs, boxes.W_GenericBox):
            w_lhs = W_NDimArray.from_scalar(space, w_lhs)
        assert isinstance(w_lhs, W_NDimArray)
        if isinstance(w_rhs, boxes.W_GenericBox):
            w_rhs = W_NDimArray.from_scalar(space, w_rhs)
        assert isinstance(w_rhs, W_NDimArray)
        new_shape = shape_agreement(space, w_lhs.get_shape(), w_rhs)
        new_shape = shape_agreement(space, new_shape, out, broadcast_down=False)
        return loop.call2(space, new_shape, self.func, calc_dtype,
                          res_dtype, w_lhs, w_rhs, out)


class W_UfuncGeneric(W_Ufunc):
    '''
    Handle a number of python functions, each with a signature and dtypes.
    The signature can specify how to create the inner loop, i.e.
    (i,j),(j,k)->(i,k) for a dot-like matrix multiplication, and the dtypes
    can specify the input, output args for the function. When called, the actual
    function used will be resolved by examining the input arg's dtypes.

    If dtypes == 'match', only one argument is provided and the output dtypes
    will match the input dtype (not cpython numpy compatible)

    This is the parallel to PyUFuncOjbect, see include/numpy/ufuncobject.h
    '''
    _immutable_fields_ = ["funcs", "dtypes", "data", "match_dtypes"]

    def __init__(self, space, funcs, name, identity, nin, nout, dtypes, signature, match_dtypes=False, stack_inputs=False):
        # XXX make sure funcs, signature, dtypes, nin, nout are consistent

        # These don't matter, we use the signature and dtypes for determining
        # output dtype
        promote_to_largest = promote_to_float = promote_bools = False
        allow_bool = allow_complex = True
        int_only = complex_to_float = False
        W_Ufunc.__init__(self, name, promote_to_largest, promote_to_float, promote_bools,
                         identity, int_only, allow_bool, allow_complex, complex_to_float)
        self.funcs = funcs
        self.dtypes = dtypes
        self.nin = nin
        self.nout = nout
        self.match_dtypes = match_dtypes
        self.nargs = nin + max(nout, 1) # ufuncs can always be called with an out=<> kwarg
        if not match_dtypes and (len(dtypes) % len(funcs) != 0 or
                                  len(dtypes) / len(funcs) != self.nargs):
            raise oefmt(space.w_ValueError,
                "generic ufunc with %d functions, %d arguments, but %d dtypes",
                len(funcs), self.nargs, len(dtypes))
        self.signature = signature
        #These will be filled in by _parse_signature
        self.core_enabled = True    # False for scalar ufunc, True for generalized ufunc
        self.stack_inputs = stack_inputs
        self.core_num_dim_ix = 0 # number of distinct dimension names in signature
        self.core_num_dims = [0] * self.nargs  # number of core dimensions of each nargs
        self.core_offsets = [0] * self.nargs
        self.core_dim_ixs = [] # indices into unique shapes for each arg

    def reduce(self, space, w_obj, w_axis, keepdims=False, out=None, dtype=None,
               cumulative=False):
        raise oefmt(space.w_NotImplementedError, 'not implemented yet')

    def call(self, space, args_w, sig, casting, extobj):
        inargs = [None] * self.nin
        if len(args_w) < self.nin:
            raise oefmt(space.w_ValueError,
                 '%s called with too few input args, expected at least %d got %d',
                 self.name, self.nin, len(args_w))
        for i in range(self.nin):
            inargs[i] = convert_to_array(space, args_w[i])
        outargs = [None] * self.nout
        for i in range(len(args_w)-self.nin):
            out = args_w[i+self.nin]
            if space.is_w(out, space.w_None) or out is None:
                continue
            else:
                if not isinstance(out, W_NDimArray):
                    raise oefmt(space.w_TypeError,
                         'output arg %d must be an array, not %s', i+self.nin, str(args_w[i+self.nin]))
                outargs[i] = out
        if sig is None:
            sig = space.wrap(self.signature)
        index, dtypes = self.type_resolver(space, inargs, outargs, sig)
        outargs = self.alloc_outargs(space, index, inargs, outargs, dtypes)
        for i in range(len(outargs)):
            assert isinstance(outargs[i], W_NDimArray)
        outargs0 = outargs[0]
        assert isinstance(outargs0, W_NDimArray)
        res_dtype = outargs0.get_dtype()
        func = self.funcs[index]
        if not self.core_enabled:
            # func is going to do all the work, it must accept W_NDimArray args
            if self.stack_inputs:
                arglist = space.newlist(list(inargs + outargs))
                space.call_args(func, Arguments.frompacked(space, arglist))
            else:
                arglist = space.newlist(inargs)
                outargs = space.call_args(func, Arguments.frompacked(space, arglist))
                return outargs
            if len(outargs) < 2:
                return outargs[0]
            return space.newtuple(outargs)
        # Figure out the number of iteration dimensions, which
        # is the broadcast result of all the input non-core
        # dimensions
        broadcast_ndim = 0
        for i in range(len(inargs)):
            curarg = inargs[i]
            assert isinstance(curarg, W_NDimArray)
            n = curarg.ndims() - self.core_num_dims[i]
            broadcast_ndim = max(broadcast_ndim, n)
        # Figure out the number of iterator creation dimensions,
        # which is the broadcast dimensions + all the core dimensions of
        # the outputs, so that the iterator can allocate those output
        # dimensions following the rules of order='F', for example.
        iter_ndim = broadcast_ndim
        for i in range(self.nin, self.nargs):
            iter_ndim += self.core_num_dims[i];
        # Validate the core dimensions of all the operands,
        inner_dimensions = [1] * (self.core_num_dim_ix + 2)
        idim = 0
        core_start_dim = 0
        for i in range(self.nin):
            curarg = inargs[i]
            assert isinstance(curarg, W_NDimArray)
            dim_offset = self.core_offsets[i]
            num_dims = self.core_num_dims[i]
            core_start_dim = curarg.ndims() - num_dims
            if core_start_dim >=0:
                idim = 0
            else:
                idim = -core_start_dim
            while(idim < num_dims):
                core_dim_index = self.core_dim_ixs[dim_offset + idim]
                op_dim_size = curarg.get_shape()[core_start_dim + idim]
                if inner_dimensions[core_dim_index + 1] == 1:
                    inner_dimensions[core_dim_index + 1] = op_dim_size
                elif op_dim_size != 1 and inner_dimensions[1 + core_dim_index] != op_dim_size:
                    raise oefmt(space.w_ValueError, "%s: Operand %d has a "
                        "mismatch in its core dimension %d, with gufunc "
                        "signature %s (size %d is different from %d)",
                         self.name, i, idim, self.signature, op_dim_size,
                         inner_dimensions[1 + core_dim_index])
                idim += 1
        for i in range(len(outargs)):
            curarg = outargs[i]
            assert isinstance(curarg, W_NDimArray)
            dim_offset = self.core_offsets[i]
            num_dims = self.core_num_dims[i]
            core_start_dim = curarg.ndims() - num_dims
            if core_start_dim < 0:
                raise oefmt(space.w_ValueError, "%s: Output operand %d does "
                    "not have enough dimensions (has %d, gufunc with "
                    "signature %s requires %d)", self.name, i,
                    curarg.ndims(), self.signature, num_dims)
            if core_start_dim >=0:
                idim = 0
            else:
                idim = -core_start_dim
            while(idim < num_dims):
                core_dim_index = self.core_dim_ixs[dim_offset + idim]
                op_dim_size = curarg.get_shape()[core_start_dim + idim]
                if inner_dimensions[core_dim_index + 1] == 1:
                    inner_dimensions[core_dim_index + 1] = op_dim_size
                elif inner_dimensions[1 + core_dim_index] != op_dim_size:
                    raise oefmt(space.w_ValueError, "%s: Operand %d has a "
                        "mismatch in its core dimension %d, with gufunc "
                        "signature %s (size %d is different from %d)",
                         self.name, i, idim, self.signature, op_dim_size,
                         inner_dimensions[1 + core_dim_index])
                idim += 1
        iter_shape = [-1] * (broadcast_ndim + (len(outargs) * iter_ndim))
        j = broadcast_ndim
        core_dim_ixs_size = 0
        firstdim = broadcast_ndim
        for cnd in self.core_num_dims:
            firstdim  += cnd
        op_axes_arrays = [[-1,] * (self.nin + len(outargs)),] * firstdim
        for i in range(self.nin):
            # Note that n may be negative if broadcasting
            # extends into the core dimensions.
            curarg = inargs[i]
            assert isinstance(curarg, W_NDimArray)
            n = curarg.ndims() - self.core_num_dims[i]
            for idim in range(broadcast_ndim):
                if idim >= broadcast_ndim -n:
                    op_axes_arrays[idim][i] = idim - (broadcast_ndim -n)
            core_dim_ixs_size += self.core_num_dims[i];
        for i in range(len(outargs)):
            curarg = outargs[i]
            assert isinstance(curarg, W_NDimArray)
            iout = i + self.nin
            n = curarg.ndims() - self.core_num_dims[iout]
            for idim in range(broadcast_ndim):
                if idim >= broadcast_ndim -n:
                    op_axes_arrays[idim][iout] = idim - (broadcast_ndim -n)
            dim_offset = self.core_offsets[iout]
            num_dims = self.core_num_dims[iout]
            for idim in range(num_dims):
                cdi = self.core_dim_ixs[dim_offset + idim]
                iter_shape[j] = inner_dimensions[1 + cdi]
                op_axes_arrays[j][iout] = n + idim
                j += 1
            core_dim_ixs_size += self.core_num_dims[iout];
        # TODO once we support obejct dtypes,
        # FAIL with NotImplemented if the other object has
        # the __r<op>__ method and has a higher priority than
        # the current op (signalling it can handle ndarray's).

        # TODO parse and handle subok
        # TODO handle flags, op_flags
        w_flags = space.w_None # NOT 'external_loop', we do coalescing by core_num_dims
        w_op_flags = space.newtuple([space.wrap(r) for r in ['readonly'] * len(inargs)] + \
                                    [space.wrap(r) for r in ['readwrite'] * len(outargs)])
        w_op_dtypes = space.w_None
        w_casting = space.w_None
        w_itershape = space.newlist([space.wrap(i) for i in iter_shape]) 
        w_op_axes = space.w_None

        if self.stack_inputs:
            #print '\nsignature', sig
            #print [(d, getattr(self,d)) for d in dir(self) if 'core' in d or 'broad' in d]
            #print [(d, locals()[d]) for d in locals() if 'core' in d or 'broad' in d]
            #print 'shapes',[d.get_shape() for d in inargs + outargs]
            #print 'steps',[d.implementation.strides for d in inargs + outargs]
            if isinstance(func, W_GenericUFuncCaller):
                # Use GeneralizeUfunc interface with signature
                # Unlike numpy, we will not broadcast dims before
                # the core_ndims rather we use nditer iteration
                # so dims[0] == 1
                dims = [1] + inner_dimensions[1:]
                steps = []
                allargs = inargs + outargs
                assert core_start_dim >= 0
                for i in range(len(allargs)):
                    steps.append(0)
                for i in range(len(allargs)):
                    _arg = allargs[i]
                    assert isinstance(_arg, W_NDimArray)
                    steps += _arg.implementation.strides[core_start_dim:]
                #print 'set_dims_and_steps with dims, steps',dims,steps
                func.set_dims_and_steps(space, dims, steps)
            else:
                # it is a function, ready to be called by the iterator,
                # from frompyfunc
                pass
            # mimic NpyIter_AdvancedNew with a nditer
            nd_it = W_NDIter(space, space.newlist(inargs + outargs), w_flags,
                          w_op_flags, w_op_dtypes, w_casting, w_op_axes,
                          w_itershape)
            # coalesce each iterators, according to inner_dimensions
            if nd_it.order == 'F':
                fastest = 0
            else:
                fastest = -1
            for i in range(len(inargs) + len(outargs)):
                for j in range(self.core_num_dims[i]):
                    new_iter = coalesce_iter(nd_it.iters[i][0], nd_it.op_flags[i],
                                    nd_it, nd_it.order, fastest, flat=False)
                    nd_it.iters[i] = (new_iter, new_iter.reset())
            # do the iteration
            while not nd_it.done:
                # XXX jit me
                for it, st in nd_it.iters:
                    if not it.done(st):
                        break
                else:
                    nd_it.done = True
                    break
                args = []
                for i, (it, st) in enumerate(nd_it.iters):
                    args.append(nd_it.getitem(it, st))
                    nd_it.iters[i] = (it, it.next(st))
                space.call_args(func, Arguments.frompacked(space, space.newlist(args)))
            if len(outargs) > 1:
                return space.newtuple([convert_to_array(space, o) for o in outargs])
            return outargs[0]
        inargs0 = inargs[0]
        assert isinstance(inargs0, W_NDimArray)
        new_shape = inargs0.get_shape()
        if len(outargs) < 2:
            return loop.call_many_to_one(space, new_shape, func,
                                         res_dtype, inargs, outargs[0])
        return loop.call_many_to_many(space, new_shape, func,
                                         res_dtype, inargs, outargs)

    def parse_kwargs(self, space, kwargs_w):
        w_subok, w_out, casting, sig, extobj = \
                    W_Ufunc.parse_kwargs(self, space, kwargs_w)
        # do equivalent of get_ufunc_arguments in numpy's ufunc_object.c
        dtype_w = kwargs_w.pop('dtype', None)
        if not space.is_w(dtype_w, space.w_None) and not dtype_w is None:
            if sig:
                raise oefmt(space.w_RuntimeError,
                        "cannot specify both 'sig' and 'dtype'")
            dtype = descriptor.decode_w_dtype(space, dtype_w)
            sig = space.newtuple([dtype])
        order = kwargs_w.pop('dtype', None)
        if not space.is_w(order, space.w_None) and not order is None:
            raise oefmt(space.w_NotImplementedError, '"order" keyword not implemented')
        parsed_kw = []
        for kw in kwargs_w:
            if kw.startswith('sig'):
                if sig:
                    raise oefmt(space.w_RuntimeError,
                            "cannot specify both 'sig' and 'dtype'")
                sig = kwargs_w[kw]
                parsed_kw.append(kw)
            elif kw.startswith('where'):
                raise oefmt(space.w_NotImplementedError,
                            '"where" keyword not implemented')
                parsed_kw.append(kw)
        for kw in parsed_kw:
            kwargs_w.pop(kw)
        return w_subok, w_out, sig, casting, extobj

    def type_resolver(self, space, inargs, outargs, type_tup):
        # Find a match for the inargs.dtype in self.dtypes, like
        # linear_search_type_resolver in numpy ufunc_type_resolutions.c
        # type_tup can be '', a tuple of dtypes, or a string
        # of the form d,t -> D where the letters are dtype specs
        inargs0 = inargs[0]
        assert isinstance(inargs0, W_NDimArray)
        nop = len(inargs) + len(outargs)
        dtypes = []
        if isinstance(type_tup, str):
            if len(type_tup) == 1:
                dtypes = [get_dtype_cache(space).dtypes_by_name[type_tup]] * self.nargs
            elif len(type_tup) == self.nargs + 2:
                for i in range(len(inargs)):
                    dtypes.append(get_dtype_cache(space).dtype_by_name[type_tup[i]])
                #skip the '->' in the signature
                for i in range(len(self.nout)):
                    dtypes.append(get_dtype_cache(space).dtype_by_name[type_tup[i+2]])
            else:
                raise oefmt(space.w_TypeError, "a type-string for %s," \
                    "requires 1 typecode or %d typecode(s) before and %d" \
                    " after the -> sign", self.name, self.nin, self.nout)
        for i in range(0, len(self.dtypes), self.nargs):
            if inargs0.get_dtype() == self.dtypes[i]:
                break
        else:
            if len(self.funcs) < 2:
                return 0, dtypes
            raise oefmt(space.w_TypeError,
                         'input dtype %s did not match any known dtypes',
                                              str(inargs0.get_dtype()))
        return i / self.nargs, dtypes

    def alloc_outargs(self, space, index, inargs, outargs, dtypes):
        # Any None outarg should be allocated here
        inargs0 = inargs[0]
        assert isinstance(inargs0, W_NDimArray)
        temp_shape = inargs0.get_shape() # XXX wrong!!!
        dtype = inargs0.get_dtype() # XXX wrong!!!
        order = inargs0.get_order()
        for i in range(len(outargs)):
            if outargs[i] is None:
                outargs[i] = W_NDimArray.from_shape(space, temp_shape, dtype, order)
        for i in range(len(outargs)):
            assert isinstance(outargs[i], W_NDimArray)
        return outargs

W_Ufunc.typedef = TypeDef("numpy.ufunc",
    __call__ = interp2app(W_Ufunc.descr_call),
    __repr__ = interp2app(W_Ufunc.descr_repr),
    __name__ = GetSetProperty(W_Ufunc.descr_get_name),

    identity = GetSetProperty(W_Ufunc.descr_get_identity),
    accumulate = interp2app(W_Ufunc.descr_accumulate),
    nin = interp_attrproperty("nin", cls=W_Ufunc),
    nout = interp_attrproperty("nout", cls=W_Ufunc),
    nargs = interp_attrproperty("nargs", cls=W_Ufunc),
    signature = interp_attrproperty("signature", cls=W_Ufunc),

    reduce = interp2app(W_Ufunc.descr_reduce),
    outer = interp2app(W_Ufunc.descr_outer),
)


def find_binop_result_dtype(space, dt1, dt2, promote_to_float=False,
        promote_bools=False):
    if dt2 is None:
        return dt1
    if dt1 is None:
        return dt2
    # dt1.num should be <= dt2.num
    if dt1.num > dt2.num:
        dt1, dt2 = dt2, dt1
    # Some operations promote op(bool, bool) to return int8, rather than bool
    if promote_bools and (dt1.kind == dt2.kind == NPY.GENBOOLLTR):
        return descriptor.get_dtype_cache(space).w_int8dtype

    # Everything numeric promotes to complex
    if dt2.is_complex() or dt1.is_complex():
        if dt2.num == NPY.HALF:
            dt1, dt2 = dt2, dt1
        if dt2.num == NPY.CFLOAT:
            if dt1.num == NPY.DOUBLE:
                return descriptor.get_dtype_cache(space).w_complex128dtype
            elif dt1.num == NPY.LONGDOUBLE:
                return descriptor.get_dtype_cache(space).w_complexlongdtype
            return descriptor.get_dtype_cache(space).w_complex64dtype
        elif dt2.num == NPY.CDOUBLE:
            if dt1.num == NPY.LONGDOUBLE:
                return descriptor.get_dtype_cache(space).w_complexlongdtype
            return descriptor.get_dtype_cache(space).w_complex128dtype
        elif dt2.num == NPY.CLONGDOUBLE:
            return descriptor.get_dtype_cache(space).w_complexlongdtype
        else:
            raise OperationError(space.w_TypeError, space.wrap("Unsupported types"))

    if promote_to_float:
        return find_unaryop_result_dtype(space, dt2, promote_to_float=True)
    # If they're the same kind, choose the greater one.
    if dt1.kind == dt2.kind and not dt2.is_flexible():
        if dt2.num == NPY.HALF:
            return dt1
        return dt2

    # Everything promotes to float, and bool promotes to everything.
    if dt2.kind == NPY.FLOATINGLTR or dt1.kind == NPY.GENBOOLLTR:
        if dt2.num == NPY.HALF and dt1.itemtype.get_element_size() == 2:
            return descriptor.get_dtype_cache(space).w_float32dtype
        if dt2.num == NPY.HALF and dt1.itemtype.get_element_size() >= 4:
            return descriptor.get_dtype_cache(space).w_float64dtype
        if dt2.num == NPY.FLOAT and dt1.itemtype.get_element_size() >= 4:
            return descriptor.get_dtype_cache(space).w_float64dtype
        return dt2

    # for now this means mixing signed and unsigned
    if dt2.kind == NPY.SIGNEDLTR:
        # if dt2 has a greater number of bytes, then just go with it
        if dt1.itemtype.get_element_size() < dt2.itemtype.get_element_size():
            return dt2
        # we need to promote both dtypes
        dtypenum = dt2.num + 2
    elif dt2.num == NPY.ULONGLONG or (LONG_BIT == 64 and dt2.num == NPY.ULONG):
        # UInt64 + signed = Float64
        dtypenum = NPY.DOUBLE
    elif dt2.is_flexible():
        # For those operations that get here (concatenate, stack),
        # flexible types take precedence over numeric type
        if dt2.is_record():
            return dt2
        if dt1.is_str_or_unicode():
            if dt2.elsize >= dt1.elsize:
                return dt2
            return dt1
        return dt2
    else:
        # increase to the next signed type
        dtypenum = dt2.num + 1
    newdtype = descriptor.get_dtype_cache(space).dtypes_by_num[dtypenum]

    if (newdtype.itemtype.get_element_size() > dt2.itemtype.get_element_size() or
            newdtype.kind == NPY.FLOATINGLTR):
        return newdtype
    else:
        # we only promoted to long on 32-bit or to longlong on 64-bit
        # this is really for dealing with the Long and Ulong dtypes
        dtypenum += 2
        return descriptor.get_dtype_cache(space).dtypes_by_num[dtypenum]


@jit.unroll_safe
def find_unaryop_result_dtype(space, dt, promote_to_float=False,
        promote_bools=False, promote_to_largest=False):
    if promote_to_largest:
        if dt.kind == NPY.GENBOOLLTR or dt.kind == NPY.SIGNEDLTR:
            if dt.elsize * 8 < LONG_BIT:
                return descriptor.get_dtype_cache(space).w_longdtype
        elif dt.kind == NPY.UNSIGNEDLTR:
            if dt.elsize * 8 < LONG_BIT:
                return descriptor.get_dtype_cache(space).w_ulongdtype
        else:
            assert dt.kind == NPY.FLOATINGLTR or dt.kind == NPY.COMPLEXLTR
        return dt
    if promote_bools and (dt.kind == NPY.GENBOOLLTR):
        return descriptor.get_dtype_cache(space).w_int8dtype
    if promote_to_float:
        if dt.kind == NPY.FLOATINGLTR or dt.kind == NPY.COMPLEXLTR:
            return dt
        if dt.num >= NPY.INT:
            return descriptor.get_dtype_cache(space).w_float64dtype
        for bytes, dtype in descriptor.get_dtype_cache(space).float_dtypes_by_num_bytes:
            if (dtype.kind == NPY.FLOATINGLTR and
                    dtype.itemtype.get_element_size() >
                    dt.itemtype.get_element_size()):
                return dtype
    return dt


def find_dtype_for_scalar(space, w_obj, current_guess=None):
    bool_dtype = descriptor.get_dtype_cache(space).w_booldtype
    long_dtype = descriptor.get_dtype_cache(space).w_longdtype
    int64_dtype = descriptor.get_dtype_cache(space).w_int64dtype
    uint64_dtype = descriptor.get_dtype_cache(space).w_uint64dtype
    complex_dtype = descriptor.get_dtype_cache(space).w_complex128dtype
    float_dtype = descriptor.get_dtype_cache(space).w_float64dtype
    if isinstance(w_obj, boxes.W_GenericBox):
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
            return descriptor.variable_dtype(space,
                                               'S%d' % space.len_w(w_obj))
        elif current_guess.num == NPY.STRING:
            if current_guess.elsize < space.len_w(w_obj):
                return descriptor.variable_dtype(space,
                                                   'S%d' % space.len_w(w_obj))
        return current_guess
    raise oefmt(space.w_NotImplementedError,
                'unable to create dtype from objects, "%T" instance not '
                'supported', w_obj)


def ufunc_dtype_caller(space, ufunc_name, op_name, nin, comparison_func,
                       bool_result):
    def get_op(dtype):
        try:
            return getattr(dtype.itemtype, op_name)
        except AttributeError:
            raise oefmt(space.w_NotImplementedError,
                        "%s not implemented for %s",
                        ufunc_name, dtype.get_name())
    dtype_cache = descriptor.get_dtype_cache(space)
    if nin == 1:
        def impl(res_dtype, value):
            res = get_op(res_dtype)(value)
            if bool_result:
                return dtype_cache.w_booldtype.box(res)
            return res
    elif nin == 2:
        def impl(res_dtype, lvalue, rvalue):
            res = get_op(res_dtype)(lvalue, rvalue)
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

    def add_ufunc(self, space, ufunc_name, op_name, nin, extra_kwargs=None):
        if extra_kwargs is None:
            extra_kwargs = {}

        identity = extra_kwargs.get("identity")
        if identity is not None:
            identity = \
                descriptor.get_dtype_cache(space).w_longdtype.box(identity)
        extra_kwargs["identity"] = identity

        func = ufunc_dtype_caller(space, ufunc_name, op_name, nin,
            comparison_func=extra_kwargs.get("comparison_func", False),
            bool_result=extra_kwargs.get("bool_result", False),
        )
        if nin == 1:
            ufunc = W_Ufunc1(func, ufunc_name, **extra_kwargs)
        elif nin == 2:
            ufunc = W_Ufunc2(func, ufunc_name, **extra_kwargs)
        setattr(self, ufunc_name, ufunc)


def get(space):
    return space.fromcache(UfuncState)

@unwrap_spec(nin=int, nout=int, signature=str, w_identity=WrappedDefault(None),
             name=str, doc=str, stack_inputs=bool)
def frompyfunc(space, w_func, nin, nout, w_dtypes=None, signature='',
     w_identity=None, name='', doc='', stack_inputs=False):
    ''' frompyfunc(func, nin, nout) #cpython numpy compatible
        frompyfunc(func, nin, nout, dtypes=None, signature='',
                   identity=None, name='', doc='', stack_inputs=False)

    Takes an arbitrary Python function and returns a ufunc.

    Can be used, for example, to add broadcasting to a built-in Python
    function (see Examples section).

    Parameters
    ----------
    func : Python function object
        An arbitrary Python function or list of functions (if dtypes is specified).
    nin : int
        The number of input arguments.
    nout : int
        The number of arrays returned by `func`.
    dtypes: None or [dtype, ...] of the input, output args for each function,
               or 'match' to force output to exactly match input dtype
    signature*: str, default=''
         The mapping of input args to output args, defining the
         inner-loop indexing
    identity*: None (default) or int
         For reduce-type ufuncs, the default value
    name: str, default=''
    doc: str, default=''
    stack_inputs*: boolean, whether the function is of the form
            out = func(*in)  False
            or
            func(*[in + out])    True 

    only one of out_dtype or signature may be specified

    Returns
    -------
    out : ufunc
        Returns a Numpy universal function (``ufunc``) object.

    Notes
    -----
    If the signature and out_dtype are both missing, the returned ufunc
        always returns PyObject arrays (cpython numpy compatability).
    Input arguments marked with a * are pypy-only extensions

    Examples
    --------
    Use frompyfunc to add broadcasting to the Python function ``oct``:

    >>> oct_obj_array = np.frompyfunc(oct, 1, 1)
    >>> oct_obj_array(np.array((10, 30, 100)))
    array([012, 036, 0144], dtype=object)
    >>> np.array((oct(10), oct(30), oct(100))) # for comparison
    array(['012', '036', '0144'],
          dtype='|S4')
    >>> oct_array = np.frompyfunc(oct, 1, 1, out_dtype=str)
    >>> oct_obj_array(np.array((10, 30, 100)))
    array([012, 036, 0144], dtype='|S4')
    '''
    if (space.isinstance_w(w_func, space.w_tuple) or
        space.isinstance_w(w_func, space.w_list)):
        func = space.listview(w_func)
        for w_f in func:
            if not space.is_true(space.callable(w_f)):
                raise oefmt(space.w_TypeError, 'func must be callable')
    else:
        if not space.is_true(space.callable(w_func)):
            raise oefmt(space.w_TypeError, 'func must be callable')
        func = [w_func]
    match_dtypes = False
    if space.is_none(w_dtypes) and not signature:
        raise oefmt(space.w_NotImplementedError,
             'object dtype requested but not implemented')
    elif (space.isinstance_w(w_dtypes, space.w_tuple) or
            space.isinstance_w(w_dtypes, space.w_list)):
            _dtypes = space.listview(w_dtypes)
            if space.isinstance_w(_dtypes[0], space.w_str) and space.str_w(_dtypes[0]) == 'match':
                dtypes = []
                match_dtypes = True
            else:
                dtypes = [None]*len(_dtypes)
                for i in range(len(dtypes)):
                    dtypes[i] = descriptor.decode_w_dtype(space, _dtypes[i])
    else:
        raise oefmt(space.w_ValueError,
            'dtypes must be None or a list of dtypes')

    if space.is_none(w_identity):
        identity =  None
    elif space.isinstance_w(w_identity, space.w_int):
        identity = \
            descriptor.get_dtype_cache(space).w_longdtype.box(space.int_w(w_identity))
    else:
        raise oefmt(space.w_ValueError,
            'identity must be None or an int')

    if len(signature) == 0:
        # cpython compatability, func is of the form (),()->()
        signature = ','.join(['()'] * nin) + '->' + ','.join(['()'] * nout)
    else:
        #stack_inputs = True
        pass

    w_ret = W_UfuncGeneric(space, func, name, identity, nin, nout, dtypes,
                           signature, match_dtypes=match_dtypes,
                           stack_inputs=stack_inputs)
    _parse_signature(space, w_ret, w_ret.signature)
    if doc:
        w_ret.w_doc = space.wrap(doc)
    return w_ret

# Instantiated in cpyext/ndarrayobject. It is here since ufunc calls
# set_dims_and_steps, otherwise ufunc, ndarrayobject would have circular
# imports
npy_intpp = rffi.LONGP
LONG_SIZE = LONG_BIT / 8
CCHARP_SIZE = _get_bitsize('P') / 8

class W_GenericUFuncCaller(W_Root):
    _attrs_ = ['func', 'data', 'dims', 'steps', 'dims_steps_set']
    def __init__(self, func, data):
        self.func = func
        self.data = data
        self.dims = alloc_raw_storage(0, track_allocation=False)
        self.steps = alloc_raw_storage(0, track_allocation=False)
        self.dims_steps_set = False

    def __del__(self):
        free_raw_storage(self.dims, track_allocation=False)
        free_raw_storage(self.steps, track_allocation=False)

    def descr_call(self, space, __args__):
        args_w, kwds_w = __args__.unpack()
        # Can be called two ways, as a GenericUfunc or a GeneralizedUfunc.
        # The difference is in the meaning of dims and steps,
        # a GenericUfunc is a scalar function that flatiters over the array(s).
        # a GeneralizedUfunc will iterate over dims[0], but will use dims[1...]
        # and steps[1, ...] to call a function on ndarray(s).
        # set up via a call to set_dims_and_steps()
        dataps = alloc_raw_storage(CCHARP_SIZE * len(args_w), track_allocation=False)
        if self.dims_steps_set is False:
            self.dims = alloc_raw_storage(LONG_SIZE * len(args_w), track_allocation=False)
            self.steps = alloc_raw_storage(LONG_SIZE * len(args_w), track_allocation=False)
            for i in range(len(args_w)):
                arg_i = args_w[i]
                if not isinstance(arg_i, W_NDimArray):
                    raise OperationError(space.w_NotImplementedError,
                         space.wrap("cannot mix ndarray and %r (arg %d) in call to ufunc" % (
                                    arg_i, i)))
                raw_storage_setitem(dataps, CCHARP_SIZE * i,
                        rffi.cast(rffi.CCHARP, arg_i.implementation.get_storage_as_int(space)))
                #This assumes we iterate over the whole array (it should be a view...)
                raw_storage_setitem(self.dims, LONG_SIZE * i, rffi.cast(rffi.LONG, arg_i.get_size()))
                raw_storage_setitem(self.steps, LONG_SIZE * i, rffi.cast(rffi.LONG, arg_i.get_dtype().elsize))
        else:
            for i in range(len(args_w)):
                arg_i = args_w[i]
                assert isinstance(arg_i, W_NDimArray)
                raw_storage_setitem(dataps, CCHARP_SIZE * i,
                        rffi.cast(rffi.CCHARP, arg_i.implementation.get_storage_as_int(space)))
        try:
            arg1 = rffi.cast(rffi.CArrayPtr(rffi.CCHARP), dataps)
            arg2 = rffi.cast(npy_intpp, self.dims)
            arg3 = rffi.cast(npy_intpp, self.steps)
            self.func(arg1, arg2, arg3, self.data)
        finally:
            free_raw_storage(dataps, track_allocation=False)

    def set_dims_and_steps(self, space, dims, steps):
        if not isinstance(dims, list) or not isinstance(steps, list):
            raise oefmt(space.w_RuntimeError,
                 "set_dims_and_steps called inappropriately")
        if self.dims_steps_set:
            free_raw_storage(self.dims, track_allocation=False)
            free_raw_storage(self.steps, track_allocation=False)
        self.dims = alloc_raw_storage(LONG_SIZE * len(dims), track_allocation=False)
        self.steps = alloc_raw_storage(LONG_SIZE * len(steps), track_allocation=False)
        for i in range(len(dims)):
            raw_storage_setitem(self.dims, LONG_SIZE * i, rffi.cast(rffi.LONG, dims[i]))
        for i in range(len(steps)):
            raw_storage_setitem(self.steps, LONG_SIZE * i, rffi.cast(rffi.LONG, steps[i]))
        self.dims_steps_set = True

W_GenericUFuncCaller.typedef = TypeDef("hiddenclass",
    __call__ = interp2app(W_GenericUFuncCaller.descr_call),
)

GenericUfunc = lltype.FuncType([rffi.CArrayPtr(rffi.CCHARP), npy_intpp, npy_intpp,
                                      rffi.VOIDP], lltype.Void)
