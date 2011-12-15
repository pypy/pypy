from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import interp2app, unwrap_spec, NoneNotWrapped
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.module.micronumpy import interp_ufuncs, interp_dtype, signature
from pypy.rlib import jit
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.tool.sourcetools import func_with_new_name
from pypy.rlib.rstring import StringBuilder
from pypy.rlib.objectmodel import instantiate


numpy_driver = jit.JitDriver(
    greens=['shapelen', 'signature'],
    reds=['result_size', 'i', 'ri', 'self', 'result']
)
all_driver = jit.JitDriver(
    greens=['shapelen', 'signature'],
    reds=['i', 'self', 'dtype']
)
any_driver = jit.JitDriver(
    greens=['shapelen', 'signature'],
    reds=['i', 'self', 'dtype']
)
slice_driver = jit.JitDriver(
    greens=['shapelen', 'signature'],
    reds=['self', 'source', 'source_iter', 'res_iter']
)

def _find_shape_and_elems(space, w_iterable):
    shape = [space.len_w(w_iterable)]
    batch = space.listview(w_iterable)
    while True:
        new_batch = []
        if not batch:
            return shape, []
        if not space.issequence_w(batch[0]):
            for elem in batch:
                if space.issequence_w(elem):
                    raise OperationError(space.w_ValueError, space.wrap(
                        "setting an array element with a sequence"))
            return shape, batch
        size = space.len_w(batch[0])
        for w_elem in batch:
            if not space.issequence_w(w_elem) or space.len_w(w_elem) != size:
                raise OperationError(space.w_ValueError, space.wrap(
                    "setting an array element with a sequence"))
            new_batch += space.listview(w_elem)
        shape.append(size)
        batch = new_batch

def shape_agreement(space, shape1, shape2):
    ret = _shape_agreement(shape1, shape2)
    if len(ret) < max(len(shape1), len(shape2)):
        raise OperationError(space.w_ValueError,
            space.wrap("operands could not be broadcast together with shapes (%s) (%s)" % (
                ",".join([str(x) for x in shape1]),
                ",".join([str(x) for x in shape2]),
            ))
        )
    return ret

def _shape_agreement(shape1, shape2):
    """ Checks agreement about two shapes with respect to broadcasting. Returns
    the resulting shape.
    """
    lshift = 0
    rshift = 0
    if len(shape1) > len(shape2):
        m = len(shape1)
        n = len(shape2)
        rshift = len(shape2) - len(shape1)
        remainder = shape1
    else:
        m = len(shape2)
        n = len(shape1)
        lshift = len(shape1) - len(shape2)
        remainder = shape2
    endshape = [0] * m
    indices1 = [True] * m
    indices2 = [True] * m
    for i in range(m - 1, m - n - 1, -1):
        left = shape1[i + lshift]
        right = shape2[i + rshift]
        if left == right:
            endshape[i] = left
        elif left == 1:
            endshape[i] = right
            indices1[i + lshift] = False
        elif right == 1:
            endshape[i] = left
            indices2[i + rshift] = False
        else:
            return []
            #raise OperationError(space.w_ValueError, space.wrap(
            #    "frames are not aligned"))
    for i in range(m - n):
        endshape[i] = remainder[i]
    return endshape

def get_shape_from_iterable(space, old_size, w_iterable):
    new_size = 0
    new_shape = []
    if space.isinstance_w(w_iterable, space.w_int):
        new_size = space.int_w(w_iterable)
        if new_size < 0:
            new_size = old_size
        new_shape = [new_size]
    else:
        neg_dim = -1
        batch = space.listview(w_iterable)
        new_size = 1
        if len(batch) < 1:
            if old_size == 1:
                # Scalars can have an empty size.
                new_size = 1
            else:
                new_size = 0
        new_shape = []
        i = 0
        for elem in batch:
            s = space.int_w(elem)
            if s < 0:
                if neg_dim >= 0:
                    raise OperationError(space.w_ValueError, space.wrap(
                             "can only specify one unknown dimension"))
                s = 1
                neg_dim = i
            new_size *= s
            new_shape.append(s)
            i += 1
        if neg_dim >= 0:
            new_shape[neg_dim] = old_size / new_size
            new_size *= new_shape[neg_dim]
    if new_size != old_size:
        raise OperationError(space.w_ValueError,
                space.wrap("total size of new array must be unchanged"))
    return new_shape

