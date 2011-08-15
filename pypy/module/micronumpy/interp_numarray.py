import math

from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import interp2app, unwrap_spec, NoneNotWrapped
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.module.micronumpy import interp_ufuncs, interp_dtype
from pypy.module.micronumpy.interp_support import Signature
from pypy.rlib import jit
from pypy.rlib.objectmodel import specialize
from pypy.rlib.rfloat import DTSF_STR_PRECISION
from pypy.rpython.lltypesystem import lltype
from pypy.tool.sourcetools import func_with_new_name


numpy_driver = jit.JitDriver(greens = ['signature'],
                             reds = ['result_size', 'i', 'self', 'result'])
all_driver = jit.JitDriver(greens=['signature'], reds=['i', 'size', 'self'])
any_driver = jit.JitDriver(greens=['signature'], reds=['i', 'size', 'self'])
slice_driver1 = jit.JitDriver(greens=['signature'], reds=['i', 'j', 'step', 'stop', 'source', 'dest'])
slice_driver2 = jit.JitDriver(greens=['signature'], reds=['i', 'j', 'step', 'stop', 'source', 'dest'])

class BaseArray(Wrappable):
    def __init__(self):
        self.invalidates = []

    def invalidated(self):
        if self.invalidates:
            self._invalidated()

    def _invalidated(self):
        for arr in self.invalidates:
            arr.force_if_needed()
        del self.invalidates[:]

    def descr__new__(space, w_subtype, w_size_or_iterable, w_dtype=NoneNotWrapped):
        if w_dtype is None:
            w_dtype = space.w_float
        dtype = space.interp_w(interp_dtype.W_Dtype,
            space.call_function(space.gettypefor(interp_dtype.W_Dtype), w_dtype)
        )
        l = space.listview(w_size_or_iterable)
        arr = SingleDimArray(len(l), dtype=dtype)
        i = 0
        for w_elem in l:
            dtype.setitem_w(space, arr.storage, i, w_elem)
            i += 1
        return arr

    def _unaryop_impl(w_ufunc):
        def impl(self, space):
            return w_ufunc(space, self)
        return func_with_new_name(impl, "unaryop_%s_impl" % w_ufunc.__name__)

    descr_pos = _unaryop_impl(interp_ufuncs.positive)
    descr_neg = _unaryop_impl(interp_ufuncs.negative)
    descr_abs = _unaryop_impl(interp_ufuncs.absolute)

    def _binop_impl(w_ufunc):
        def impl(self, space, w_other):
            return w_ufunc(space, self, w_other)
        return func_with_new_name(impl, "binop_%s_impl" % w_ufunc.__name__)

    descr_add = _binop_impl(interp_ufuncs.add)
    descr_sub = _binop_impl(interp_ufuncs.subtract)
    descr_mul = _binop_impl(interp_ufuncs.multiply)
    descr_div = _binop_impl(interp_ufuncs.divide)
    descr_pow = _binop_impl(interp_ufuncs.power)
    descr_mod = _binop_impl(interp_ufuncs.mod)

    def _binop_right_impl(w_ufunc):
        def impl(self, space, w_other):
            w_other = scalar_w(space, interp_dtype.W_Float64Dtype, w_other)
            return w_ufunc(space, w_other, self)
        return func_with_new_name(impl, "binop_right_%s_impl" % w_ufunc.__name__)

    descr_radd = _binop_right_impl(interp_ufuncs.add)
    descr_rsub = _binop_right_impl(interp_ufuncs.subtract)
    descr_rmul = _binop_right_impl(interp_ufuncs.multiply)
    descr_rdiv = _binop_right_impl(interp_ufuncs.divide)
    descr_rpow = _binop_right_impl(interp_ufuncs.power)
    descr_rmod = _binop_right_impl(interp_ufuncs.mod)

    def _reduce_sum_prod_impl(op_name, init):
        reduce_driver = jit.JitDriver(greens=['signature'],
                         reds = ['i', 'size', 'self', 'result'])

        def loop(self, res_dtype, result, size):
            i = 0
            while i < size:
                reduce_driver.jit_merge_point(signature=self.signature,
                                              self=self, size=size, i=i,
                                              result=result)
                result = getattr(res_dtype, op_name)(result, self.eval(i))
                i += 1
            return result

        def impl(self, space):
            result = space.fromcache(interp_dtype.W_Float64Dtype).Box(init).convert_to(self.find_dtype())
            return loop(self, self.find_dtype(), result, self.find_size()).wrap(space)
        return func_with_new_name(impl, "reduce_%s_impl" % op_name)

    def _reduce_max_min_impl(op_name):
        reduce_driver = jit.JitDriver(greens=['signature'],
                         reds = ['i', 'size', 'self', 'result'])
        def loop(self, result, size):
            i = 1
            dtype = self.find_dtype()
            while i < size:
                reduce_driver.jit_merge_point(signature=self.signature,
                                              self=self, size=size, i=i,
                                              result=result)
                result = getattr(dtype, op_name)(result, self.eval(i))
                i += 1
            return result

        def impl(self, space):
            size = self.find_size()
            if size == 0:
                raise OperationError(space.w_ValueError,
                    space.wrap("Can't call %s on zero-size arrays" \
                            % op_name))
            return loop(self, self.eval(0), size).wrap(space)
        return func_with_new_name(impl, "reduce_%s_impl" % op_name)

    def _reduce_argmax_argmin_impl(op_name):
        reduce_driver = jit.JitDriver(greens=['signature'],
                         reds = ['i', 'size', 'result', 'self', 'cur_best'])
        def loop(self, size):
            result = 0
            cur_best = self.eval(0)
            i = 1
            dtype = self.find_dtype()
            while i < size:
                reduce_driver.jit_merge_point(signature=self.signature,
                                              self=self, size=size, i=i,
                                              result=result, cur_best=cur_best)
                new_best = getattr(dtype, op_name)(cur_best, self.eval(i))
                if dtype.ne(new_best, cur_best):
                    result = i
                    cur_best = new_best
                i += 1
            return result
        def impl(self, space):
            size = self.find_size()
            if size == 0:
                raise OperationError(space.w_ValueError,
                    space.wrap("Can't call %s on zero-size arrays" \
                            % op_name))
            return space.wrap(loop(self, size))
        return func_with_new_name(impl, "reduce_arg%s_impl" % op_name)

    def _all(self):
        size = self.find_size()
        dtype = self.find_dtype()
        i = 0
        while i < size:
            all_driver.jit_merge_point(signature=self.signature, self=self, size=size, i=i)
            if not dtype.bool(self.eval(i)):
                return False
            i += 1
        return True
    def descr_all(self, space):
        return space.wrap(self._all())

    def _any(self):
        size = self.find_size()
        dtype = self.find_dtype()
        i = 0
        while i < size:
            any_driver.jit_merge_point(signature=self.signature, self=self, size=size, i=i)
            if dtype.bool(self.eval(i)):
                return True
            i += 1
        return False
    def descr_any(self, space):
        return space.wrap(self._any())

    descr_sum = _reduce_sum_prod_impl("add", 0.0)
    descr_prod = _reduce_sum_prod_impl("mul", 1.0)
    descr_max = _reduce_max_min_impl("max")
    descr_min = _reduce_max_min_impl("min")
    descr_argmax = _reduce_argmax_argmin_impl("max")
    descr_argmin = _reduce_argmax_argmin_impl("min")

    def descr_dot(self, space, w_other):
        if isinstance(w_other, BaseArray):
            w_res = self.descr_mul(space, w_other)
            assert isinstance(w_res, BaseArray)
            return w_res.descr_sum(space)
        else:
            return self.descr_mul(space, w_other)

    def _getnums(self, comma):
        dtype = self.find_dtype()
        if self.find_size() > 1000:
            nums = [
                dtype.str_format(self.eval(index))
                for index in range(3)
            ]
            nums.append("..." + "," * comma)
            nums.extend([
                dtype.str_format(self.eval(index))
                for index in range(self.find_size() - 3, self.find_size())
            ])
        else:
            nums = [
                dtype.str_format(self.eval(index))
                for index in range(self.find_size())
            ]
        return nums

    def get_concrete(self):
        raise NotImplementedError

    def descr_copy(self, space):
        return space.call_function(space.gettypefor(BaseArray), self)

    def descr_get_shape(self, space):
        return space.newtuple([self.descr_len(space)])

    def descr_len(self, space):
        return self.get_concrete().descr_len(space)

    def descr_repr(self, space):
        # Simple implementation so that we can see the array. Needs work.
        concrete = self.get_concrete()
        return space.wrap("array([" + ", ".join(concrete._getnums(False)) + "])")

    def descr_str(self, space):
        # Simple implementation so that we can see the array. Needs work.
        concrete = self.get_concrete()
        return space.wrap("[" + " ".join(concrete._getnums(True)) + "]")

    def descr_getitem(self, space, w_idx):
        # TODO: indexing by tuples
        start, stop, step, slice_length = space.decode_index4(w_idx, self.find_size())
        if step == 0:
            # Single index
            return self.get_concrete().eval(start).wrap(space)
        else:
            # Slice
            res = SingleDimSlice(start, stop, step, slice_length, self, self.signature.transition(SingleDimSlice.static_signature))
            return space.wrap(res)

    def descr_setitem(self, space, w_idx, w_value):
        # TODO: indexing by tuples and lists
        self.invalidated()
        start, stop, step, slice_length = space.decode_index4(w_idx,
                                                              self.find_size())
        if step == 0:
            # Single index
            self.get_concrete().setitem(space, start, w_value)
        else:
            concrete = self.get_concrete()
            if isinstance(w_value, BaseArray):
                # for now we just copy if setting part of an array from
                # part of itself. can be improved.
                if (concrete.get_root_storage() ==
                    w_value.get_concrete().get_root_storage()):
                    w_value = space.call_function(space.gettypefor(BaseArray), w_value)
            else:
                w_value = convert_to_array(space, w_value)
            concrete.setslice(space, start, stop, step,
                                               slice_length, w_value)

    def descr_mean(self, space):
        return space.wrap(space.float_w(self.descr_sum(space))/self.find_size())

    def _sliceloop1(self, start, stop, step, source, dest):
        i = start
        j = 0
        while i < stop:
            slice_driver1.jit_merge_point(signature=source.signature,
                    step=step, stop=stop, i=i, j=j, source=source,
                    dest=dest)
            dest.dtype.setitem(dest.storage, i, source.eval(j))
            j += 1
            i += step

    def _sliceloop2(self, start, stop, step, source, dest):
        i = start
        j = 0
        while i > stop:
            slice_driver2.jit_merge_point(signature=source.signature,
                    step=step, stop=stop, i=i, j=j, source=source,
                    dest=dest)
            dest.dtype.setitem(dest.storage, i, source.eval(j))
            j += 1
            i += step

