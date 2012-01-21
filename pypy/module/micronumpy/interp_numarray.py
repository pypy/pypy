from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.module.micronumpy import interp_ufuncs, interp_dtype, signature
from pypy.module.micronumpy.strides import calculate_slice_strides,\
     shape_agreement, find_shape_and_elems, get_shape_from_iterable,\
     calc_new_strides
from pypy.rlib import jit
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.tool.sourcetools import func_with_new_name
from pypy.rlib.rstring import StringBuilder
from pypy.module.micronumpy.interp_iter import ArrayIterator, OneDimIterator,\
     SkipLastAxisIterator, Chunk, ViewIterator
from pypy.module.micronumpy.appbridge import get_appbridge_cache

numpy_driver = jit.JitDriver(
    greens=['shapelen', 'sig'],
    virtualizables=['frame'],
    reds=['result_size', 'frame', 'ri', 'self', 'result'],
    get_printable_location=signature.new_printable_location('numpy'),
    name='numpy',
)
all_driver = jit.JitDriver(
    greens=['shapelen', 'sig'],
    virtualizables=['frame'],
    reds=['frame', 'self', 'dtype'],
    get_printable_location=signature.new_printable_location('all'),
    name='numpy_all',
)
any_driver = jit.JitDriver(
    greens=['shapelen', 'sig'],
    virtualizables=['frame'],
    reds=['frame', 'self', 'dtype'],
    get_printable_location=signature.new_printable_location('any'),
    name='numpy_any',
)
slice_driver = jit.JitDriver(
    greens=['shapelen', 'sig'],
    virtualizables=['frame'],
    reds=['self', 'frame', 'arr'],
    get_printable_location=signature.new_printable_location('slice'),
    name='numpy_slice',
)
count_driver = jit.JitDriver(
    greens=['shapelen'],
    virtualizables=['frame'],
    reds=['s', 'frame', 'iter', 'arr'],
    name='numpy_count'
)
filter_driver = jit.JitDriver(
    greens=['shapelen', 'sig'],
    virtualizables=['frame'],
    reds=['concr', 'argi', 'ri', 'frame', 'v', 'res', 'self'],
    name='numpy_filter',
)
filter_set_driver = jit.JitDriver(
    greens=['shapelen', 'sig'],
    virtualizables=['frame'],
    reds=['idx', 'idxi', 'frame', 'arr'],
    name='numpy_filterset',
)