# Recalculating strides. Find the steps that the iteration does for each
# dimension, given the stride and shape. Then try to create a new stride that
# fits the new shape, using those steps. If there is a shape/step mismatch
# (meaning that the realignment of elements crosses from one step into another)
# return None so that the caller can raise an exception.
def calc_new_strides(new_shape, old_shape, old_strides):
    # Return the proper strides for new_shape, or None if the mapping crosses
    # stepping boundaries

    # Assumes that prod(old_shape) == prod(new_shape), len(old_shape) > 1, and
    # len(new_shape) > 0
    steps = []
    last_step = 1
    oldI = 0
    new_strides = []
    if old_strides[0] < old_strides[-1]:
        for i in range(len(old_shape)):
            steps.append(old_strides[i] / last_step)
            last_step *= old_shape[i]
        cur_step = steps[0]
        n_new_elems_used = 1
        n_old_elems_to_use = old_shape[0]
        for s in new_shape:
            new_strides.append(cur_step * n_new_elems_used)
            n_new_elems_used *= s
            while n_new_elems_used > n_old_elems_to_use:
                oldI += 1
                if steps[oldI] != steps[oldI - 1]:
                    return None
                n_old_elems_to_use *= old_shape[oldI]
            if n_new_elems_used == n_old_elems_to_use:
                oldI += 1
                if oldI >= len(old_shape):
                    break
                cur_step = steps[oldI]
                n_old_elems_to_use *= old_shape[oldI]
    else:
        for i in range(len(old_shape) - 1, -1, -1):
            steps.insert(0, old_strides[i] / last_step)
            last_step *= old_shape[i]
        cur_step = steps[-1]
        n_new_elems_used = 1
        oldI = -1
        n_old_elems_to_use = old_shape[-1]
        for i in range(len(new_shape) - 1, -1, -1):
            s = new_shape[i]
            new_strides.insert(0, cur_step * n_new_elems_used)
            n_new_elems_used *= s
            while n_new_elems_used > n_old_elems_to_use:
                oldI -= 1
                if steps[oldI] != steps[oldI + 1]:
                    return None
                n_old_elems_to_use *= old_shape[oldI]
            if n_new_elems_used == n_old_elems_to_use:
                oldI -= 1
                if oldI < -len(old_shape):
                    break
                cur_step = steps[oldI]
                n_old_elems_to_use *= old_shape[oldI]
    return new_strides

# Iterators for arrays
# --------------------
# all those iterators with the exception of BroadcastIterator iterate over the
# entire array in C order (the last index changes the fastest). This will
# yield all elements. Views iterate over indices and look towards strides and
# backstrides to find the correct position. Notably the offset between
# x[..., i + 1] and x[..., i] will be strides[-1]. Offset between
# x[..., k + 1, 0] and x[..., k, i_max] will be backstrides[-2] etc.

# BroadcastIterator works like that, but for indexes that don't change source
# in the original array, strides[i] == backstrides[i] == 0

class BaseIterator(object):
    def next(self, shapelen):
        raise NotImplementedError

    def done(self):
        raise NotImplementedError

    def get_offset(self):
        raise NotImplementedError

class ArrayIterator(BaseIterator):
    def __init__(self, size):
        self.offset = 0
        self.size = size

    def next(self, shapelen):
        arr = instantiate(ArrayIterator)
        arr.size = self.size
        arr.offset = self.offset + 1
        return arr

    def done(self):
        return self.offset >= self.size

    def get_offset(self):
        return self.offset

class OneDimIterator(BaseIterator):
    def __init__(self, start, step, stop):
        self.offset = start
        self.step = step
        self.size = stop * step + start

    def next(self, shapelen):
        arr = instantiate(OneDimIterator)
        arr.size = self.size
        arr.step = self.step
        arr.offset = self.offset + self.step
        return arr

    def done(self):
        return self.offset == self.size

    def get_offset(self):
        return self.offset

class ViewIterator(BaseIterator):
    def __init__(self, arr):
        self.indices = [0] * len(arr.shape)
        self.offset  = arr.start
        self.arr     = arr
        self._done   = False

    @jit.unroll_safe
    def next(self, shapelen):
        offset = self.offset
        indices = [0] * shapelen
        for i in range(shapelen):
            indices[i] = self.indices[i]
        done = False
        for i in range(shapelen - 1, -1, -1):
            if indices[i] < self.arr.shape[i] - 1:
                indices[i] += 1
                offset += self.arr.strides[i]
                break
            else:
                indices[i] = 0
                offset -= self.arr.backstrides[i]
        else:
            done = True
        res = instantiate(ViewIterator)
        res.offset = offset
        res.indices = indices
        res.arr = self.arr
        res._done = done
        return res

    def done(self):
        return self._done

    def get_offset(self):
        return self.offset

