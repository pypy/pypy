from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.module.micronumpy.interp_support import Signature
from pypy.module.micronumpy import interp_ufuncs
from pypy.objspace.std.floatobject import float2string as float2string_orig
from pypy.rlib import jit
from pypy.rlib.rfloat import DTSF_STR_PRECISION
from pypy.rpython.lltypesystem import lltype
from pypy.tool.sourcetools import func_with_new_name
import math

TP = lltype.Array(lltype.Float, hints={'nolength': True})

numpy_driver = jit.JitDriver(greens = ['signature'],
                             reds = ['result_size', 'i', 'self', 'result'])
all_driver = jit.JitDriver(greens=['signature'], reds=['i', 'size', 'self'])
any_driver = jit.JitDriver(greens=['signature'], reds=['i', 'size', 'self'])
slice_driver1 = jit.JitDriver(greens=['signature'], reds=['i', 'j', 'step', 'stop', 'source', 'dest'])
slice_driver2 = jit.JitDriver(greens=['signature'], reds=['i', 'j', 'step', 'stop', 'source', 'dest'])

def add(v1, v2):
    return v1 + v2
def mul(v1, v2):
    return v1 * v2
def maximum(v1, v2):
    return max(v1, v2)
def minimum(v1, v2):
    return min(v1, v2)