def convert_to_array (space, w_obj):
    if isinstance(w_obj, BaseArray):
        return w_obj
    elif space.issequence_w(w_obj):
        # Convert to array.
        w_obj = space.call_function(space.gettypefor(BaseArray), w_obj)
        assert isinstance(w_obj, BaseArray)
        return w_obj
    else:
        # If it's a scalar
        return scalar_w(space, interp_dtype.W_Float64Dtype, w_obj)

@specialize.arg(1)
def scalar_w(space, dtype, w_obj):
    return Scalar(scalar(space, dtype, w_obj))

@specialize.arg(1)
def scalar(space, dtype, w_obj):
    dtype = space.fromcache(dtype)
    return dtype.unwrap(space, w_obj)

class Scalar(BaseArray):
    """
    Intermediate class representing a float literal.
    """
    _immutable_fields_ = ["value"]
    signature = Signature()

    def __init__(self, value):
        BaseArray.__init__(self)
        self.value = value

    def find_size(self):
        raise ValueError

    def find_dtype(self):
        raise ValueError

    def eval(self, i):
        return self.value

class VirtualArray(BaseArray):
    """
    Class for representing virtual arrays, such as binary ops or ufuncs
    """
    def __init__(self, signature):
        BaseArray.__init__(self)
        self.forced_result = None
        self.signature = signature

    def _del_sources(self):
        # Function for deleting references to source arrays, to allow garbage-collecting them
        raise NotImplementedError

    def compute(self):
        i = 0
        signature = self.signature
        result_size = self.find_size()
        result = SingleDimArray(result_size, self.find_dtype())
        while i < result_size:
            numpy_driver.jit_merge_point(signature=signature,
                                         result_size=result_size, i=i,
                                         self=self, result=result)
            result.dtype.setitem(result.storage, i, self.eval(i))
            i += 1
        return result

    def force_if_needed(self):
        if self.forced_result is None:
            self.forced_result = self.compute()
            self._del_sources()

    def get_concrete(self):
        self.force_if_needed()
        return self.forced_result

    def eval(self, i):
        if self.forced_result is not None:
            return self.forced_result.eval(i)
        return self._eval(i)

    def find_size(self):
        if self.forced_result is not None:
            # The result has been computed and sources may be unavailable
            return self.forced_result.find_size()
        return self._find_size()

    def find_dtype(self):
        if self.forced_result is not None:
            return self.forced_result.find_dtype()
        return self._find_dtype()


