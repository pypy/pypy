from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef, GetSetProperty, make_weakref_descr
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault
from pypy.interpreter.error import OperationError
#from pypy.module.micronumpy.iter import W_NDIter

class W_NDIter(W_Root):

    def __init__(self, *args, **kwargs):
        pass

    def descr_iter(self, space):
        return space.wrap(self)

    def descr_getitem(self, space, w_idx):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            'not implemented yet'))

    def descr_setitem(self, space, w_idx, w_value):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            'not implemented yet'))

    def descr_len(self, space):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            'not implemented yet'))

    def descr_next(self, space):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            'not implemented yet'))

    def descr_iternext(self, space):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            'not implemented yet'))

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

    def descr_get_operands(self, space, w_indx):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            'not implemented yet'))

    def descr_get_dtypes(self, space):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            'not implemented yet'))

    def descr_get_finished(self, space):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            'not implemented yet'))

    def descr_get_has_delayed_bufalloc(self, space):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            'not implemented yet'))

    def descr_get_has_index(self, space):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            'not implemented yet'))

    def descr_get_index(self, space):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            'not implemented yet'))

    def descr_get_has_multi_index(self, space):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            'not implemented yet'))

    def descr_get_multi_index(self, space):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            'not implemented yet'))

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
    return W_NDIter()

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
