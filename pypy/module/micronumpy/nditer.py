from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault
from pypy.interpreter.error import OperationError, oefmt
from pypy.module.micronumpy import ufuncs, support, concrete
from pypy.module.micronumpy.base import W_NDimArray, convert_to_array
from pypy.module.micronumpy.descriptor import decode_w_dtype
from pypy.module.micronumpy.iterators import ArrayIter
from pypy.module.micronumpy.strides import (calculate_broadcast_strides,
                                            shape_agreement, shape_agreement_multiple)


def parse_op_arg(space, name, w_op_flags, n, parse_one_arg):
    if space.is_w(w_op_flags, space.w_None):
        w_op_flags = space.newtuple([space.wrap('readonly')])
    if not space.isinstance_w(w_op_flags, space.w_tuple) and not \
            space.isinstance_w(w_op_flags, space.w_list):
        raise oefmt(space.w_ValueError,
                    '%s must be a tuple or array of per-op flag-tuples',
                    name)
    ret = []
    w_lst = space.listview(w_op_flags)
    if space.isinstance_w(w_lst[0], space.w_tuple) or \
       space.isinstance_w(w_lst[0], space.w_list):
        if len(w_lst) != n:
            raise oefmt(space.w_ValueError,
                        '%s must be a tuple or array of per-op flag-tuples',
                        name)
        for item in w_lst:
            ret.append(parse_one_arg(space, space.listview(item)))
    else:
        op_flag = parse_one_arg(space, w_lst)
        for i in range(n):
            ret.append(op_flag)
    return ret


class OpFlag(object):
    def __init__(self):
        self.rw = ''
        self.broadcast = True
        self.force_contig = False
        self.force_align = False
        self.native_byte_order = False
        self.tmp_copy = ''
        self.allocate = False


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
    if op_flag.rw == '':
        raise oefmt(space.w_ValueError,
                    "None of the iterator flags READWRITE, READONLY, or "
                    "WRITEONLY were specified for an operand")
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
            raise oefmt(space.w_TypeError,
                        'expected string or Unicode object, %s found',
                        typename)
        item = space.str_w(w_item)
        if item == 'external_loop':
            raise OperationError(space.w_NotImplementedError, space.wrap(
                'nditer external_loop not implemented yet'))
            nditer.external_loop = True
        elif item == 'buffered':
            raise OperationError(space.w_NotImplementedError, space.wrap(
                'nditer buffered not implemented yet'))
            # For numpy compatability
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
            raise OperationError(space.w_NotImplementedError, space.wrap(
                'nditer reduce_ok not implemented yet'))
            nditer.reduce_ok = True
        elif item == 'zerosize_ok':
            nditer.zerosize_ok = True
        else:
            raise oefmt(space.w_ValueError,
                        'Unexpected iterator global flag "%s"',
                        item)
    if nditer.tracked_index and nditer.external_loop:
        raise OperationError(space.w_ValueError, space.wrap(
            'Iterator flag EXTERNAL_LOOP cannot be used if an index or '
            'multi-index is being tracked'))


def is_backward(imp, order):
    if order == 'K' or (order == 'C' and imp.order == 'C'):
        return False
    elif order == 'F' and imp.order == 'C':
        return True
    else:
        raise NotImplementedError('not implemented yet')