def float2string(x):
    return float2string_orig(x, 'g', DTSF_STR_PRECISION)

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
            w_other = FloatWrapper(space.float_w(w_other))
            return w_ufunc(space, w_other, self)
        return func_with_new_name(impl, "binop_right_%s_impl" % w_ufunc.__name__)

    descr_radd = _binop_right_impl(interp_ufuncs.add)
    descr_rsub = _binop_right_impl(interp_ufuncs.subtract)
    descr_rmul = _binop_right_impl(interp_ufuncs.multiply)
    descr_rdiv = _binop_right_impl(interp_ufuncs.divide)
    descr_rpow = _binop_right_impl(interp_ufuncs.power)
    descr_rmod = _binop_right_impl(interp_ufuncs.mod)

    def _reduce_sum_prod_impl(function, init):
        reduce_driver = jit.JitDriver(greens=['signature'],
                         reds = ['i', 'size', 'self', 'result'])

        def loop(self, result, size):
            i = 0
            while i < size:
                reduce_driver.jit_merge_point(signature=self.signature,
                                              self=self, size=size, i=i,
                                              result=result)
                result = function(result, self.eval(i))
                i += 1
            return result

        def impl(self, space):
            return space.wrap(loop(self, init, self.find_size()))
        return func_with_new_name(impl, "reduce_%s_impl" % function.__name__)

    def _reduce_max_min_impl(function):
        reduce_driver = jit.JitDriver(greens=['signature'],
                         reds = ['i', 'size', 'self', 'result'])
        def loop(self, result, size):
            i = 1
            while i < size:
                reduce_driver.jit_merge_point(signature=self.signature,
                                              self=self, size=size, i=i,
                                              result=result)
                result = function(result, self.eval(i))
                i += 1
            return result

        def impl(self, space):
            size = self.find_size()
            if size == 0:
                raise OperationError(space.w_ValueError,
                    space.wrap("Can't call %s on zero-size arrays" \
                            % function.__name__))
            return space.wrap(loop(self, self.eval(0), size))
        return func_with_new_name(impl, "reduce_%s_impl" % function.__name__)

    def _reduce_argmax_argmin_impl(function):
        reduce_driver = jit.JitDriver(greens=['signature'],
                         reds = ['i', 'size', 'result', 'self', 'cur_best'])
        def loop(self, size):
            result = 0
            cur_best = self.eval(0)
            i = 1
            while i < size:
                reduce_driver.jit_merge_point(signature=self.signature,
                                              self=self, size=size, i=i,
                                              result=result, cur_best=cur_best)
                new_best = function(cur_best, self.eval(i))
                if new_best != cur_best:
                    result = i
                    cur_best = new_best
                i += 1
            return result
        def impl(self, space):
            size = self.find_size()
            if size == 0:
                raise OperationError(space.w_ValueError,
                    space.wrap("Can't call %s on zero-size arrays" \
                            % function.__name__))
            return space.wrap(loop(self, size))
        return func_with_new_name(impl, "reduce_arg%s_impl" % function.__name__)

    def _all(self):
        size = self.find_size()
        i = 0
        while i < size:
            all_driver.jit_merge_point(signature=self.signature, self=self, size=size, i=i)
            if not self.eval(i):
                return False
            i += 1
        return True
    def descr_all(self, space):
        return space.wrap(self._all())

    def _any(self):
        size = self.find_size()
        i = 0
        while i < size:
            any_driver.jit_merge_point(signature=self.signature, self=self, size=size, i=i)
            if self.eval(i):
                return True
            i += 1
        return False
    def descr_any(self, space):
        return space.wrap(self._any())

    descr_sum = _reduce_sum_prod_impl(add, 0.0)
    descr_prod = _reduce_sum_prod_impl(mul, 1.0)
    descr_max = _reduce_max_min_impl(maximum)
    descr_min = _reduce_max_min_impl(minimum)
    descr_argmax = _reduce_argmax_argmin_impl(maximum)
    descr_argmin = _reduce_argmax_argmin_impl(minimum)

    def descr_sort(self, space):
        size = self.find_size()
        stack = [(0,size-1)]
        first=0; last=size-1; splitpoint=first;
        while (len(stack) > 0):
            first, last = stack.pop()
            while last>first:
                #splitpoint = split(first,last)
                x = self.eval(first)
                splitpoint = first
                unknown = first+1
                while (unknown<=last):
                    if (self.eval(unknown)<x):
                        splitpoint = splitpoint + 1
                        #interchange(splitpoint,unknown)
                        temp = self.eval(splitpoint)
                        self.storage[splitpoint] = self.eval(unknown)
                        self.storage[unknown] = temp
                    unknown = unknown + 1
                #interchange(first,splitpoint)
                temp = self.eval(splitpoint)
                self.storage[splitpoint] = self.eval(first)
                self.storage[first] = temp

                if (last-splitpoint<splitpoint-first):
                    stack.append((first,splitpoint-1));
                    first = splitpoint + 1
                else:
                    stack.append((splitpoint+1,last));
                    last = splitpoint - 1


    def descr_dot(self, space, w_other):
        if isinstance(w_other, BaseArray):
            w_res = self.descr_mul(space, w_other)
            assert isinstance(w_res, BaseArray)
            return w_res.descr_sum(space)
        else:
            return self.descr_mul(space, w_other)

    def _getnums(self, comma):
        if self.find_size() > 1000:
            nums = [
                float2string(self.eval(index))
                for index in range(3)
            ]
            nums.append("..." + "," * comma)
            nums.extend([
                float2string(self.eval(index))
                for index in range(self.find_size() - 3, self.find_size())
            ])
        else:
            nums = [
                float2string(self.eval(index))
                for index in range(self.find_size())
            ]
        return nums

    def get_concrete(self):
        raise NotImplementedError

    def descr_copy(self, space):
        return new_numarray(space, self)

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
            return space.wrap(self.get_concrete().eval(start))
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
            self.get_concrete().setitem(start, space.float_w(w_value))
        else:
            concrete = self.get_concrete()
            if isinstance(w_value, BaseArray):
                # for now we just copy if setting part of an array from 
                # part of itself. can be improved.
                if (concrete.get_root_storage() ==
                    w_value.get_concrete().get_root_storage()):
                    w_value = new_numarray(space, w_value)
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
            dest.storage[i] = source.eval(j)
            j += 1
            i += step

    def _sliceloop2(self, start, stop, step, source, dest):
        i = start
        j = 0
        while i > stop:
            slice_driver2.jit_merge_point(signature=source.signature,
                    step=step, stop=stop, i=i, j=j, source=source,
                    dest=dest)
            dest.storage[i] = source.eval(j)
            j += 1
            i += step

