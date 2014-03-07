from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault
from pypy.interpreter.error import OperationError
from pypy.module.micronumpy.base import W_NDimArray, convert_to_array
from pypy.module.micronumpy.strides import (calculate_broadcast_strides,
                                             shape_agreement_multiple)
from pypy.module.micronumpy.iterators import ArrayIter, SliceIterator
from pypy.module.micronumpy.concrete import SliceArray

class AbstractIterator(object):
    def done(self):
        raise NotImplementedError("Abstract Class")

    def next(self):
        raise NotImplementedError("Abstract Class")

    def getitem(self, space, array):
        raise NotImplementedError("Abstract Class")

class IteratorMixin(object):
    _mixin_ = True
    def __init__(self, it, op_flags):
        self.it = it
        self.op_flags = op_flags

    def done(self):
        return self.it.done()

    def next(self):
        self.it.next()

    def getitem(self, space, array):
        return self.op_flags.get_it_item[self.index](space, array, self.it)

class BoxIterator(IteratorMixin, AbstractIterator):
    index = 0

class ExternalLoopIterator(IteratorMixin, AbstractIterator):
    index = 1

def parse_op_arg(space, name, w_op_flags, n, parse_one_arg):
    ret = []
    if space.is_w(w_op_flags, space.w_None):
        for i in range(n):
            ret.append(OpFlag())
    elif not space.isinstance_w(w_op_flags, space.w_tuple) and not \
             space.isinstance_w(w_op_flags, space.w_list):
        raise OperationError(space.w_ValueError, space.wrap(
                '%s must be a tuple or array of per-op flag-tuples' % name))
    else:
        w_lst = space.listview(w_op_flags)
        if space.isinstance_w(w_lst[0], space.w_tuple) or \
           space.isinstance_w(w_lst[0], space.w_list):
            if len(w_lst) != n:
                raise OperationError(space.w_ValueError, space.wrap(
                   '%s must be a tuple or array of per-op flag-tuples' % name))
            for item in w_lst:
                ret.append(parse_one_arg(space, space.listview(item)))
        else:
            op_flag = parse_one_arg(space, w_lst)
            for i in range(n):
                ret.append(op_flag)
    return ret

class OpFlag(object):
    def __init__(self):
        self.rw = 'r'
        self.broadcast = True
        self.force_contig = False
        self.force_align = False
        self.native_byte_order = False
        self.tmp_copy = ''
        self.allocate = False
        self.get_it_item = (get_readonly_item, get_readonly_slice)

def get_readonly_item(space, array, it):
    return space.wrap(it.getitem())

def get_readwrite_item(space, array, it):
    #create a single-value view (since scalars are not views)
    res = SliceArray(it.array.start + it.offset, [0], [0], [1,], it.array, array)
    #it.dtype.setitem(res, 0, it.getitem())
    return W_NDimArray(res)

def get_readonly_slice(space, array, it):
    return W_NDimArray(it.getslice().readonly())

def get_readwrite_slice(space, array, it):
    return W_NDimArray(it.getslice())

def parse_op_flag(space, lst):
    op_flag = OpFlag()
    for w_item in lst:
        item = space.str_w(w_item)
        if item == 'readonly':
            op_flag.rw = 'r'
        elif item == 'readwrite':
            op_flag.rw = 'rw'
        elif item == 'writeonly':
            op_flag.rw = 'w'
        elif item == 'no_broadcast':
            op_flag.broadcast = False
        elif item == 'contig':
            op_flag.force_contig = True
        elif item == 'aligned':
            op_flag.force_align = True
        elif item == 'nbo':
            op_flag.native_byte_order = True
        elif item == 'copy':
            op_flag.tmp_copy = 'r'
        elif item == 'updateifcopy':
            op_flag.tmp_copy = 'rw'
        elif item == 'allocate':
            op_flag.allocate = True
        elif item == 'no_subtype':
            raise OperationError(space.w_NotImplementedError, space.wrap(
                    '"no_subtype" op_flag not implemented yet'))
        elif item == 'arraymask':
            raise OperationError(space.w_NotImplementedError, space.wrap(
                    '"arraymask" op_flag not implemented yet'))
        elif item == 'writemask':
            raise OperationError(space.w_NotImplementedError, space.wrap(
                    '"writemask" op_flag not implemented yet'))
        else:
            raise OperationError(space.w_ValueError, space.wrap(
                    'op_flags must be a tuple or array of per-op flag-tuples'))
        if op_flag.rw == 'r':
            op_flag.get_it_item = (get_readonly_item, get_readonly_slice)
        elif op_flag.rw == 'rw':
            op_flag.get_it_item = (get_readwrite_item, get_readwrite_slice)
    return op_flag