class Call1(VirtualArray):
    _immutable_fields_ = ["function", "values"]

    def __init__(self, function, values, signature):
        VirtualArray.__init__(self, signature)
        self.function = function
        self.values = values

    def _del_sources(self):
        self.values = None

    def _find_size(self):
        return self.values.find_size()

    def _find_dtype(self):
        return self.values.find_dtype()

    def _eval(self, i):
        return self.function(self.find_dtype(), self.values.eval(i))

class Call2(VirtualArray):
    """
    Intermediate class for performing binary operations.
    """
    _immutable_fields_ = ["function", "left", "right"]

    def __init__(self, function, left, right, signature):
        VirtualArray.__init__(self, signature)
        self.function = function
        self.left = left
        self.right = right

    def _del_sources(self):
        self.left = None
        self.right = None

    def _find_size(self):
        try:
            return self.left.find_size()
        except ValueError:
            pass
        return self.right.find_size()

    def _eval(self, i):
        dtype = self.find_dtype()
        lhs, rhs = self.left.eval(i), self.right.eval(i)
        lhs, rhs = lhs.convert_to(dtype), rhs.convert_to(dtype)
        return self.function(dtype, lhs, rhs)

    def _find_dtype(self):
        lhs_dtype = None
        rhs_dtype = None
        try:
            lhs_dtype = self.left.find_dtype()
        except ValueError:
            pass
        try:
            rhs_dtype = self.right.find_dtype()
        except ValueError:
            pass
        if lhs_dtype is not None and rhs_dtype is not None:
            assert lhs_dtype is rhs_dtype
            return lhs_dtype
        elif lhs_dtype is not None:
            return lhs_dtype
        elif rhs_dtype is not None:
            return rhs_dtype
        else:
            raise ValueError