class BaseArray(Wrappable):
    _attrs_ = ["invalidates", "shape", 'size']

    _immutable_fields_ = []

    strides = None
    start = 0

    def __init__(self, shape):
        self.invalidates = []
        self.shape = shape

    def invalidated(self):
        if self.invalidates:
            self._invalidated()

    def _invalidated(self):
        for arr in self.invalidates:
            arr.force_if_needed()
        del self.invalidates[:]

    def add_invalidates(self, other):
        self.invalidates.append(other)

    def descr__new__(space, w_subtype, w_size, w_dtype=None):
        dtype = space.interp_w(interp_dtype.W_Dtype,
            space.call_function(space.gettypefor(interp_dtype.W_Dtype), w_dtype)
        )
        size, shape = _find_size_and_shape(space, w_size)
        return space.wrap(W_NDimArray(size, shape[:], dtype=dtype))

    def _unaryop_impl(ufunc_name):
        def impl(self, space):
            return getattr(interp_ufuncs.get(space), ufunc_name).call(space, [self])
        return func_with_new_name(impl, "unaryop_%s_impl" % ufunc_name)

    descr_pos = _unaryop_impl("positive")
    descr_neg = _unaryop_impl("negative")
    descr_abs = _unaryop_impl("absolute")

    def _binop_impl(ufunc_name):
        def impl(self, space, w_other):
            return getattr(interp_ufuncs.get(space), ufunc_name).call(space, [self, w_other])
        return func_with_new_name(impl, "binop_%s_impl" % ufunc_name)

    descr_add = _binop_impl("add")
    descr_sub = _binop_impl("subtract")
    descr_mul = _binop_impl("multiply")
    descr_div = _binop_impl("divide")
    descr_pow = _binop_impl("power")
    descr_mod = _binop_impl("mod")

    descr_eq = _binop_impl("equal")
    descr_ne = _binop_impl("not_equal")
    descr_lt = _binop_impl("less")
    descr_le = _binop_impl("less_equal")
    descr_gt = _binop_impl("greater")
    descr_ge = _binop_impl("greater_equal")

    descr_and = _binop_impl("bitwise_and")
    descr_or = _binop_impl("bitwise_or")

    def _binop_right_impl(ufunc_name):
        def impl(self, space, w_other):
            w_other = scalar_w(space,
                interp_ufuncs.find_dtype_for_scalar(space, w_other, self.find_dtype()),
                w_other
            )
            return getattr(interp_ufuncs.get(space), ufunc_name).call(space, [w_other, self])
        return func_with_new_name(impl, "binop_right_%s_impl" % ufunc_name)

    descr_radd = _binop_right_impl("add")
    descr_rsub = _binop_right_impl("subtract")
    descr_rmul = _binop_right_impl("multiply")
    descr_rdiv = _binop_right_impl("divide")
    descr_rpow = _binop_right_impl("power")
    descr_rmod = _binop_right_impl("mod")

    def _reduce_ufunc_impl(ufunc_name, promote_to_largest=False):
        def impl(self, space, w_axis=None):
            if space.is_w(w_axis, space.w_None):
                axis = -1
            else:
                axis = space.int_w(w_axis)
            return getattr(interp_ufuncs.get(space), ufunc_name).reduce(space,
                                        self, True, promote_to_largest, axis)
        return func_with_new_name(impl, "reduce_%s_impl" % ufunc_name)

    descr_sum = _reduce_ufunc_impl("add")
    descr_sum_promote = _reduce_ufunc_impl("add", True)
    descr_prod = _reduce_ufunc_impl("multiply", True)
    descr_max = _reduce_ufunc_impl("maximum")
    descr_min = _reduce_ufunc_impl("minimum")

    def _reduce_argmax_argmin_impl(op_name):
        reduce_driver = jit.JitDriver(
            greens=['shapelen', 'sig'],
            reds=['result', 'idx', 'frame', 'self', 'cur_best', 'dtype'],
            get_printable_location=signature.new_printable_location(op_name),
            name='numpy_' + op_name,
        )
        def loop(self):
            sig = self.find_sig()
            frame = sig.create_frame(self)
            cur_best = sig.eval(frame, self)
            shapelen = len(self.shape)
            frame.next(shapelen)
            dtype = self.find_dtype()
            result = 0
            idx = 1
            while not frame.done():
                reduce_driver.jit_merge_point(sig=sig,
                                              shapelen=shapelen,
                                              self=self, dtype=dtype,
                                              frame=frame, result=result,
                                              idx=idx,
                                              cur_best=cur_best)
                new_best = getattr(dtype.itemtype, op_name)(cur_best, sig.eval(frame, self))
                if dtype.itemtype.ne(new_best, cur_best):
                    result = idx
                    cur_best = new_best
                frame.next(shapelen)
                idx += 1
            return result
        def impl(self, space):
            if self.size == 0:
                raise OperationError(space.w_ValueError,
                    space.wrap("Can't call %s on zero-size arrays" % op_name))
            return space.wrap(loop(self))
        return func_with_new_name(impl, "reduce_arg%s_impl" % op_name)

    def _all(self):
        dtype = self.find_dtype()
        sig = self.find_sig()
        frame = sig.create_frame(self)
        shapelen = len(self.shape)
        while not frame.done():
            all_driver.jit_merge_point(sig=sig,
                                       shapelen=shapelen, self=self,
                                       dtype=dtype, frame=frame)
            if not dtype.itemtype.bool(sig.eval(frame, self)):
                return False
            frame.next(shapelen)
        return True

    def descr_all(self, space):
        return space.wrap(self._all())

    def _any(self):
        dtype = self.find_dtype()
        sig = self.find_sig()
        frame = sig.create_frame(self)
        shapelen = len(self.shape)
        while not frame.done():
            any_driver.jit_merge_point(sig=sig, frame=frame,
                                       shapelen=shapelen, self=self,
                                       dtype=dtype)
            if dtype.itemtype.bool(sig.eval(frame, self)):
                return True
            frame.next(shapelen)
        return False

    def descr_any(self, space):
        return space.wrap(self._any())

    descr_argmax = _reduce_argmax_argmin_impl("max")
    descr_argmin = _reduce_argmax_argmin_impl("min")

    def descr_dot(self, space, w_other):
        w_other = convert_to_array(space, w_other)
        if isinstance(w_other, Scalar):
            return self.descr_mul(space, w_other)
        else:
            w_res = self.descr_mul(space, w_other)
            assert isinstance(w_res, BaseArray)
            return w_res.descr_sum(space, space.wrap(-1))

    def get_concrete(self):
        raise NotImplementedError

    def descr_get_dtype(self, space):
        return space.wrap(self.find_dtype())

    def descr_get_ndim(self, space):
        return space.wrap(len(self.shape))

    @jit.unroll_safe
    def descr_get_shape(self, space):
        return space.newtuple([space.wrap(i) for i in self.shape])

    def descr_set_shape(self, space, w_iterable):
        new_shape = get_shape_from_iterable(space,
                            self.size, w_iterable)
        if isinstance(self, Scalar):
            return
        self.get_concrete().setshape(space, new_shape)

    def descr_get_size(self, space):
        return space.wrap(self.size)

    def descr_copy(self, space):
        return self.copy(space)

    def descr_flatten(self, space):
        return self.flatten(space)

    def copy(self, space):
        return self.get_concrete().copy(space)

    def flatten(self, space):
        return self.get_concrete().flatten(space)

    def descr_len(self, space):
        if len(self.shape):
            return space.wrap(self.shape[0])
        raise OperationError(space.w_TypeError, space.wrap(
            "len() of unsized object"))

    def descr_repr(self, space):
        res = StringBuilder()
        res.append("array(")
        concrete = self.get_concrete_or_scalar()
        dtype = concrete.find_dtype()
        if not concrete.size:
            res.append('[]')
            if len(self.shape) > 1:
                # An empty slice reports its shape
                res.append(", shape=(")
                self_shape = str(self.shape)
                res.append_slice(str(self_shape), 1, len(self_shape) - 1)
                res.append(')')
        else:
            concrete.to_str(space, 1, res, indent='       ')
        if (dtype is not interp_dtype.get_dtype_cache(space).w_float64dtype and
            not (dtype.kind == interp_dtype.SIGNEDLTR and
            dtype.itemtype.get_element_size() == rffi.sizeof(lltype.Signed)) or
            not self.size):
            res.append(", dtype=" + dtype.name)
        res.append(")")
        return space.wrap(res.build())

    def descr_str(self, space):
        cache = get_appbridge_cache(space)
        if cache.w_array_str is None:
            raise OperationError(space.w_RuntimeError, space.wrap(
                "str function not set"))
        return space.call_function(cache.w_array_str, self)
        
        ret = StringBuilder()
        concrete = self.get_concrete_or_scalar()
        concrete.to_str(space, 0, ret, ' ')
        return space.wrap(ret.build())

    @jit.unroll_safe
    def _single_item_result(self, space, w_idx):
        """ The result of getitem/setitem is a single item if w_idx
        is a list of scalars that match the size of shape
        """
        shape_len = len(self.shape)
        if shape_len == 0:
            raise OperationError(space.w_IndexError, space.wrap(
                "0-d arrays can't be indexed"))
        if shape_len == 1:
            if space.isinstance_w(w_idx, space.w_int):
                return True
            if space.isinstance_w(w_idx, space.w_slice):
                return False
        elif (space.isinstance_w(w_idx, space.w_slice) or
              space.isinstance_w(w_idx, space.w_int)):
            return False
        lgt = space.len_w(w_idx)
        if lgt > shape_len:
            raise OperationError(space.w_IndexError,
                                 space.wrap("invalid index"))
        if lgt < shape_len:
            return False
        for w_item in space.fixedview(w_idx):
            if space.isinstance_w(w_item, space.w_slice):
                return False
        return True

    @jit.unroll_safe
    def _prepare_slice_args(self, space, w_idx):
        if (space.isinstance_w(w_idx, space.w_int) or
            space.isinstance_w(w_idx, space.w_slice)):
            return [Chunk(*space.decode_index4(w_idx, self.shape[0]))]
        return [Chunk(*space.decode_index4(w_item, self.shape[i])) for i, w_item in
                enumerate(space.fixedview(w_idx))]

    def count_all_true(self, arr):
        sig = arr.find_sig()
        frame = sig.create_frame(self)
        shapelen = len(arr.shape)
        s = 0
        iter = None
        while not frame.done():
            count_driver.jit_merge_point(arr=arr, frame=frame, iter=iter, s=s,
                                         shapelen=shapelen)
            iter = frame.get_final_iter()
            s += arr.dtype.getitem_bool(arr.storage, iter.offset)
            frame.next(shapelen)
        return s

    def getitem_filter(self, space, arr):
        concr = arr.get_concrete()
        size = self.count_all_true(concr)
        res = W_NDimArray(size, [size], self.find_dtype())
        ri = ArrayIterator(size)
        shapelen = len(self.shape)
        argi = concr.create_iter()
        sig = self.find_sig()
        frame = sig.create_frame(self)
        v = None
        while not frame.done():
            filter_driver.jit_merge_point(concr=concr, argi=argi, ri=ri,
                                          frame=frame, v=v, res=res, sig=sig,
                                          shapelen=shapelen, self=self)
            if concr.dtype.getitem_bool(concr.storage, argi.offset):
                v = sig.eval(frame, self)
                res.setitem(ri.offset, v)
                ri = ri.next(1)
            else:
                ri = ri.next_no_increase(1)
            argi = argi.next(shapelen)
            frame.next(shapelen)
        return res

    def setitem_filter(self, space, idx, val):
        size = self.count_all_true(idx)
        arr = SliceArray([size], self.dtype, self, val)
        sig = arr.find_sig()
        shapelen = len(self.shape)
        frame = sig.create_frame(arr)
        idxi = idx.create_iter()
        while not frame.done():
            filter_set_driver.jit_merge_point(idx=idx, idxi=idxi, sig=sig,
                                              frame=frame, arr=arr,
                                              shapelen=shapelen)
            if idx.dtype.getitem_bool(idx.storage, idxi.offset):
                sig.eval(frame, arr)
                frame.next_from_second(1)
            frame.next_first(shapelen)
            idxi = idxi.next(shapelen)

    def descr_getitem(self, space, w_idx):
        if (isinstance(w_idx, BaseArray) and w_idx.shape == self.shape and
            w_idx.find_dtype().is_bool_type()):
            return self.getitem_filter(space, w_idx)
        if self._single_item_result(space, w_idx):
            concrete = self.get_concrete()
            item = concrete._index_of_single_item(space, w_idx)
            return concrete.getitem(item)
        chunks = self._prepare_slice_args(space, w_idx)
        return space.wrap(self.create_slice(chunks))

    def descr_setitem(self, space, w_idx, w_value):
        self.invalidated()
        if (isinstance(w_idx, BaseArray) and w_idx.shape == self.shape and
            w_idx.find_dtype().is_bool_type()):
            return self.get_concrete().setitem_filter(space,
                                                      w_idx.get_concrete(),
                                             convert_to_array(space, w_value))
        if self._single_item_result(space, w_idx):
            concrete = self.get_concrete()
            item = concrete._index_of_single_item(space, w_idx)
            dtype = concrete.find_dtype()
            concrete.setitem(item, dtype.coerce(space, w_value))
            return
        if not isinstance(w_value, BaseArray):
            w_value = convert_to_array(space, w_value)
        chunks = self._prepare_slice_args(space, w_idx)
        view = self.create_slice(chunks).get_concrete()
        view.setslice(space, w_value)

    @jit.unroll_safe
    def create_slice(self, chunks):
        shape = []
        i = -1
        for i, chunk in enumerate(chunks):
            chunk.extend_shape(shape)
        s = i + 1
        assert s >= 0
        shape += self.shape[s:]
        if not isinstance(self, ConcreteArray):
            return VirtualSlice(self, chunks, shape)
        r = calculate_slice_strides(self.shape, self.start, self.strides,
                                    self.backstrides, chunks)
        _, start, strides, backstrides = r
        return W_NDimSlice(start, strides[:], backstrides[:],
                           shape[:], self)

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
        concrete = self.get_concrete()
        new_shape = get_shape_from_iterable(space, concrete.size, w_shape)
        # Since we got to here, prod(new_shape) == self.size
        new_strides = calc_new_strides(new_shape,
                                       concrete.shape, concrete.strides)
        if new_strides:
            # We can create a view, strides somehow match up.
            ndims = len(new_shape)
            new_backstrides = [0] * ndims
            for nd in range(ndims):
                new_backstrides[nd] = (new_shape[nd] - 1) * new_strides[nd]
            arr = W_NDimSlice(concrete.start, new_strides, new_backstrides,
                              new_shape, self)
        else:
            # Create copy with contiguous data
            arr = concrete.copy(space)
            arr.setshape(space, new_shape)
        return arr

    def descr_tolist(self, space):
        if len(self.shape) == 0:
            assert isinstance(self, Scalar)
            return self.value.descr_tolist(space)
        w_result = space.newlist([])
        for i in range(self.shape[0]):
            space.call_method(w_result, "append",
                space.call_method(self.descr_getitem(space, space.wrap(i)), "tolist")
            )
        return w_result

    def descr_mean(self, space, w_axis=None):
        if space.is_w(w_axis, space.w_None):
            w_axis = space.wrap(-1)
            w_denom = space.wrap(self.size)
        else:
            dim = space.int_w(w_axis)
            w_denom = space.wrap(self.shape[dim])
        return space.div(self.descr_sum_promote(space, w_axis), w_denom)

    def descr_var(self, space, w_axis=None):
        return get_appbridge_cache(space).call_method(space, '_var', self,
                                                      w_axis)

    def descr_std(self, space, w_axis=None):
        return get_appbridge_cache(space).call_method(space, '_std', self,
                                                      w_axis)

    def descr_fill(self, space, w_value):
        concr = self.get_concrete_or_scalar()
        concr.fill(space, w_value)

    def descr_nonzero(self, space):
        if self.size > 1:
            raise OperationError(space.w_ValueError, space.wrap(
                "The truth value of an array with more than one element is ambiguous. Use a.any() or a.all()"))
        concr = self.get_concrete_or_scalar()
        sig = concr.find_sig()
        frame = sig.create_frame(self)
        return space.wrap(space.is_true(
            sig.eval(frame, concr)))

    def get_concrete_or_scalar(self):
        return self.get_concrete()

    def descr_get_transpose(self, space):
        concrete = self.get_concrete()
        if len(concrete.shape) < 2:
            return space.wrap(self)
        strides = []
        backstrides = []
        shape = []
        for i in range(len(concrete.shape) - 1, -1, -1):
            strides.append(concrete.strides[i])
            backstrides.append(concrete.backstrides[i])
            shape.append(concrete.shape[i])
        return space.wrap(W_NDimSlice(concrete.start, strides,
                                      backstrides, shape, concrete))

    def descr_get_flatiter(self, space):
        return space.wrap(W_FlatIterator(self))

    def getitem(self, item):
        raise NotImplementedError

    def find_sig(self, res_shape=None, arr=None):
        """ find a correct signature for the array
        """
        res_shape = res_shape or self.shape
        arr = arr or self
        return signature.find_sig(self.create_sig(), arr)

    def descr_array_iface(self, space):
        if not self.shape:
            raise OperationError(space.w_TypeError,
                space.wrap("can't get the array data of a 0-d array for now")
            )
        concrete = self.get_concrete()
        storage = concrete.storage
        addr = rffi.cast(lltype.Signed, storage)
        w_d = space.newdict()
        space.setitem_str(w_d, 'data', space.newtuple([space.wrap(addr),
                                                       space.w_False]))
        return w_d

    def supports_fast_slicing(self):
        return False