def parse_func_flags(space, nditer, w_flags):
    if space.is_w(w_flags, space.w_None):
        return
    elif not space.isinstance_w(w_flags, space.w_tuple) and not \
             space.isinstance_w(w_flags, space.w_list):
        raise OperationError(space.w_ValueError, space.wrap(
                'Iter global flags must be a list or tuple of strings'))
    lst = space.listview(w_flags)
    for w_item in lst:
        if not space.isinstance_w(w_item, space.w_str) and not \
               space.isinstance_w(w_item, space.w_unicode):
            typename = space.type(w_item).getname(space)
            raise OperationError(space.w_TypeError, space.wrap(
                    'expected string or Unicode object, %s found' % typename))
        item = space.str_w(w_item)
        if item == 'external_loop':
            nditer.external_loop = True
        elif item == 'buffered':
            nditer.buffered = True
        elif item == 'c_index':
            nditer.tracked_index = 'C'
        elif item == 'f_index':
            nditer.tracked_index = 'F'
        elif item == 'multi_index':
            nditer.tracked_index = 'multi'
        elif item == 'common_dtype':
            nditer.common_dtype = True
        elif item == 'delay_bufalloc':
            nditer.delay_bufalloc = True
        elif item == 'grow_inner':
            nditer.grow_inner = True
        elif item == 'ranged':
            nditer.ranged = True
        elif item == 'refs_ok':
            nditer.refs_ok = True
        elif item == 'reduce_ok':
            nditer.reduce_ok = True
        elif item == 'zerosize_ok':
            nditer.zerosize_ok = True
        else:
            raise OperationError(space.w_ValueError, space.wrap(
                    'Unexpected iterator global flag "%s"' % item))
    if nditer.tracked_index and nditer.external_loop:
            raise OperationError(space.w_ValueError, space.wrap(
                'Iterator flag EXTERNAL_LOOP cannot be used if an index or '
                'multi-index is being tracked'))

def get_iter(space, order, arr, shape):
    imp = arr.implementation
    if order == 'K' or (order == 'C' and imp.order == 'C'):
        backward = False
    elif order =='F' and imp.order == 'C':
        backward = True
    else:
        raise OperationError(space.w_NotImplementedError, space.wrap(
                'not implemented yet'))
    if (imp.strides[0] < imp.strides[-1] and not backward) or \
       (imp.strides[0] > imp.strides[-1] and backward):
        # flip the strides. Is this always true for multidimension?
        strides = [imp.strides[i] for i in range(len(imp.strides) - 1, -1, -1)]
        backstrides = [imp.backstrides[i] for i in range(len(imp.backstrides) - 1, -1, -1)]
        shape = [imp.shape[i] for i in range(len(imp.shape) - 1, -1, -1)]
    else:
        strides = imp.strides
        backstrides = imp.backstrides
    r = calculate_broadcast_strides(strides, backstrides, imp.shape,
                                    shape, backward)
    return ArrayIter(imp, imp.get_size(), shape, r[0], r[1])

def is_backward(imp, order):
    if order == 'K' or (order == 'C' and imp.order == 'C'):
        return False
    elif order =='F' and imp.order == 'C':
        return True
    else:
        raise NotImplementedError('not implemented yet')

def get_external_loop_iter(space, order, arr, shape):
    imp = arr.implementation

    backward = is_backward(imp, order)

    return SliceIterator(arr, imp.strides, imp.backstrides, shape, order=order, backward=backward)

class IndexIterator(object):
    def __init__(self, shape, backward=False):
        self.shape = shape
        self.index = [0] * len(shape)
        self.backward = backward

    def next(self):
        # TODO It's probably possible to refactor all the "next" method from each iterator
        for i in range(len(self.shape) - 1, -1, -1):
            if self.index[i] < self.shape[i] - 1:
                self.index[i] += 1
                break
            else:
                self.index[i] = 0

    def getvalue(self):
        if not self.backward:
            ret = self.index[-1]
            for i in range(len(self.shape) - 2, -1, -1):
                ret += self.index[i] * self.shape[i - 1]
        else:
            ret = self.index[0]
            for i in range(1, len(self.shape)):
                ret += self.index[i] * self.shape[i - 1]
        return ret

