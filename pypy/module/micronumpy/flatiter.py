from pypy.interpreter.error import OperationError, oefmt
from pypy.module.micronumpy import loop
from pypy.module.micronumpy.base import W_NDimArray, convert_to_array
from pypy.module.micronumpy.concrete import BaseConcreteArray


class FakeArrayImplementation(BaseConcreteArray):
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

    def create_iter(self, shape=None, backward_broadcast=False):
        assert isinstance(self.base(), W_NDimArray)
        return self.base().create_iter()


class W_FlatIterator(W_NDimArray):
    def __init__(self, arr):
        self.base = arr
        self.iter, self.state = arr.create_iter()
        # this is needed to support W_NDimArray interface
        self.implementation = FakeArrayImplementation(self.base)

    def descr_len(self, space):
        return space.wrap(self.iter.size)

    def descr_next(self, space):
        if self.iter.done(self.state):
            raise OperationError(space.w_StopIteration, space.w_None)
        w_res = self.iter.getitem(self.state)
        self.state = self.iter.next(self.state)
        return w_res

    def descr_index(self, space):
        return space.wrap(self.state.index)

    def descr_coords(self, space):
        self.state = self.iter.update(self.state)
        return space.newtuple([space.wrap(c) for c in self.state.indices])

    def descr_getitem(self, space, w_idx):
        if not (space.isinstance_w(w_idx, space.w_int) or
                space.isinstance_w(w_idx, space.w_slice)):
            raise oefmt(space.w_IndexError, 'unsupported iterator index')
        try:
            start, stop, step, length = space.decode_index4(w_idx, self.iter.size)
            state = self.iter.goto(start)
            if length == 1:
                return self.iter.getitem(state)
            base = self.base
            res = W_NDimArray.from_shape(space, [length], base.get_dtype(),
                                         base.get_order(), w_instance=base)
            return loop.flatiter_getitem(res, self.iter, state, step)
        finally:
            self.state = self.iter.reset(self.state)

    def descr_setitem(self, space, w_idx, w_value):
        if not (space.isinstance_w(w_idx, space.w_int) or
                space.isinstance_w(w_idx, space.w_slice)):
            raise oefmt(space.w_IndexError, 'unsupported iterator index')
        start, stop, step, length = space.decode_index4(w_idx, self.iter.size)
        try:
            state = self.iter.goto(start)
            dtype = self.base.get_dtype()
            if length == 1:
                try:
                    val = dtype.coerce(space, w_value)
                except OperationError:
                    raise oefmt(space.w_ValueError, "Error setting single item of array.")
                self.iter.setitem(state, val)
                return
            arr = convert_to_array(space, w_value)
            loop.flatiter_setitem(space, dtype, arr, self.iter, state, step, length)
        finally:
            self.state = self.iter.reset(self.state)

    def descr_iter(self):
        return self

    def descr_base(self, space):
        return space.wrap(self.base)

# typedef is in interp_ndarray, so we see the additional arguments