def convert_to_array(space, w_obj):
    if isinstance(w_obj, BaseArray):
        return w_obj
    elif space.issequence_w(w_obj):
        # Convert to array.
        return array(space, w_obj, w_order=None)
    else:
        # If it's a scalar
        dtype = interp_ufuncs.find_dtype_for_scalar(space, w_obj)
        return scalar_w(space, dtype, w_obj)

def scalar_w(space, dtype, w_obj):
    return Scalar(dtype, dtype.coerce(space, w_obj))

class Scalar(BaseArray):
    """
    Intermediate class representing a literal.
    """
    size = 1
    _attrs_ = ["dtype", "value", "shape"]

    def __init__(self, dtype, value):
        self.shape = []
        BaseArray.__init__(self, [])
        self.dtype = dtype
        self.value = value

    def find_dtype(self):
        return self.dtype

    def to_str(self, space, comma, builder, indent=' ', use_ellipsis=False):
        builder.append(self.dtype.itemtype.str_format(self.value))

    def copy(self, space):
        return Scalar(self.dtype, self.value)

    def flatten(self, space):
        array = W_NDimArray(self.size, [self.size], self.dtype)
        array.setitem(0, self.value)
        return array

    def fill(self, space, w_value):
        self.value = self.dtype.coerce(space, w_value)

    def create_sig(self):
        return signature.ScalarSignature(self.dtype)

    def get_concrete_or_scalar(self):
        return self