class ViewArray(BaseArray):
    """
    Class for representing views of arrays, they will reflect changes of parent
    arrays. Example: slices
    """
    _immutable_fields_ = ["parent"]

    def __init__(self, parent, signature):
        BaseArray.__init__(self)
        self.signature = signature
        self.parent = parent
        self.invalidates = parent.invalidates

    def get_concrete(self):
        # in fact, ViewArray never gets "concrete" as it never stores data.
        # This implementation is needed for BaseArray getitem/setitem to work,
        # can be refactored.
        self.parent.get_concrete()
        return self

    def eval(self, i):
        return self.parent.eval(self.calc_index(i))

    @unwrap_spec(item=int)
    def setitem(self, space, item, w_value):
        return self.parent.setitem(space, self.calc_index(item), w_value)

    def descr_len(self, space):
        return space.wrap(self.find_size())

    def calc_index(self, item):
        raise NotImplementedError

class SingleDimSlice(ViewArray):
    _immutable_fields_ = ["start", "stop", "step", "size"]
    static_signature = Signature()

    def __init__(self, start, stop, step, slice_length, parent, signature):
        ViewArray.__init__(self, parent, signature)
        if isinstance(parent, SingleDimSlice):
            self.start = parent.calc_index(start)
            self.stop = parent.calc_index(stop)
            self.step = parent.step * step
            self.parent = parent.parent
        else:
            self.start = start
            self.stop = stop
            self.step = step
            self.parent = parent
        self.size = slice_length

    def get_root_storage(self):
        return self.parent.storage

    def find_size(self):
        return self.size

    def find_dtype(self):
        return self.parent.find_dtype()

    def setslice(self, space, start, stop, step, slice_length, arr):
        start = self.calc_index(start)
        if stop != -1:
            stop = self.calc_index(stop)
        step = self.step * step
        if step > 0:
            self._sliceloop1(start, stop, step, arr, self.parent)
        else:
            self._sliceloop2(start, stop, step, arr, self.parent)

    def calc_index(self, item):
        return (self.start + item * self.step)