class BroadcastIterator(BaseIterator):
    '''Like a view iterator, but will repeatedly access values
       for all iterations across a res_shape, folding the offset
       using mod() arithmetic
    '''
    def __init__(self, arr, res_shape):
        self.indices = [0] * len(res_shape)
        self.offset  = arr.start
        #strides are 0 where original shape==1
        self.strides = []
        self.backstrides = []
        for i in range(len(arr.shape)):
            if arr.shape[i] == 1:
                self.strides.append(0)
                self.backstrides.append(0)
            else:
                self.strides.append(arr.strides[i])
                self.backstrides.append(arr.backstrides[i])
        self.res_shape = res_shape
        self.strides = [0] * (len(res_shape) - len(arr.shape)) + self.strides
        self.backstrides = [0] * (len(res_shape) - len(arr.shape)) + self.backstrides
        self._done = False

    @jit.unroll_safe
    def next(self, shapelen):
        offset = self.offset
        indices = [0] * shapelen
        _done = False
        for i in range(shapelen):
            indices[i] = self.indices[i]
        for i in range(shapelen - 1, -1, -1):
            if indices[i] < self.res_shape[i] - 1:
                indices[i] += 1
                offset += self.strides[i]
                break
            else:
                indices[i] = 0
                offset -= self.backstrides[i]
        else:
            _done = True
        res = instantiate(BroadcastIterator)
        res.indices = indices
        res.offset = offset
        res._done = _done
        res.strides = self.strides
        res.backstrides = self.backstrides
        res.res_shape = self.res_shape
        return res

    def done(self):
        return self._done

    def get_offset(self):
        return self.offset

class Call2Iterator(BaseIterator):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def next(self, shapelen):
        return Call2Iterator(self.left.next(shapelen),
                             self.right.next(shapelen))

    def done(self):
        if isinstance(self.left, ConstantIterator):
            return self.right.done()
        return self.left.done()

    def get_offset(self):
        if isinstance(self.left, ConstantIterator):
            return self.right.get_offset()
        return self.left.get_offset()

class Call1Iterator(BaseIterator):
    def __init__(self, child):
        self.child = child

    def next(self, shapelen):
        return Call1Iterator(self.child.next(shapelen))

    def done(self):
        return self.child.done()

    def get_offset(self):
        return self.child.get_offset()

class ConstantIterator(BaseIterator):
    def next(self, shapelen):
        return self

    def done(self):
        return False

    def get_offset(self):
        return 0