class VirtualArray(BaseArray):
    """
    Class for representing virtual arrays, such as binary ops or ufuncs
    """
    def __init__(self, name, shape, res_dtype):
        BaseArray.__init__(self, shape)
        self.forced_result = None
        self.res_dtype = res_dtype
        self.name = name

    def _del_sources(self):
        # Function for deleting references to source arrays,
        # to allow garbage-collecting them
        raise NotImplementedError

    def compute(self):
        result = W_NDimArray(self.size, self.shape, self.find_dtype())
        shapelen = len(self.shape)
        sig = self.find_sig()
        frame = sig.create_frame(self)
        ri = ArrayIterator(self.size)
        while not ri.done():
            numpy_driver.jit_merge_point(sig=sig,
                                         shapelen=shapelen,
                                         result_size=self.size,
                                         frame=frame,
                                         ri=ri,
                                         self=self, result=result)
            result.setitem(ri.offset, sig.eval(frame, self))
            frame.next(shapelen)
            ri = ri.next(shapelen)
        return result

    def force_if_needed(self):
        if self.forced_result is None:
            self.forced_result = self.compute()
            self._del_sources()

    def get_concrete(self):
        self.force_if_needed()
        res = self.forced_result
        assert isinstance(res, ConcreteArray)
        return res

    def getitem(self, item):
        return self.get_concrete().getitem(item)

    def setitem(self, item, value):
        return self.get_concrete().setitem(item, value)

    def find_dtype(self):
        return self.res_dtype