class W_NDIter(W_Root):

    def __init__(self, space, w_seq, w_flags, w_op_flags, w_op_dtypes, w_casting,
            w_op_axes, w_itershape, w_buffersize, order):
        self.order = order
        self.external_loop = False
        self.buffered = False
        self.tracked_index = ''
        self.common_dtype = False
        self.delay_bufalloc = False
        self.grow_inner = False
        self.ranged = False
        self.refs_ok = False
        self.reduce_ok = False
        self.zerosize_ok = False
        self.index_iter = None
        self.done = False
        self.first_next = True
        if space.isinstance_w(w_seq, space.w_tuple) or \
           space.isinstance_w(w_seq, space.w_list):
            w_seq_as_list = space.listview(w_seq)
            self.seq = [convert_to_array(space, w_elem) for w_elem in w_seq_as_list]
        else:
            self.seq =[convert_to_array(space, w_seq)]
        parse_func_flags(space, self, w_flags)
        self.op_flags = parse_op_arg(space, 'op_flags', w_op_flags,
                                     len(self.seq), parse_op_flag)
        if not space.is_none(w_op_axes):
            self.set_op_axes(space, w_op_axes)
        self.iters=[]
        self.shape = iter_shape = shape_agreement_multiple(space, self.seq)
        if self.tracked_index != "":
            if self.order == "K":
                self.order = self.seq[0].implementation.order
            if self.tracked_index == "multi":
                backward = False
            else:
                backward = self.order != self.tracked_index
            self.index_iter = IndexIterator(iter_shape, backward=backward)
        if self.external_loop:
            for i in range(len(self.seq)):
                self.iters.append(ExternalLoopIterator(get_external_loop_iter(space, self.order,
                                self.seq[i], iter_shape), self.op_flags[i]))
        else:
            for i in range(len(self.seq)):
                self.iters.append(BoxIterator(get_iter(space, self.order,
                                self.seq[i], iter_shape), self.op_flags[i]))

    def set_op_axes(self, space, w_op_axes):
        if space.len_w(w_op_axes) != len(self.seq):
            raise OperationError(space.w_ValueError, space.wrap("op_axes must be a tuple/list matching the number of ops"))
        op_axes = space.listview(w_op_axes)
        l = -1
        for w_axis in op_axes:
            if not space.is_(w_axis, space.w_None):
                axis_len = space.len_w(w_axis)
                if l == -1:
                    l = axis_len
                elif axis_len != l:
                    raise OperationError(space.w_ValueError, space.wrap("Each entry of op_axes must have the same size"))
                self.op_axes.append([space.int_w(x) if not space.is_(x, space.w_None) else space.w_None for x in space.listview(w_axis)])
        if l == -1:
            raise OperationError(space.w_ValueError, space.wrap("If op_axes is provided, at least one list of axes must be contained within it"))

    def descr_iter(self, space):
        return space.wrap(self)

    def descr_getitem(self, space, w_idx):
        idx = space.int_w(w_idx)
        try:
            ret = space.wrap(self.iters[idx].getitem(space, self.seq[idx]))
        except IndexError:
            raise OperationError(space.w_IndexError, space.wrap("Iterator operand index %d is out of bounds" % idx))
        return ret

    def descr_setitem(self, space, w_idx, w_value):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            'not implemented yet'))

    def descr_len(self, space):
        space.wrap(len(self.iters))

    def descr_next(self, space):
        for it in self.iters:
            if not it.done():
                break
        else:
            self.done = True
            raise OperationError(space.w_StopIteration, space.w_None)
        res = []
        if self.index_iter:
            if not self.first_next:
                self.index_iter.next()
            else:
                self.first_next = False
        for i in range(len(self.iters)):
            res.append(self.iters[i].getitem(space, self.seq[i]))
            self.iters[i].next()
        if len(res) <2:
            return res[0]
        return space.newtuple(res)

    def iternext(self):
        if self.index_iter:
            self.index_iter.next()
        for i in range(len(self.iters)):
            self.iters[i].next()
        for it in self.iters:
            if not it.done():
                break
        else:
            self.done = True
            return self.done
        return self.done

    def descr_iternext(self, space):
        return space.wrap(self.iternext())

    def descr_copy(self, space):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            'not implemented yet'))

    def descr_debug_print(self, space):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            'not implemented yet'))

    def descr_enable_external_loop(self, space):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            'not implemented yet'))

    @unwrap_spec(axis=int)
    def descr_remove_axis(self, space, axis):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            'not implemented yet'))

    def descr_remove_multi_index(self, space, w_multi_index):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            'not implemented yet'))

    def descr_reset(self, space):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            'not implemented yet'))

    def descr_get_operands(self, space):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            'not implemented yet'))

    def descr_get_dtypes(self, space):
        res = [None] * len(self.seq)
        for i in range(len(self.seq)):
            res[i] = self.seq[i].descr_get_dtype(space)
        return space.newtuple(res)

    def descr_get_finished(self, space):
        return space.wrap(self.done)

    def descr_get_has_delayed_bufalloc(self, space):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            'not implemented yet'))

    def descr_get_has_index(self, space):
        return space.wrap(self.tracked_index in ["C", "F"])

    def descr_get_index(self, space):
        if not self.tracked_index in ["C", "F"]:
            raise OperationError(space.w_ValueError, space.wrap("Iterator does not have an index"))
        if self.done:
            raise OperationError(space.w_ValueError, space.wrap("Iterator is past the end"))
        return space.wrap(self.index_iter.getvalue())

    def descr_get_has_multi_index(self, space):
        return space.wrap(self.tracked_index == "multi")

    def descr_get_multi_index(self, space):
        if not self.tracked_index == "multi":
            raise OperationError(space.w_ValueError, space.wrap("Iterator is not tracking a multi-index"))
        if self.done:
            raise OperationError(space.w_ValueError, space.wrap("Iterator is past the end"))
        return space.newtuple([space.wrap(x) for x in self.index_iter.index])

    def descr_get_iterationneedsapi(self, space):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            'not implemented yet'))

    def descr_get_iterindex(self, space):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            'not implemented yet'))

    def descr_get_itersize(self, space):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            'not implemented yet'))

    def descr_get_itviews(self, space):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            'not implemented yet'))

    def descr_get_ndim(self, space):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            'not implemented yet'))

    def descr_get_nop(self, space):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            'not implemented yet'))

    def descr_get_shape(self, space):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            'not implemented yet'))

    def descr_get_value(self, space):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            'not implemented yet'))