class BaseArray(Wrappable):
    _attrs_ = ["invalidates", "signature", "shape", "strides", "backstrides",
               "start", 'order']

    _immutable_fields_ = ['start', "order"]

    strides = None
    start = 0

    def __init__(self, shape, order):
        self.invalidates = []
        self.shape = shape
        self.order = order
        if self.strides is None:
            self.calc_strides(shape)

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
        self.strides = strides[:]
        self.backstrides = backstrides[:]

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

    def _reduce_ufunc_impl(ufunc_name):
        def impl(self, space):
            return getattr(interp_ufuncs.get(space), ufunc_name).reduce(space, self, multidim=True)
        return func_with_new_name(impl, "reduce_%s_impl" % ufunc_name)

    descr_sum = _reduce_ufunc_impl("add")
    descr_prod = _reduce_ufunc_impl("multiply")
    descr_max = _reduce_ufunc_impl("maximum")
    descr_min = _reduce_ufunc_impl("minimum")

    def _reduce_argmax_argmin_impl(op_name):
        reduce_driver = jit.JitDriver(
            greens=['shapelen', 'signature'],
            reds=['result', 'idx', 'i', 'self', 'cur_best', 'dtype']
        )
        def loop(self):
            i = self.start_iter()
            cur_best = self.eval(i)
            shapelen = len(self.shape)
            i = i.next(shapelen)
            dtype = self.find_dtype()
            result = 0
            idx = 1
            while not i.done():
                reduce_driver.jit_merge_point(signature=self.signature,
                                              shapelen=shapelen,
                                              self=self, dtype=dtype,
                                              i=i, result=result, idx=idx,
                                              cur_best=cur_best)
                new_best = getattr(dtype.itemtype, op_name)(cur_best, self.eval(i))
                if dtype.itemtype.ne(new_best, cur_best):
                    result = idx
                    cur_best = new_best
                i = i.next(shapelen)
                idx += 1
            return result
        def impl(self, space):
            size = self.find_size()
            if size == 0:
                raise OperationError(space.w_ValueError,
                    space.wrap("Can't call %s on zero-size arrays" % op_name))
            return space.wrap(loop(self))
        return func_with_new_name(impl, "reduce_arg%s_impl" % op_name)

    def _all(self):
        dtype = self.find_dtype()
        i = self.start_iter()
        shapelen = len(self.shape)
        while not i.done():
            all_driver.jit_merge_point(signature=self.signature,
                                       shapelen=shapelen, self=self,
                                       dtype=dtype, i=i)
            if not dtype.itemtype.bool(self.eval(i)):
                return False
            i = i.next(shapelen)
        return True

    def descr_all(self, space):
        return space.wrap(self._all())

    def _any(self):
        dtype = self.find_dtype()
        i = self.start_iter()
        shapelen = len(self.shape)
        while not i.done():
            any_driver.jit_merge_point(signature=self.signature,
                                       shapelen=shapelen, self=self,
                                       dtype=dtype, i=i)
            if dtype.itemtype.bool(self.eval(i)):
                return True
            i = i.next(shapelen)
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
            return w_res.descr_sum(space)

    def get_concrete(self):
        raise NotImplementedError

    def descr_get_dtype(self, space):
        return space.wrap(self.find_dtype())

    @jit.unroll_safe
    def descr_get_shape(self, space):
        return space.newtuple([space.wrap(i) for i in self.shape])

    def descr_set_shape(self, space, w_iterable):
        concrete = self.get_concrete()
        new_shape = get_shape_from_iterable(space,
                            concrete.find_size(), w_iterable)
        concrete.setshape(space, new_shape)

    def descr_get_size(self, space):
        return space.wrap(self.find_size())

    def descr_copy(self, space):
        return self.get_concrete().copy()

    def descr_len(self, space):
        return self.get_concrete().descr_len(space)

    def descr_repr(self, space):
        res = StringBuilder()
        res.append("array(")
        concrete = self.get_concrete()
        dtype = concrete.find_dtype()
        if not concrete.find_size():
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
            dtype is not interp_dtype.get_dtype_cache(space).w_int64dtype) or \
            not self.find_size():
            res.append(", dtype=" + dtype.name)
        res.append(")")
        return space.wrap(res.build())

    def to_str(self, space, comma, builder, indent=' ', use_ellipsis=False):
        '''Modifies builder with a representation of the array/slice
        The items will be seperated by a comma if comma is 1
        Multidimensional arrays/slices will span a number of lines,
        each line will begin with indent.
        '''
        size = self.find_size()
        if size < 1:
            builder.append('[]')
            return
        if size > 1000:
            # Once this goes True it does not go back to False for recursive
            # calls
            use_ellipsis = True
        dtype = self.find_dtype()
        ndims = len(self.shape)
        i = 0
        start = True
        builder.append('[')
        if ndims > 1:
            if use_ellipsis:
                for i in range(3):
                    if start:
                        start = False
                    else:
                        builder.append(',' * comma + '\n')
                        if ndims == 3:
                            builder.append('\n' + indent)
                        else:
                            builder.append(indent)
                    # create_slice requires len(chunks) > 1 in order to reduce
                    # shape
                    view = self.create_slice(space, [(i, 0, 0, 1), (0, self.shape[1], 1, self.shape[1])])
                    view.to_str(space, comma, builder, indent=indent + ' ', use_ellipsis=use_ellipsis)
                builder.append('\n' + indent + '..., ')
                i = self.shape[0] - 3
            while i < self.shape[0]:
                if start:
                    start = False
                else:
                    builder.append(',' * comma + '\n')
                    if ndims == 3:
                        builder.append('\n' + indent)
                    else:
                        builder.append(indent)
                # create_slice requires len(chunks) > 1 in order to reduce
                # shape
                view = self.create_slice(space, [(i, 0, 0, 1), (0, self.shape[1], 1, self.shape[1])])
                view.to_str(space, comma, builder, indent=indent + ' ', use_ellipsis=use_ellipsis)
                i += 1
        elif ndims == 1:
            spacer = ',' * comma + ' '
            item = self.start
            # An iterator would be a nicer way to walk along the 1d array, but
            # how do I reset it if printing ellipsis? iterators have no
            # "set_offset()"
            i = 0
            if use_ellipsis:
                for i in range(3):
                    if start:
                        start = False
                    else:
                        builder.append(spacer)
                    builder.append(dtype.itemtype.str_format(self.getitem(item)))
                    item += self.strides[0]
                # Add a comma only if comma is False - this prevents adding two
                # commas
                builder.append(spacer + '...' + ',' * (1 - comma))
                # Ugly, but can this be done with an iterator?
                item = self.start + self.backstrides[0] - 2 * self.strides[0]
                i = self.shape[0] - 3
            while i < self.shape[0]:
                if start:
                    start = False
                else:
                    builder.append(spacer)
                builder.append(dtype.itemtype.str_format(self.getitem(item)))
                item += self.strides[0]
                i += 1
        else:
            builder.append('[')
        builder.append(']')

    def descr_str(self, space):
        ret = StringBuilder()
        concrete = self.get_concrete()
        concrete.to_str(space, 0, ret, ' ')
        return space.wrap(ret.build())

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

    @jit.unroll_safe
    def _single_item_result(self, space, w_idx):
        """ The result of getitem/setitem is a single item if w_idx
        is a list of scalars that match the size of shape
        """
        shape_len = len(self.shape)
        if shape_len == 0:
            if not space.isinstance_w(w_idx, space.w_int):
                raise OperationError(space.w_IndexError, space.wrap(
                    "wrong index"))
            return True
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
            return [space.decode_index4(w_idx, self.shape[0])]
        return [space.decode_index4(w_item, self.shape[i]) for i, w_item in
                enumerate(space.fixedview(w_idx))]

    def descr_getitem(self, space, w_idx):
        if self._single_item_result(space, w_idx):
            concrete = self.get_concrete()
            if len(concrete.shape) < 1:
                raise OperationError(space.w_IndexError, space.wrap(
                        "0-d arrays can't be indexed"))
            item = concrete._index_of_single_item(space, w_idx)
            return concrete.getitem(item)
        chunks = self._prepare_slice_args(space, w_idx)
        return space.wrap(self.create_slice(space, chunks))

    def descr_setitem(self, space, w_idx, w_value):
        self.invalidated()
        if self._single_item_result(space, w_idx):
            concrete = self.get_concrete()
            if len(concrete.shape) < 1:
                raise OperationError(space.w_IndexError, space.wrap(
                        "0-d arrays can't be indexed"))
            item = concrete._index_of_single_item(space, w_idx)
            dtype = concrete.find_dtype()
            concrete.setitem(item, dtype.coerce(space, w_value))
            return
        if not isinstance(w_value, BaseArray):
            w_value = convert_to_array(space, w_value)
        chunks = self._prepare_slice_args(space, w_idx)
        view = self.create_slice(space, chunks)
        view.setslice(space, w_value)

    @jit.unroll_safe
    def create_slice(self, space, chunks):
        if len(chunks) == 1:
            start, stop, step, lgt = chunks[0]
            if step == 0:
                shape = self.shape[1:]
                strides = self.strides[1:]
                backstrides = self.backstrides[1:]
            else:
                shape = [lgt] + self.shape[1:]
                strides = [self.strides[0] * step] + self.strides[1:]
                backstrides = [(lgt - 1) * self.strides[0] * step] + self.backstrides[1:]
            start *= self.strides[0]
            start += self.start
        else:
            shape = []
            strides = []
            backstrides = []
            start = self.start
            i = -1
            for i, (start_, stop, step, lgt) in enumerate(chunks):
                if step != 0:
                    shape.append(lgt)
                    strides.append(self.strides[i] * step)
                    backstrides.append(self.strides[i] * (lgt - 1) * step)
                start += self.strides[i] * start_
            # add a reminder
            s = i + 1
            assert s >= 0
            shape += self.shape[s:]
            strides += self.strides[s:]
            backstrides += self.backstrides[s:]
        new_sig = signature.Signature.find_sig([
            W_NDimSlice.signature, self.signature,
        ])
        return W_NDimSlice(self, new_sig, start, strides[:], backstrides[:],
                           shape[:])

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
        new_shape = get_shape_from_iterable(space,
                                            concrete.find_size(), w_shape)
        # Since we got to here, prod(new_shape) == self.size
        new_strides = calc_new_strides(new_shape,
                                       concrete.shape, concrete.strides)
        if new_strides:
            # We can create a view, strides somehow match up.
            new_sig = signature.Signature.find_sig([
                W_NDimSlice.signature, self.signature
            ])
            ndims = len(new_shape)
            new_backstrides = [0] * ndims
            for nd in range(ndims):
                new_backstrides[nd] = (new_shape[nd] - 1) * new_strides[nd]
            arr = W_NDimSlice(self, new_sig, self.start, new_strides,
                              new_backstrides, new_shape)
        else:
            # Create copy with contiguous data
            arr = concrete.copy()
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

    def descr_mean(self, space):
        return space.div(self.descr_sum(space), space.wrap(self.find_size()))

    def descr_nonzero(self, space):
        if self.find_size() > 1:
            raise OperationError(space.w_ValueError, space.wrap(
                "The truth value of an array with more than one element is ambiguous. Use a.any() or a.all()"))
        return space.wrap(space.is_true(
            self.get_concrete().eval(self.start_iter(self.shape))
        ))

    def descr_get_transpose(self, space):
        concrete = self.get_concrete()
        if len(concrete.shape) < 2:
            return space.wrap(self)
        new_sig = signature.Signature.find_sig([
            W_NDimSlice.signature, self.signature
        ])
        strides = []
        backstrides = []
        shape = []
        for i in range(len(concrete.shape) - 1, -1, -1):
            strides.append(concrete.strides[i])
            backstrides.append(concrete.backstrides[i])
            shape.append(concrete.shape[i])
        return space.wrap(W_NDimSlice(concrete, new_sig, self.start, strides[:],
                                      backstrides[:], shape[:]))

    def descr_get_flatiter(self, space):
        return space.wrap(W_FlatIterator(self))

    def getitem(self, item):
        raise NotImplementedError

    def start_iter(self, res_shape=None):
        raise NotImplementedError

    def descr_array_iface(self, space):
        concrete = self.get_concrete()
        storage = concrete.get_storage(space)
        addr = rffi.cast(lltype.Signed, storage)
        w_d = space.newdict()
        space.setitem_str(w_d, 'data', space.newtuple([space.wrap(addr),
                                                       space.w_False]))
        return w_d

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
    signature = signature.BaseSignature()

    _attrs_ = ["dtype", "value", "shape"]

    def __init__(self, dtype, value):
        self.shape = self.strides = []
        BaseArray.__init__(self, [], 'C')
        self.dtype = dtype
        self.value = value

    def find_size(self):
        return 1

    def get_concrete(self):
        return self

    def find_dtype(self):
        return self.dtype

    def getitem(self, item):
        raise NotImplementedError

    def eval(self, iter):
        return self.value

    def start_iter(self, res_shape=None):
        return ConstantIterator()

    def to_str(self, space, comma, builder, indent=' ', use_ellipsis=False):
        builder.append(self.dtype.itemtype.str_format(self.value))

    def copy(self):
        return Scalar(self.dtype, self.value)

    def debug_repr(self):
        return 'Scalar'

    def setshape(self, space, new_shape):
        # In order to get here, we already checked that prod(new_shape) == 1,
        # so in order to have a consistent API, let it go through.
        pass

    def get_storage(self, space):
        raise OperationError(space.w_TypeError, space.wrap("Cannot get array interface on scalars in pypy"))