class VirtualSlice(VirtualArray):
    def __init__(self, child, chunks, shape):
        size = 1
        for sh in shape:
            size *= sh
        self.child = child
        self.chunks = chunks
        self.size = size
        VirtualArray.__init__(self, 'slice', shape, child.find_dtype())

    def create_sig(self):
        if self.forced_result is not None:
            return self.forced_result.create_sig()
        return signature.VirtualSliceSignature(
            self.child.create_sig())

    def force_if_needed(self):
        if self.forced_result is None:
            concr = self.child.get_concrete()
            self.forced_result = concr.create_slice(self.chunks)

    def _del_sources(self):
        self.child = None


class Call1(VirtualArray):
    def __init__(self, ufunc, name, shape, res_dtype, values):
        VirtualArray.__init__(self, name, shape, res_dtype)
        self.values = values
        self.size = values.size
        self.ufunc = ufunc

    def _del_sources(self):
        self.values = None

    def create_sig(self):
        if self.forced_result is not None:
            return self.forced_result.create_sig()
        return signature.Call1(self.ufunc, self.name, self.values.create_sig())

class Call2(VirtualArray):
    """
    Intermediate class for performing binary operations.
    """
    _immutable_fields_ = ['left', 'right']

    def __init__(self, ufunc, name, shape, calc_dtype, res_dtype, left, right):
        VirtualArray.__init__(self, name, shape, res_dtype)
        self.ufunc = ufunc
        self.left = left
        self.right = right
        self.calc_dtype = calc_dtype
        self.size = 1
        for s in self.shape:
            self.size *= s

    def _del_sources(self):
        self.left = None
        self.right = None

    def create_sig(self):
        if self.forced_result is not None:
            return self.forced_result.create_sig()
        if self.shape != self.left.shape and self.shape != self.right.shape:
            return signature.BroadcastBoth(self.ufunc, self.name,
                                           self.calc_dtype,
                                           self.left.create_sig(),
                                           self.right.create_sig())
        elif self.shape != self.left.shape:
            return signature.BroadcastLeft(self.ufunc, self.name,
                                           self.calc_dtype,
                                           self.left.create_sig(),
                                           self.right.create_sig())
        elif self.shape != self.right.shape:
            return signature.BroadcastRight(self.ufunc, self.name,
                                            self.calc_dtype,
                                            self.left.create_sig(),
                                            self.right.create_sig())
        return signature.Call2(self.ufunc, self.name, self.calc_dtype,
                               self.left.create_sig(), self.right.create_sig())

class SliceArray(Call2):
    def __init__(self, shape, dtype, left, right, no_broadcast=False):
        self.no_broadcast = no_broadcast
        Call2.__init__(self, None, 'sliceloop', shape, dtype, dtype, left,
                       right)

    def create_sig(self):
        lsig = self.left.create_sig()
        rsig = self.right.create_sig()
        if not self.no_broadcast and self.shape != self.right.shape:
            return signature.SliceloopBroadcastSignature(self.ufunc,
                                                         self.name,
                                                         self.calc_dtype,
                                                         lsig, rsig)
        return signature.SliceloopSignature(self.ufunc, self.name,
                                            self.calc_dtype,
                                            lsig, rsig)

class AxisReduce(Call2):
    """ NOTE: this is only used as a container, you should never
    encounter such things in the wild. Remove this comment
    when we'll make AxisReduce lazy
    """
    _immutable_fields_ = ['left', 'right']

    def __init__(self, ufunc, name, shape, dtype, left, right, dim):
        Call2.__init__(self, ufunc, name, shape, dtype, dtype,
                       left, right)
        self.dim = dim