@unwrap_spec(w_flags = WrappedDefault(None), w_op_flags=WrappedDefault(None),
             w_op_dtypes = WrappedDefault(None), order=str,
             w_casting=WrappedDefault(None), w_op_axes=WrappedDefault(None),
             w_itershape=WrappedDefault(None), w_buffersize=WrappedDefault(None))
def nditer(space, w_seq, w_flags, w_op_flags, w_op_dtypes, w_casting, w_op_axes,
             w_itershape, w_buffersize, order='K'):
    return W_NDIter(space, w_seq, w_flags, w_op_flags, w_op_dtypes, w_casting, w_op_axes,
            w_itershape, w_buffersize, order)

W_NDIter.typedef = TypeDef(
    'nditer',
    __iter__ = interp2app(W_NDIter.descr_iter),
    __getitem__ = interp2app(W_NDIter.descr_getitem),
    __setitem__ = interp2app(W_NDIter.descr_setitem),
    __len__ = interp2app(W_NDIter.descr_len),

    next = interp2app(W_NDIter.descr_next),
    iternext = interp2app(W_NDIter.descr_iternext),
    copy = interp2app(W_NDIter.descr_copy),
    debug_print = interp2app(W_NDIter.descr_debug_print),
    enable_external_loop = interp2app(W_NDIter.descr_enable_external_loop),
    remove_axis = interp2app(W_NDIter.descr_remove_axis),
    remove_multi_index = interp2app(W_NDIter.descr_remove_multi_index),
    reset = interp2app(W_NDIter.descr_reset),

    operands = GetSetProperty(W_NDIter.descr_get_operands),
    dtypes = GetSetProperty(W_NDIter.descr_get_dtypes),
    finished = GetSetProperty(W_NDIter.descr_get_finished),
    has_delayed_bufalloc = GetSetProperty(W_NDIter.descr_get_has_delayed_bufalloc),
    has_index = GetSetProperty(W_NDIter.descr_get_has_index),
    index = GetSetProperty(W_NDIter.descr_get_index),
    has_multi_index = GetSetProperty(W_NDIter.descr_get_has_multi_index),
    multi_index = GetSetProperty(W_NDIter.descr_get_multi_index),
    iterationneedsapi = GetSetProperty(W_NDIter.descr_get_iterationneedsapi),
    iterindex = GetSetProperty(W_NDIter.descr_get_iterindex),
    itersize = GetSetProperty(W_NDIter.descr_get_itersize),
    itviews = GetSetProperty(W_NDIter.descr_get_itviews),
    ndim = GetSetProperty(W_NDIter.descr_get_ndim),
    nop = GetSetProperty(W_NDIter.descr_get_nop),
    shape = GetSetProperty(W_NDIter.descr_get_shape),
    value = GetSetProperty(W_NDIter.descr_get_value),
)
