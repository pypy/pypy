from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError
from rpython.tool.pairtype import extendabletype


def wrap_impl(space, w_cls, w_instance, impl):
    if w_cls is None or space.is_w(w_cls, space.gettypefor(W_NDimArray)):
        w_ret = W_NDimArray(impl)
    else:
        w_ret = space.allocate_instance(W_NDimArray, w_cls)
        W_NDimArray.__init__(w_ret, impl)
        assert isinstance(w_ret, W_NDimArray)
        space.call_method(w_ret, '__array_finalize__', w_instance)
    return w_ret


class ArrayArgumentException(Exception):
    pass


class W_NDimArray(W_Root):
    __metaclass__ = extendabletype

    def __init__(self, implementation):
        from pypy.module.micronumpy.concrete import BaseConcreteArray
        assert isinstance(implementation, BaseConcreteArray)
        assert isinstance(self, W_NDimArray)
        self.implementation = implementation

    @staticmethod
    def from_shape(space, shape, dtype, order='C', w_instance=None):
        from pypy.module.micronumpy import concrete
        from pypy.module.micronumpy.strides import calc_strides
        strides, backstrides = calc_strides(shape, dtype.base, order)
        impl = concrete.ConcreteArray(shape, dtype.base, order, strides,
                                      backstrides)
        if w_instance:
            return wrap_impl(space, space.type(w_instance), w_instance, impl)
        return W_NDimArray(impl)

    @staticmethod
    def from_shape_and_storage(space, shape, storage, dtype, order='C', owning=False,
                               w_subtype=None, w_base=None, writable=True):
        from pypy.module.micronumpy import concrete
        from pypy.module.micronumpy.strides import calc_strides
        strides, backstrides = calc_strides(shape, dtype, order)
        if w_base is not None:
            if owning:
                raise OperationError(space.w_ValueError,
                        space.wrap("Cannot have owning=True when specifying a buffer"))
            if writable:
                impl = concrete.ConcreteArrayWithBase(shape, dtype, order, strides,
                                                      backstrides, storage, w_base)
            else:
                impl = concrete.ConcreteNonWritableArrayWithBase(shape, dtype, order,
                                                                 strides, backstrides,
                                                                 storage, w_base)
        elif owning:
            # Will free storage when GCd
            impl = concrete.ConcreteArray(shape, dtype, order, strides,
                                          backstrides, storage=storage)
        else:
            impl = concrete.ConcreteArrayNotOwning(shape, dtype, order, strides,
                                                   backstrides, storage)
        if w_subtype:
            w_ret = space.allocate_instance(W_NDimArray, w_subtype)
            W_NDimArray.__init__(w_ret, impl)
            space.call_method(w_ret, '__array_finalize__', w_subtype)
            return w_ret
        return W_NDimArray(impl)

    @staticmethod
    def new_slice(space, offset, strides, backstrides, shape, parent, orig_arr, dtype=None):
        from pypy.module.micronumpy import concrete

        impl = concrete.SliceArray(offset, strides, backstrides, shape, parent,
                                   orig_arr, dtype)
        return wrap_impl(space, space.type(orig_arr), orig_arr, impl)

    @staticmethod
    def new_scalar(space, dtype, w_val=None):
        if w_val is not None:
            w_val = dtype.coerce(space, w_val)
        else:
            w_val = dtype.coerce(space, space.wrap(0))
        return convert_to_array(space, w_val)


def convert_to_array(space, w_obj):
    from pypy.module.micronumpy.ctors import array
    if isinstance(w_obj, W_NDimArray):
        return w_obj
    return array(space, w_obj)