class ConcreteArray(BaseArray):
    """ An array that have actual storage, whether owned or not
    """
    _immutable_fields_ = ['storage']

    def __init__(self, size, shape, dtype, order='C', parent=None):
        self.size = size
        self.parent = parent
        if parent is not None:
            self.storage = parent.storage
        else:
            self.storage = dtype.malloc(size)
        self.order = order
        self.dtype = dtype
        if self.strides is None:
            self.calc_strides(shape)
        BaseArray.__init__(self, shape)
        if parent is not None:
            self.invalidates = parent.invalidates

    def get_concrete(self):
        return self

    def supports_fast_slicing(self):
        return self.order == 'C' and self.strides[-1] == 1

    def find_dtype(self):
        return self.dtype

    def getitem(self, item):
        return self.dtype.getitem(self.storage, item)

    def setitem(self, item, value):
        self.invalidated()
        self.dtype.setitem(self.storage, item, value)

    def calc_strides(self, shape):
        strides = []
        backstrides = []
        s = 1
        shape_rev = shape[:]
        if self.order == 'C':
            shape_rev.reverse()
        for sh in shape_rev:
            strides.append(s)
            backstrides.append(s * (sh - 1))
            s *= sh
        if self.order == 'C':
            strides.reverse()
            backstrides.reverse()
        self.strides = strides
        self.backstrides = backstrides

    def to_str(self, space, comma, builder, indent=' ', use_ellipsis=False):
        '''Modifies builder with a representation of the array/slice
        The items will be seperated by a comma if comma is 1
        Multidimensional arrays/slices will span a number of lines,
        each line will begin with indent.
        '''
        size = self.size
        ccomma = ',' * comma
        ncomma = ',' * (1 - comma)
        dtype = self.find_dtype()
        if size < 1:
            builder.append('[]')
            return
        if size > 1000:
            # Once this goes True it does not go back to False for recursive
            # calls
            use_ellipsis = True
        ndims = len(self.shape)
        if ndims == 0:
            builder.append(dtype.itemtype.str_format(self.getitem(0)))
            return
        i = 0
        builder.append('[')
        if ndims > 1:
            if use_ellipsis:
                for i in range(min(3, self.shape[0])):
                    if i > 0:
                        builder.append(ccomma + '\n')
                        if ndims >= 3:
                            builder.append('\n' + indent)
                        else:
                            builder.append(indent)
                    view = self.create_slice([Chunk(i, 0, 0, 1)]).get_concrete()
                    view.to_str(space, comma, builder, indent=indent + ' ',
                                                    use_ellipsis=use_ellipsis)
                if i < self.shape[0] - 1:
                    builder.append(ccomma + '\n' + indent + '...' + ncomma)
                    i = self.shape[0] - 3
                else:
                    i += 1
            while i < self.shape[0]:
                if i > 0:
                    builder.append(ccomma + '\n')
                    if ndims >= 3:
                        builder.append('\n' + indent)
                    else:
                        builder.append(indent)
                # create_slice requires len(chunks) > 1 in order to reduce
                # shape
                view = self.create_slice([Chunk(i, 0, 0, 1)]).get_concrete()
                view.to_str(space, comma, builder, indent=indent + ' ',
                                                    use_ellipsis=use_ellipsis)
                i += 1
        elif ndims == 1:
            spacer = ccomma + ' '
            item = self.start
            # An iterator would be a nicer way to walk along the 1d array, but
            # how do I reset it if printing ellipsis? iterators have no
            # "set_offset()"
            i = 0
            if use_ellipsis:
                for i in range(min(3, self.shape[0])):
                    if i > 0:
                        builder.append(spacer)
                    builder.append(dtype.itemtype.str_format(self.getitem(item)))
                    item += self.strides[0]
                if i < self.shape[0] - 1:
                    # Add a comma only if comma is False - this prevents adding
                    # two commas
                    builder.append(spacer + '...' + ncomma)
                    # Ugly, but can this be done with an iterator?
                    item = self.start + self.backstrides[0] - 2 * self.strides[0]
                    i = self.shape[0] - 3
                else:
                    i += 1
            while i < self.shape[0]:
                if i > 0:
                    builder.append(spacer)
                builder.append(dtype.itemtype.str_format(self.getitem(item)))
                item += self.strides[0]
                i += 1
        builder.append(']')

    @jit.unroll_safe
    def _index_of_single_item(self, space, w_idx):
        if space.isinstance_w(w_idx, space.w_int):
            idx = space.int_w(w_idx)
            if idx < 0:
                idx = self.shape[0] + idx
            if idx < 0 or idx >= self.shape[0]:
                raise OperationError(space.w_IndexError,
                                     space.wrap("index out of range"))
            return self.start + idx * self.strides[0]
        index = [space.int_w(w_item)
                 for w_item in space.fixedview(w_idx)]
        item = self.start
        for i in range(len(index)):
            v = index[i]
            if v < 0:
                v += self.shape[i]
            if v < 0 or v >= self.shape[i]:
                raise operationerrfmt(space.w_IndexError,
                    "index (%d) out of range (0<=index<%d", i, self.shape[i],
                )
            item += v * self.strides[i]
        return item

    def setslice(self, space, w_value):
        res_shape = shape_agreement(space, self.shape, w_value.shape)
        if (res_shape == w_value.shape and self.supports_fast_slicing() and
            w_value.supports_fast_slicing() and
            self.dtype is w_value.find_dtype()):
            self._fast_setslice(space, w_value)
        else:
            arr = SliceArray(self.shape, self.dtype, self, w_value)
            self._sliceloop(arr)

    def _fast_setslice(self, space, w_value):
        assert isinstance(w_value, ConcreteArray)
        itemsize = self.dtype.itemtype.get_element_size()
        shapelen = len(self.shape)
        if shapelen == 1:
            rffi.c_memcpy(
                rffi.ptradd(self.storage, self.start * itemsize),
                rffi.ptradd(w_value.storage, w_value.start * itemsize),
                self.size * itemsize
            )
        else:
            dest = SkipLastAxisIterator(self)
            source = SkipLastAxisIterator(w_value)
            while not dest.done:
                rffi.c_memcpy(
                    rffi.ptradd(self.storage, dest.offset * itemsize),
                    rffi.ptradd(w_value.storage, source.offset * itemsize),
                    self.shape[-1] * itemsize
                )
                source.next()
                dest.next()

    def _sliceloop(self, arr):
        sig = arr.find_sig()
        frame = sig.create_frame(arr)
        shapelen = len(self.shape)
        while not frame.done():
            slice_driver.jit_merge_point(sig=sig, frame=frame, self=self,
                                         arr=arr,
                                         shapelen=shapelen)
            sig.eval(frame, arr)
            frame.next(shapelen)

    def copy(self, space):
        array = W_NDimArray(self.size, self.shape[:], self.dtype, self.order)
        array.setslice(space, self)
        return array

    def flatten(self, space):
        array = W_NDimArray(self.size, [self.size], self.dtype, self.order)
        if self.supports_fast_slicing():
            array._fast_setslice(space, self)
        else:
            arr = SliceArray(array.shape, array.dtype, array, self, no_broadcast=True)
            array._sliceloop(arr)
        return array

    def fill(self, space, w_value):
        self.setslice(space, scalar_w(space, self.dtype, w_value))


class ViewArray(ConcreteArray):
    def create_sig(self):
        return signature.ViewSignature(self.dtype)