class SingleDimArray(BaseArray):
    signature = Signature()

    def __init__(self, size, dtype):
        BaseArray.__init__(self)
        self.size = size
        self.dtype = dtype
        self.storage = dtype.malloc(size)

    def get_concrete(self):
        return self

    def get_root_storage(self):
        return self.storage

    def find_size(self):
        return self.size

    def find_dtype(self):
        return self.dtype

    def eval(self, i):
        return self.dtype.getitem(self.storage, i)

    def descr_len(self, space):
        return space.wrap(self.size)

    def setitem(self, space, item, w_value):
        self.invalidated()
        self.dtype.setitem_w(space, self.storage, item, w_value)

    def setslice(self, space, start, stop, step, slice_length, arr):
        if step > 0:
            self._sliceloop1(start, stop, step, arr, self)
        else:
            self._sliceloop2(start, stop, step, arr, self)

    def __del__(self):
        lltype.free(self.storage, flavor='raw', track_allocation=False)

@unwrap_spec(size=int)
def zeros(space, size):
    return space.wrap(SingleDimArray(size, dtype=space.fromcache(interp_dtype.W_Float64Dtype)))

@unwrap_spec(size=int)
def ones(space, size):
    dtype = space.fromcache(interp_dtype.W_Float64Dtype)
    arr = SingleDimArray(size, dtype=dtype)
    one = dtype.Box(1.0)
    for i in xrange(size):
        arr.dtype.setitem(arr.storage, i, one)
    return space.wrap(arr)

BaseArray.typedef = TypeDef(
    'numarray',
    __new__ = interp2app(BaseArray.descr__new__.im_func),

    copy = interp2app(BaseArray.descr_copy),
    shape = GetSetProperty(BaseArray.descr_get_shape),

    __len__ = interp2app(BaseArray.descr_len),
    __getitem__ = interp2app(BaseArray.descr_getitem),
    __setitem__ = interp2app(BaseArray.descr_setitem),

    __pos__ = interp2app(BaseArray.descr_pos),
    __neg__ = interp2app(BaseArray.descr_neg),
    __abs__ = interp2app(BaseArray.descr_abs),
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
    __repr__ = interp2app(BaseArray.descr_repr),
    __str__ = interp2app(BaseArray.descr_str),

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
)