class VirtualArray(BaseArray):
    """
    Class for representing virtual arrays, such as binary ops or ufuncs
    """
    def __init__(self, signature, shape, res_dtype, order):
        BaseArray.__init__(self, shape, order)
        self.forced_result = None
        self.signature = signature
        self.res_dtype = res_dtype

    def _del_sources(self):
        # Function for deleting references to source arrays, to allow garbage-collecting them
        raise NotImplementedError

    def compute(self):
        i = 0
        signature = self.signature
        result_size = self.find_size()
        result = W_NDimArray(result_size, self.shape, self.find_dtype())
        shapelen = len(self.shape)
        i = self.start_iter()
        ri = result.start_iter()
        while not ri.done():
            numpy_driver.jit_merge_point(signature=signature,
                                         shapelen=shapelen,
                                         result_size=result_size, i=i, ri=ri,
                                         self=self, result=result)
            result.dtype.setitem(result.storage, ri.offset, self.eval(i))
            i = i.next(shapelen)
            ri = ri.next(shapelen)
        return result

    def force_if_needed(self):
        if self.forced_result is None:
            self.forced_result = self.compute()
            self._del_sources()

    def get_concrete(self):
        self.force_if_needed()
        return self.forced_result

    def eval(self, iter):
        if self.forced_result is not None:
            return self.forced_result.eval(iter)
        return self._eval(iter)

    def getitem(self, item):
        return self.get_concrete().getitem(item)

    def setitem(self, item, value):
        return self.get_concrete().setitem(item, value)

    def find_size(self):
        if self.forced_result is not None:
            # The result has been computed and sources may be unavailable
            return self.forced_result.find_size()
        return self._find_size()

    def find_dtype(self):
        return self.res_dtype


