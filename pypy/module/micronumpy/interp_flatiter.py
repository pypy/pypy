
from pypy.module.micronumpy.base import W_NDimArray, convert_to_array
from pypy.module.micronumpy import loop
from pypy.module.micronumpy.arrayimpl.base import BaseArrayImplementation
from pypy.interpreter.error import OperationError

class FakeArrayImplementation(BaseArrayImplementation):
    """ The sole purpose of this class is to W_FlatIterator can behave
    like a real array for descr_eq and friends
    """
    def __init__(self, base):
        self._base = base
        self.dtype = base.get_dtype()
        self.shape = [base.get_size()]

    def base(self):
        return self._base

    def get_shape(self):
        return self.shape

    def create_iter(self, shape=None, backward_broadcast=False, require_index=False):
        assert isinstance(self.base(), W_NDimArray)
        return self.base().create_iter()

class W_FlatIterator(W_NDimArray):
    def __init__(self, arr):
        self.base = arr
        # this is needed to support W_NDimArray interface
        self.implementation = FakeArrayImplementation(self.base)
        self.reset()

    def reset(self):
        self.iter = self.base.create_iter()
        self.index = 0

    def descr_len(self, space):
        return space.wrap(self.base.get_size())

    def descr_next(self, space):
        if self.iter.done():
            raise OperationError(space.w_StopIteration, space.w_None)
        w_res = self.iter.getitem()
        self.iter.next()
        self.index += 1
        return w_res

    def descr_index(self, space):
        return space.wrap(self.index)

    def descr_coords(self, space):
        coords = self.base.to_coords(space, space.wrap(self.index))
        return space.newtuple([space.wrap(c) for c in coords])

    def descr_getitem(self, space, w_idx):
        if not (space.isinstance_w(w_idx, space.w_int) or
            space.isinstance_w(w_idx, space.w_slice)):
            raise OperationError(space.w_IndexError,
                                 space.wrap('unsupported iterator index'))
        self.reset()
        base = self.base
        start, stop, step, length = space.decode_index4(w_idx, base.get_size())
        base_iter = base.create_iter()
        base_iter.next_skip_x(start)
        if length == 1:
            return base_iter.getitem()
        res = W_NDimArray.from_shape(space, [length], base.get_dtype(),
                                     base.get_order(), w_instance=base)
        return loop.flatiter_getitem(res, base_iter, step)

    def descr_setitem(self, space, w_idx, w_value):
        if not (space.isinstance_w(w_idx, space.w_int) or
            space.isinstance_w(w_idx, space.w_slice)):
            raise OperationError(space.w_IndexError,
                                 space.wrap('unsupported iterator index'))
        base = self.base
        start, stop, step, length = space.decode_index4(w_idx, base.get_size())
        arr = convert_to_array(space, w_value)
        loop.flatiter_setitem(space, self.base, arr, start, step, length)

    def descr_iter(self):
        return self

    def descr_base(self, space):
        return space.wrap(self.base)

# typedef is in interp_numarray, so we see the additional arguments