def get_iter(space, order, arr, shape, dtype):
    imp = arr.implementation
    backward = is_backward(imp, order)
    if arr.is_scalar():
        return ArrayIter(imp, 1, [], [], [])
    if (imp.strides[0] < imp.strides[-1] and not backward) or \
       (imp.strides[0] > imp.strides[-1] and backward):
        # flip the strides. Is this always true for multidimension?
        strides = imp.strides[:]
        backstrides = imp.backstrides[:]
        shape = imp.shape[:]
        strides.reverse()
        backstrides.reverse()
        shape.reverse()
    else:
        strides = imp.strides
        backstrides = imp.backstrides
    r = calculate_broadcast_strides(strides, backstrides, imp.shape,
                                    shape, backward)
    return ArrayIter(imp, imp.get_size(), shape, r[0], r[1])


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
        self.op_axes = []
        # convert w_seq operands to a list of W_NDimArray
        if space.isinstance_w(w_seq, space.w_tuple) or \
           space.isinstance_w(w_seq, space.w_list):
            w_seq_as_list = space.listview(w_seq)
            self.seq = [convert_to_array(space, w_elem)
                        if not space.is_none(w_elem) else None
                        for w_elem in w_seq_as_list]
        else:
            self.seq = [convert_to_array(space, w_seq)]

        parse_func_flags(space, self, w_flags)
        self.op_flags = parse_op_arg(space, 'op_flags', w_op_flags,
                                     len(self.seq), parse_op_flag)
        # handle w_op_axes
        if not space.is_none(w_op_axes):
            self.set_op_axes(space, w_op_axes)

        # handle w_op_dtypes part 1: creating self.dtypes list from input
        if not space.is_none(w_op_dtypes):
            w_seq_as_list = space.listview(w_op_dtypes)
            self.dtypes = [decode_w_dtype(space, w_elem) for w_elem in w_seq_as_list]
            if len(self.dtypes) != len(self.seq):
                raise OperationError(space.w_ValueError, space.wrap(
                    "op_dtypes must be a tuple/list matching the number of ops"))
        else:
            self.dtypes = []

        # handle None or writable operands, calculate my shape
        self.iters = []
        outargs = [i for i in range(len(self.seq))
                   if self.seq[i] is None or self.op_flags[i].rw == 'w']
        if len(outargs) > 0:
            out_shape = shape_agreement_multiple(space, [self.seq[i] for i in outargs])
        else:
            out_shape = None
        self.shape = iter_shape = shape_agreement_multiple(space, self.seq,
                                                           shape=out_shape)
        if len(outargs) > 0:
            # Make None operands writeonly and flagged for allocation
            if len(self.dtypes) > 0:
                out_dtype = self.dtypes[outargs[0]]
            else:
                out_dtype = None
                for i in range(len(self.seq)):
                    if self.seq[i] is None:
                        self.op_flags[i].allocate = True
                        continue
                    if self.op_flags[i].rw == 'w':
                        continue
                    out_dtype = ufuncs.find_binop_result_dtype(
                        space, self.seq[i].get_dtype(), out_dtype)
            for i in outargs:
                if self.seq[i] is None:
                    # XXX can we postpone allocation to later?
                    self.seq[i] = W_NDimArray.from_shape(space, iter_shape, out_dtype)
                else:
                    if not self.op_flags[i].broadcast:
                        # Raises if ooutput cannot be broadcast
                        shape_agreement(space, iter_shape, self.seq[i], False)

        if self.tracked_index != "":
            if self.order == "K":
                self.order = self.seq[0].implementation.order
            if self.tracked_index == "multi":
                backward = False
            else:
                backward = self.order != self.tracked_index
            self.index_iter = IndexIterator(iter_shape, backward=backward)

        # handle w_op_dtypes part 2: copy where needed if possible
        if len(self.dtypes) > 0:
            for i in range(len(self.seq)):
                selfd = self.dtypes[i]
                seq_d = self.seq[i].get_dtype()
                if not selfd:
                    self.dtypes[i] = seq_d
                elif selfd != seq_d:
                    if not 'r' in self.op_flags[i].tmp_copy:
                        raise oefmt(space.w_TypeError,
                                    "Iterator operand required copying or "
                                    "buffering for operand %d", i)
                    impl = self.seq[i].implementation
                    new_impl = impl.astype(space, selfd)
                    self.seq[i] = W_NDimArray(new_impl)
        else:
            #copy them from seq
            self.dtypes = [s.get_dtype() for s in self.seq]

        # create an iterator for each operand
        for i in range(len(self.seq)):
            it = get_iter(space, self.order, self.seq[i], iter_shape, self.dtypes[i])
            self.iters.append((it, it.reset()))

    def set_op_axes(self, space, w_op_axes):
        if space.len_w(w_op_axes) != len(self.seq):
            raise oefmt(space.w_ValueError,
                        "op_axes must be a tuple/list matching the number of ops")
        op_axes = space.listview(w_op_axes)
        l = -1
        for w_axis in op_axes:
            if not space.is_none(w_axis):
                axis_len = space.len_w(w_axis)
                if l == -1:
                    l = axis_len
                elif axis_len != l:
                    raise oefmt(space.w_ValueError,
                                "Each entry of op_axes must have the same size")
                self.op_axes.append([space.int_w(x) if not space.is_none(x) else -1
                                     for x in space.listview(w_axis)])
        if l == -1:
            raise oefmt(space.w_ValueError,
                        "If op_axes is provided, at least one list of axes "
                        "must be contained within it")
        raise Exception('xxx TODO')
        # Check that values make sense:
        # - in bounds for each operand
        # ValueError: Iterator input op_axes[0][3] (==3) is not a valid axis of op[0], which has 2 dimensions
        # - no repeat axis
        # ValueError: The 'op_axes' provided to the iterator constructor for operand 1 contained duplicate value 0

    def descr_iter(self, space):
        return space.wrap(self)

    def getitem(self, it, st, op_flags):
        if op_flags.rw == 'r':
            impl = concrete.ConcreteNonWritableArrayWithBase
        else:
            impl = concrete.ConcreteArrayWithBase
        res = impl([], it.array.dtype, it.array.order, [], [],
                   it.array.storage, self)
        res.start = st.offset
        return W_NDimArray(res)

    def descr_getitem(self, space, w_idx):
        idx = space.int_w(w_idx)
        try:
            it, st = self.iters[idx]
        except IndexError:
            raise oefmt(space.w_IndexError,
                        "Iterator operand index %d is out of bounds", idx)
        return self.getitem(it, st, self.op_flags[idx])

    def descr_setitem(self, space, w_idx, w_value):
        raise oefmt(space.w_NotImplementedError, "not implemented yet")

    def descr_len(self, space):
        space.wrap(len(self.iters))

    def descr_next(self, space):
        for it, st in self.iters:
            if not it.done(st):
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
        for i, (it, st) in enumerate(self.iters):
            res.append(self.getitem(it, st, self.op_flags[i]))
            self.iters[i] = (it, it.next(st))
        if len(res) < 2:
            return res[0]
        return space.newtuple(res)

    def iternext(self):
        if self.index_iter:
            self.index_iter.next()
        for i, (it, st) in enumerate(self.iters):
            self.iters[i] = (it, it.next(st))
        for it, st in self.iters:
            if not it.done(st):
                break
        else:
            self.done = True
            return self.done
        return self.done

    def descr_iternext(self, space):
        return space.wrap(self.iternext())

    def descr_copy(self, space):
        raise oefmt(space.w_NotImplementedError, "not implemented yet")

    def descr_debug_print(self, space):
        raise oefmt(space.w_NotImplementedError, "not implemented yet")

    def descr_enable_external_loop(self, space):
        raise oefmt(space.w_NotImplementedError, "not implemented yet")

    @unwrap_spec(axis=int)
    def descr_remove_axis(self, space, axis):
        raise oefmt(space.w_NotImplementedError, "not implemented yet")

    def descr_remove_multi_index(self, space, w_multi_index):
        raise oefmt(space.w_NotImplementedError, "not implemented yet")

    def descr_reset(self, space):
        raise oefmt(space.w_NotImplementedError, "not implemented yet")

    def descr_get_operands(self, space):
        l_w = []
        for op in self.seq:
            l_w.append(op.descr_view(space))
        return space.newlist(l_w)

    def descr_get_dtypes(self, space):
        res = [None] * len(self.seq)
        for i in range(len(self.seq)):
            res[i] = self.seq[i].descr_get_dtype(space)
        return space.newtuple(res)

    def descr_get_finished(self, space):
        return space.wrap(self.done)

    def descr_get_has_delayed_bufalloc(self, space):
        raise oefmt(space.w_NotImplementedError, "not implemented yet")

    def descr_get_has_index(self, space):
        return space.wrap(self.tracked_index in ["C", "F"])

    def descr_get_index(self, space):
        if not self.tracked_index in ["C", "F"]:
            raise oefmt(space.w_ValueError, "Iterator does not have an index")
        if self.done:
            raise oefmt(space.w_ValueError, "Iterator is past the end")
        return space.wrap(self.index_iter.getvalue())

    def descr_get_has_multi_index(self, space):
        return space.wrap(self.tracked_index == "multi")

    def descr_get_multi_index(self, space):
        if not self.tracked_index == "multi":
            raise oefmt(space.w_ValueError, "Iterator is not tracking a multi-index")
        if self.done:
            raise oefmt(space.w_ValueError, "Iterator is past the end")
        return space.newtuple([space.wrap(x) for x in self.index_iter.index])

    def descr_get_iterationneedsapi(self, space):
        raise oefmt(space.w_NotImplementedError, "not implemented yet")

    def descr_get_iterindex(self, space):
        raise oefmt(space.w_NotImplementedError, "not implemented yet")

    def descr_get_itersize(self, space):
        return space.wrap(support.product(self.shape))

    def descr_get_itviews(self, space):
        raise oefmt(space.w_NotImplementedError, "not implemented yet")

    def descr_get_ndim(self, space):
        raise oefmt(space.w_NotImplementedError, "not implemented yet")

    def descr_get_nop(self, space):
        raise oefmt(space.w_NotImplementedError, "not implemented yet")

    def descr_get_shape(self, space):
        raise oefmt(space.w_NotImplementedError, "not implemented yet")

    def descr_get_value(self, space):
        raise oefmt(space.w_NotImplementedError, "not implemented yet")


@unwrap_spec(w_flags=WrappedDefault(None), w_op_flags=WrappedDefault(None),
             w_op_dtypes=WrappedDefault(None), order=str,
             w_casting=WrappedDefault(None), w_op_axes=WrappedDefault(None),
             w_itershape=WrappedDefault(None), w_buffersize=WrappedDefault(None))
def descr__new__(space, w_subtype, w_seq, w_flags, w_op_flags, w_op_dtypes,
                 w_casting, w_op_axes, w_itershape, w_buffersize, order='K'):
    return W_NDIter(space, w_seq, w_flags, w_op_flags, w_op_dtypes, w_casting, w_op_axes,
                    w_itershape, w_buffersize, order)

W_NDIter.typedef = TypeDef('numpy.nditer',
    __new__ = interp2app(descr__new__),

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
W_NDIter.typedef.acceptable_as_base_class = False