class Call1(VirtualArray):
    def __init__(self, signature, shape, res_dtype, values, order):
        VirtualArray.__init__(self, signature, shape, res_dtype,
                              values.order)
        self.values = values

    def _del_sources(self):
        self.values = None

    def _find_size(self):
        return self.values.find_size()

    def _find_dtype(self):
        return self.res_dtype

    def _eval(self, iter):
        assert isinstance(iter, Call1Iterator)
        val = self.values.eval(iter.child).convert_to(self.res_dtype)
        sig = jit.promote(self.signature)
        assert isinstance(sig, signature.Signature)
        call_sig = sig.components[0]
        assert isinstance(call_sig, signature.Call1)
        return call_sig.func(self.res_dtype, val)

    def start_iter(self, res_shape=None):
        if self.forced_result is not None:
            return self.forced_result.start_iter(res_shape)
        return Call1Iterator(self.values.start_iter(res_shape))

    def debug_repr(self):
        sig = self.signature
        assert isinstance(sig, signature.Signature)
        call_sig = sig.components[0]
        assert isinstance(call_sig, signature.Call1)
        if self.forced_result is not None:
            return 'Call1(%s, forced=%s)' % (call_sig.name,
                                             self.forced_result.debug_repr())
        return 'Call1(%s, %s)' % (call_sig.name,
                                  self.values.debug_repr())