class W_NDimSlice(ViewArray):
    def __init__(self, start, strides, backstrides, shape, parent):
        assert isinstance(parent, ConcreteArray)
        if isinstance(parent, W_NDimSlice):
            parent = parent.parent
        size = 1
        for sh in shape:
            size *= sh
        self.strides = strides
        self.backstrides = backstrides
        ViewArray.__init__(self, size, shape, parent.dtype, parent.order,
                               parent)
        self.start = start

    def create_iter(self):
        return ViewIterator(self.start, self.strides, self.backstrides,
                            self.shape)

    def setshape(self, space, new_shape):
        if len(self.shape) < 1:
            return
        elif len(self.shape) < 2:
            # TODO: this code could be refactored into calc_strides
            # but then calc_strides would have to accept a stepping factor
            strides = []
            backstrides = []
            s = self.strides[0]
            if self.order == 'C':
                new_shape.reverse()
            for sh in new_shape:
                strides.append(s)
                backstrides.append(s * (sh - 1))
                s *= sh
            if self.order == 'C':
                strides.reverse()
                backstrides.reverse()
                new_shape.reverse()
            self.strides = strides
            self.backstrides = backstrides
            self.shape = new_shape
            return
        new_strides = calc_new_strides(new_shape, self.shape, self.strides)
        if new_strides is None:
            raise OperationError(space.w_AttributeError, space.wrap(
                          "incompatible shape for a non-contiguous array"))
        new_backstrides = [0] * len(new_shape)
        for nd in range(len(new_shape)):
            new_backstrides[nd] = (new_shape[nd] - 1) * new_strides[nd]
        self.strides = new_strides[:]
        self.backstrides = new_backstrides
        self.shape = new_shape[:]

class W_NDimArray(ConcreteArray):
    """ A class representing contiguous array. We know that each iteration
    by say ufunc will increase the data index by one
    """
    def setitem(self, item, value):
        self.invalidated()
        self.dtype.setitem(self.storage, item, value)

    def setshape(self, space, new_shape):
        self.shape = new_shape
        self.calc_strides(new_shape)

    def create_iter(self):
        return ArrayIterator(self.size)

    def create_sig(self):
        return signature.ArraySignature(self.dtype)

    def __del__(self):
        lltype.free(self.storage, flavor='raw', track_allocation=False)

def _find_size_and_shape(space, w_size):
    if space.isinstance_w(w_size, space.w_int):
        size = space.int_w(w_size)
        shape = [size]
    else:
        size = 1
        shape = []
        for w_item in space.fixedview(w_size):
            item = space.int_w(w_item)
            size *= item
            shape.append(item)
    return size, shape

@unwrap_spec(subok=bool, copy=bool, ownmaskna=bool)
def array(space, w_item_or_iterable, w_dtype=None, w_order=None,
          subok=True, copy=True, w_maskna=None, ownmaskna=False):
    # find scalar
    if w_maskna is None:
        w_maskna = space.w_None
    if (not subok or not space.is_w(w_maskna, space.w_None) or
        ownmaskna):
        raise OperationError(space.w_NotImplementedError, space.wrap("Unsupported args"))
    if not space.issequence_w(w_item_or_iterable):
        if space.is_w(w_dtype, space.w_None):
            w_dtype = interp_ufuncs.find_dtype_for_scalar(space,
                                                          w_item_or_iterable)
        dtype = space.interp_w(interp_dtype.W_Dtype,
            space.call_function(space.gettypefor(interp_dtype.W_Dtype), w_dtype)
        )
        return scalar_w(space, dtype, w_item_or_iterable)
    if space.is_w(w_order, space.w_None) or w_order is None:
        order = 'C'
    else:
        order = space.str_w(w_order)
        if order != 'C':  # or order != 'F':
            raise operationerrfmt(space.w_ValueError, "Unknown order: %s",
                                  order)
    if isinstance(w_item_or_iterable, BaseArray):
        if (not space.is_w(w_dtype, space.w_None) and
            w_item_or_iterable.find_dtype() is not w_dtype):
            raise OperationError(space.w_NotImplementedError, space.wrap(
                "copying over different dtypes unsupported"))
        if copy:
            return w_item_or_iterable.copy(space)
        return w_item_or_iterable
    shape, elems_w = find_shape_and_elems(space, w_item_or_iterable)
    # they come back in C order
    size = len(elems_w)
    if space.is_w(w_dtype, space.w_None):
        w_dtype = None
        for w_elem in elems_w:
            w_dtype = interp_ufuncs.find_dtype_for_scalar(space, w_elem,
                                                          w_dtype)
            if w_dtype is interp_dtype.get_dtype_cache(space).w_float64dtype:
                break
    if w_dtype is None:
        w_dtype = space.w_None
    dtype = space.interp_w(interp_dtype.W_Dtype,
        space.call_function(space.gettypefor(interp_dtype.W_Dtype), w_dtype)
    )
    arr = W_NDimArray(size, shape[:], dtype=dtype, order=order)
    shapelen = len(shape)
    arr_iter = ArrayIterator(arr.size)
    # XXX we might want to have a jitdriver here
    for i in range(len(elems_w)):
        w_elem = elems_w[i]
        dtype.setitem(arr.storage, arr_iter.offset,
                      dtype.coerce(space, w_elem))
        arr_iter = arr_iter.next(shapelen)
    return arr

def zeros(space, w_size, w_dtype=None):
    dtype = space.interp_w(interp_dtype.W_Dtype,
        space.call_function(space.gettypefor(interp_dtype.W_Dtype), w_dtype)
    )
    size, shape = _find_size_and_shape(space, w_size)
    return space.wrap(W_NDimArray(size, shape[:], dtype=dtype))