def convert_to_array (space, w_obj):
    if isinstance(w_obj, BaseArray):
        return w_obj
    elif space.issequence_w(w_obj):
        # Convert to array.
        return new_numarray(space, w_obj)
    else:
        # If it's a scalar
        return FloatWrapper(space.float_w(w_obj))

class FloatWrapper(BaseArray):
    """
    Intermediate class representing a float literal.
    """
    signature = Signature()

    def __init__(self, float_value):
        BaseArray.__init__(self)
        self.float_value = float_value

    def find_size(self):
        raise ValueError

    def eval(self, i):
        return self.float_value

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
        result = SingleDimArray(result_size)
        while i < result_size:
            numpy_driver.jit_merge_point(signature=signature,
                                         result_size=result_size, i=i,
                                         self=self, result=result)
            result.storage[i] = self.eval(i)
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


class Call1(VirtualArray):
    def __init__(self, function, values, signature):
        VirtualArray.__init__(self, signature)
        self.function = function
        self.values = values

    def _del_sources(self):
        self.values = None

    def _find_size(self):
        return self.values.find_size()

    def _eval(self, i):
        return self.function(self.values.eval(i))

class Call2(VirtualArray):
    """
    Intermediate class for performing binary operations.
    """
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
        lhs, rhs = self.left.eval(i), self.right.eval(i)
        return self.function(lhs, rhs)

class ViewArray(BaseArray):
    """
    Class for representing views of arrays, they will reflect changes of parent
    arrays. Example: slices
    """
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

    @unwrap_spec(item=int, value=float)
    def setitem(self, item, value):
        return self.parent.setitem(self.calc_index(item), value)

    def descr_len(self, space):
        return space.wrap(self.find_size())

    def calc_index(self, item):
        raise NotImplementedError

class SingleDimSlice(ViewArray):
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

    def __init__(self, size):
        BaseArray.__init__(self)
        self.size = size
        self.storage = lltype.malloc(TP, size, zero=True,
                                     flavor='raw', track_allocation=False,
                                     add_memory_pressure=True)
        # XXX find out why test_zjit explodes with trackign of allocations

    def get_concrete(self):
        return self

    def get_root_storage(self):
        return self.storage

    def find_size(self):
        return self.size

    def eval(self, i):
        return self.storage[i]

    def descr_len(self, space):
        return space.wrap(self.size)

    def setitem(self, item, value):
        self.invalidated()
        self.storage[item] = value

    def setslice(self, space, start, stop, step, slice_length, arr):
        if step > 0:
            self._sliceloop1(start, stop, step, arr, self)
        else:
            self._sliceloop2(start, stop, step, arr, self)

    def __del__(self):
        lltype.free(self.storage, flavor='raw', track_allocation=False)

def new_numarray(space, w_size_or_iterable):
    l = space.listview(w_size_or_iterable)
    arr = SingleDimArray(len(l))
    i = 0
    for w_elem in l:
        arr.storage[i] = space.float_w(space.float(w_elem))
        i += 1
    return arr

def descr_new_numarray(space, w_type, w_size_or_iterable):
    return space.wrap(new_numarray(space, w_size_or_iterable))

@unwrap_spec(size=int)
def zeros(space, size):
    return space.wrap(SingleDimArray(size))

@unwrap_spec(size=int)
def ones(space, size):
    arr = SingleDimArray(size)
    for i in xrange(size):
        arr.storage[i] = 1.0
    return space.wrap(arr)

BaseArray.typedef = TypeDef(
    'numarray',
    __new__ = interp2app(descr_new_numarray),

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
    sort = interp2app(BaseArray.descr_sort),
)