class Call2(VirtualArray):
    """
    Intermediate class for performing binary operations.
    """
    def __init__(self, signature, shape, calc_dtype, res_dtype, left, right):
        # XXX do something if left.order != right.order
        VirtualArray.__init__(self, signature, shape, res_dtype, left.order)
        self.left = left
        self.right = right
        self.calc_dtype = calc_dtype
        self.size = 1
        for s in self.shape:
            self.size *= s

    def _del_sources(self):
        self.left = None
        self.right = None

    def _find_size(self):
        return self.size

    def start_iter(self, res_shape=None):
        if self.forced_result is not None:
            return self.forced_result.start_iter(res_shape)
        if res_shape is None:
            res_shape = self.shape  # we still force the shape on children
        return Call2Iterator(self.left.start_iter(res_shape),
                             self.right.start_iter(res_shape))

    def _eval(self, iter):
        assert isinstance(iter, Call2Iterator)
        lhs = self.left.eval(iter.left).convert_to(self.calc_dtype)
        rhs = self.right.eval(iter.right).convert_to(self.calc_dtype)
        sig = jit.promote(self.signature)
        assert isinstance(sig, signature.Signature)
        call_sig = sig.components[0]
        assert isinstance(call_sig, signature.Call2)
        return call_sig.func(self.calc_dtype, lhs, rhs)

    def debug_repr(self):
        sig = self.signature
        assert isinstance(sig, signature.Signature)
        call_sig = sig.components[0]
        assert isinstance(call_sig, signature.Call2)
        if self.forced_result is not None:
            return 'Call2(%s, forced=%s)' % (call_sig.name,
                self.forced_result.debug_repr())
        return 'Call2(%s, %s, %s)' % (call_sig.name,
            self.left.debug_repr(),
            self.right.debug_repr())

class ViewArray(BaseArray):
    """
    Class for representing views of arrays, they will reflect changes of parent
    arrays. Example: slices
    """
    def __init__(self, parent, signature, strides, backstrides, shape):
        self.strides = strides
        self.backstrides = backstrides
        BaseArray.__init__(self, shape, parent.order)
        self.signature = signature
        self.parent = parent
        self.invalidates = parent.invalidates

    def get_concrete(self):
        # in fact, ViewArray never gets "concrete" as it never stores data.
        # This implementation is needed for BaseArray getitem/setitem to work,
        # can be refactored.
        self.parent.get_concrete()
        return self

    def getitem(self, item):
        return self.parent.getitem(item)

    def eval(self, iter):
        return self.parent.getitem(iter.get_offset())

    def setitem(self, item, value):
        # This is currently not possible to be called from anywhere.
        raise NotImplementedError

    def descr_len(self, space):
        if self.shape:
            return space.wrap(self.shape[0])
        return space.wrap(1)

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
            self.strides = strides[:]
            self.backstrides = backstrides[:]
            self.shape = new_shape[:]
            return
        new_strides = calc_new_strides(new_shape, self.shape, self.strides)
        if new_strides is None:
            raise OperationError(space.w_AttributeError, space.wrap(
                          "incompatible shape for a non-contiguous array"))
        new_backstrides = [0] * len(new_shape)
        for nd in range(len(new_shape)):
            new_backstrides[nd] = (new_shape[nd] - 1) * new_strides[nd]
        self.strides = new_strides[:]
        self.backstrides = new_backstrides[:]
        self.shape = new_shape[:]

class W_NDimSlice(ViewArray):
    signature = signature.BaseSignature()

    def __init__(self, parent, signature, start, strides, backstrides,
                 shape):
        if isinstance(parent, W_NDimSlice):
            parent = parent.parent
        ViewArray.__init__(self, parent, signature, strides, backstrides, shape)
        self.start = start
        self.size = 1
        for sh in shape:
            self.size *= sh

    def find_size(self):
        return self.size

    def find_dtype(self):
        return self.parent.find_dtype()

    def setslice(self, space, w_value):
        res_shape = shape_agreement(space, self.shape, w_value.shape)
        self._sliceloop(w_value, res_shape)

    def _sliceloop(self, source, res_shape):
        source_iter = source.start_iter(res_shape)
        res_iter = self.start_iter(res_shape)
        shapelen = len(res_shape)
        while not res_iter.done():
            slice_driver.jit_merge_point(signature=source.signature,
                                         shapelen=shapelen,
                                         self=self, source=source,
                                         res_iter=res_iter,
                                         source_iter=source_iter)
            self.setitem(res_iter.offset, source.eval(source_iter).convert_to(
                self.find_dtype()))
            source_iter = source_iter.next(shapelen)
            res_iter = res_iter.next(shapelen)

    def start_iter(self, res_shape=None):
        if res_shape is not None and res_shape != self.shape:
            return BroadcastIterator(self, res_shape)
        if len(self.shape) == 1:
            return OneDimIterator(self.start, self.strides[0], self.shape[0])
        return ViewIterator(self)

    def setitem(self, item, value):
        self.parent.setitem(item, value)

    def debug_repr(self):
        return 'Slice(%s)' % self.parent.debug_repr()

    def copy(self):
        array = W_NDimArray(self.size, self.shape[:], self.find_dtype())
        iter = self.start_iter()
        a_iter = array.start_iter()
        while not iter.done():
            array.setitem(a_iter.offset, self.getitem(iter.offset))
            iter = iter.next(len(self.shape))
            a_iter = a_iter.next(len(array.shape))
        return array

    def get_storage(self, space):
        return self.parent.get_storage(space)