def ones(space, w_size, w_dtype=None):
    dtype = space.interp_w(interp_dtype.W_Dtype,
        space.call_function(space.gettypefor(interp_dtype.W_Dtype), w_dtype)
    )

    size, shape = _find_size_and_shape(space, w_size)
    arr = W_NDimArray(size, shape[:], dtype=dtype)
    one = dtype.box(1)
    arr.dtype.fill(arr.storage, one, 0, size)
    return space.wrap(arr)

@unwrap_spec(arr=BaseArray, skipna=bool, keepdims=bool)
def count_reduce_items(space, arr, w_axis=None, skipna=False, keepdims=True):
    if not keepdims:
        raise OperationError(space.w_NotImplementedError, space.wrap("unsupported"))
    if space.is_w(w_axis, space.w_None):
        s = 1
        for elem in arr.shape:
            s *= elem
        return space.wrap(s)
    if space.isinstance_w(w_axis, space.w_int):
        return space.wrap(arr.shape[space.int_w(w_axis)])
    s = 1
    elems = space.fixedview(w_axis)
    for w_elem in elems:
        s *= arr.shape[space.int_w(w_elem)]
    return space.wrap(s)

def dot(space, w_obj, w_obj2):
    w_arr = convert_to_array(space, w_obj)
    if isinstance(w_arr, Scalar):
        return convert_to_array(space, w_obj2).descr_dot(space, w_arr)
    return w_arr.descr_dot(space, w_obj2)

BaseArray.typedef = TypeDef(
    'ndarray',
    __module__ = "numpypy",
    __new__ = interp2app(BaseArray.descr__new__.im_func),

    __len__ = interp2app(BaseArray.descr_len),
    __getitem__ = interp2app(BaseArray.descr_getitem),
    __setitem__ = interp2app(BaseArray.descr_setitem),

    __pos__ = interp2app(BaseArray.descr_pos),
    __neg__ = interp2app(BaseArray.descr_neg),
    __abs__ = interp2app(BaseArray.descr_abs),
    __nonzero__ = interp2app(BaseArray.descr_nonzero),

    __add__ = interp2app(BaseArray.descr_add),
    __sub__ = interp2app(BaseArray.descr_sub),
    __mul__ = interp2app(BaseArray.descr_mul),
    __div__ = interp2app(BaseArray.descr_div),
    __pow__ = interp2app(BaseArray.descr_pow),
    __mod__ = interp2app(BaseArray.descr_mod),

    __radd__ = interp2app(BaseArray.descr_radd),
    __rsub__ = interp2app(BaseArray.descr_rsub),
    __rmul__ = interp2app(BaseArray.descr_rmul),
    __rdiv__ = interp2app(BaseArray.descr_rdiv),
    __rpow__ = interp2app(BaseArray.descr_rpow),
    __rmod__ = interp2app(BaseArray.descr_rmod),

    __eq__ = interp2app(BaseArray.descr_eq),
    __ne__ = interp2app(BaseArray.descr_ne),
    __lt__ = interp2app(BaseArray.descr_lt),
    __le__ = interp2app(BaseArray.descr_le),
    __gt__ = interp2app(BaseArray.descr_gt),
    __ge__ = interp2app(BaseArray.descr_ge),

    __and__ = interp2app(BaseArray.descr_and),
    __or__ = interp2app(BaseArray.descr_or),

    __repr__ = interp2app(BaseArray.descr_repr),
    __str__ = interp2app(BaseArray.descr_str),
    __array_interface__ = GetSetProperty(BaseArray.descr_array_iface),

    dtype = GetSetProperty(BaseArray.descr_get_dtype),
    shape = GetSetProperty(BaseArray.descr_get_shape,
                           BaseArray.descr_set_shape),
    size = GetSetProperty(BaseArray.descr_get_size),
    ndim = GetSetProperty(BaseArray.descr_get_ndim),

    T = GetSetProperty(BaseArray.descr_get_transpose),
    flat = GetSetProperty(BaseArray.descr_get_flatiter),

    mean = interp2app(BaseArray.descr_mean),
    sum = interp2app(BaseArray.descr_sum),
    prod = interp2app(BaseArray.descr_prod),
    max = interp2app(BaseArray.descr_max),
    min = interp2app(BaseArray.descr_min),
    argmax = interp2app(BaseArray.descr_argmax),
    argmin = interp2app(BaseArray.descr_argmin),
    all = interp2app(BaseArray.descr_all),
    any = interp2app(BaseArray.descr_any),
    dot = interp2app(BaseArray.descr_dot),
    var = interp2app(BaseArray.descr_var),
    std = interp2app(BaseArray.descr_std),

    fill = interp2app(BaseArray.descr_fill),

    copy = interp2app(BaseArray.descr_copy),
    flatten = interp2app(BaseArray.descr_flatten),
    reshape = interp2app(BaseArray.descr_reshape),
    tolist = interp2app(BaseArray.descr_tolist),
)


class W_FlatIterator(ViewArray):

    @jit.unroll_safe
    def __init__(self, arr):
        arr = arr.get_concrete()
        size = 1
        for sh in arr.shape:
            size *= sh
        self.strides = [arr.strides[-1]]
        self.backstrides = [arr.backstrides[-1]]
        ViewArray.__init__(self, size, [size], arr.dtype, arr.order,
                               arr)
        self.shapelen = len(arr.shape)
        self.iter = OneDimIterator(arr.start, self.strides[0],
                                   self.shape[0])

    def descr_next(self, space):
        if self.iter.done():
            raise OperationError(space.w_StopIteration, space.w_None)
        result = self.getitem(self.iter.offset)
        self.iter = self.iter.next(self.shapelen)
        return result

    def descr_iter(self):
        return self

W_FlatIterator.typedef = TypeDef(
    'flatiter',
    next = interp2app(W_FlatIterator.descr_next),
    __iter__ = interp2app(W_FlatIterator.descr_iter),
)
W_FlatIterator.acceptable_as_base_class = False