class W_NDimArray(BaseArray):
    """ A class representing contiguous array. We know that each iteration
    by say ufunc will increase the data index by one
    """
    def __init__(self, size, shape, dtype, order='C'):
        BaseArray.__init__(self, shape, order)
        self.size = size
        self.dtype = dtype
        self.storage = dtype.malloc(size)
        self.signature = dtype.signature

    def get_concrete(self):
        return self

    def find_size(self):
        return self.size

    def find_dtype(self):
        return self.dtype

    def getitem(self, item):
        return self.dtype.getitem(self.storage, item)

    def eval(self, iter):
        return self.dtype.getitem(self.storage, iter.get_offset())

    def copy(self):
        array = W_NDimArray(self.size, self.shape[:], self.dtype, self.order)
        rffi.c_memcpy(
            array.storage,
            self.storage,
            self.size * self.dtype.itemtype.get_element_size()
        )
        return array

    def descr_len(self, space):
        if len(self.shape):
            return space.wrap(self.shape[0])
        raise OperationError(space.w_TypeError, space.wrap(
            "len() of unsized object"))

    def setitem(self, item, value):
        self.invalidated()
        self.dtype.setitem(self.storage, item, value)

    def start_iter(self, res_shape=None):
        if self.order == 'C':
            if res_shape is not None and res_shape != self.shape:
                return BroadcastIterator(self, res_shape)
            return ArrayIterator(self.size)
        raise NotImplementedError  # use ViewIterator simply, test it

    def setshape(self, space, new_shape):
        self.shape = new_shape
        self.calc_strides(new_shape)

    def debug_repr(self):
        return 'Array'

    def get_storage(self, space):
        return self.storage

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

def array(space, w_item_or_iterable, w_dtype=None, w_order=NoneNotWrapped):
    # find scalar
    if not space.issequence_w(w_item_or_iterable):
        if space.is_w(w_dtype, space.w_None):
            w_dtype = interp_ufuncs.find_dtype_for_scalar(space,
                                                          w_item_or_iterable)
        dtype = space.interp_w(interp_dtype.W_Dtype,
            space.call_function(space.gettypefor(interp_dtype.W_Dtype), w_dtype)
        )
        return scalar_w(space, dtype, w_item_or_iterable)
    if w_order is None:
        order = 'C'
    else:
        order = space.str_w(w_order)
        if order != 'C':  # or order != 'F':
            raise operationerrfmt(space.w_ValueError, "Unknown order: %s",
                                  order)
    shape, elems_w = _find_shape_and_elems(space, w_item_or_iterable)
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
    arr_iter = arr.start_iter(arr.shape)
    for i in range(len(elems_w)):
        w_elem = elems_w[i]
        dtype.setitem(arr.storage, arr_iter.offset, dtype.coerce(space, w_elem))
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

    __repr__ = interp2app(BaseArray.descr_repr),
    __str__ = interp2app(BaseArray.descr_str),
    __array_interface__ = GetSetProperty(BaseArray.descr_array_iface),

    dtype = GetSetProperty(BaseArray.descr_get_dtype),
    shape = GetSetProperty(BaseArray.descr_get_shape,
                           BaseArray.descr_set_shape),
    size = GetSetProperty(BaseArray.descr_get_size),

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

    copy = interp2app(BaseArray.descr_copy),
    reshape = interp2app(BaseArray.descr_reshape),
    tolist = interp2app(BaseArray.descr_tolist),
)


class W_FlatIterator(ViewArray):
    signature = signature.BaseSignature()

    @jit.unroll_safe
    def __init__(self, arr):
        size = 1
        for sh in arr.shape:
            size *= sh
        new_sig = signature.Signature.find_sig([
            W_FlatIterator.signature, arr.signature
        ])
        ViewArray.__init__(self, arr, new_sig, [arr.strides[-1]],
                           [arr.backstrides[-1]], [size])
        self.shapelen = len(arr.shape)
        self.arr = arr
        self.iter = self.start_iter()

    def start_iter(self, res_shape=None):
        if res_shape is not None and res_shape != self.shape:
            return BroadcastIterator(self, res_shape)
        return OneDimIterator(self.arr.start, self.strides[0],
                              self.shape[0])

    def find_dtype(self):
        return self.arr.find_dtype()

    def find_size(self):
        return self.shape[0]

    def descr_next(self, space):
        if self.iter.done():
            raise OperationError(space.w_StopIteration, space.w_None)
        result = self.eval(self.iter)
        self.iter = self.iter.next(self.shapelen)
        return result

    def descr_iter(self):
        return self

    def debug_repr(self):
        return 'FlatIter(%s)' % self.arr.debug_repr()


W_FlatIterator.typedef = TypeDef(
    'flatiter',
    next = interp2app(W_FlatIterator.descr_next),
    __iter__ = interp2app(W_FlatIterator.descr_iter),
)
W_FlatIterator.acceptable_as_base_class = False
