
from pypy.module.micronumpy.base import W_NDimArray, convert_to_array
from pypy.module.micronumpy import loop
from pypy.module.micronumpy.strides import to_coords
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef, interp2app, GetSetProperty

class W_FlatIterator(Wrappable):
    def __init__(self, arr):
        self.base = arr
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
        coords, step, lngth = to_coords(space, self.base.get_shape(),
                            self.base.get_size(), self.base.get_order(),
                            space.wrap(self.index))
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
        res = W_NDimArray.from_shape([length], base.get_dtype(),
                                     base.get_order())
        return loop.flatiter_getitem(res, base_iter, step)

    def descr_setitem(self, space, w_idx, w_value):
        if not (space.isinstance_w(w_idx, space.w_int) or
            space.isinstance_w(w_idx, space.w_slice)):
            raise OperationError(space.w_IndexError,
                                 space.wrap('unsupported iterator index'))
        base = self.base
        start, stop, step, length = space.decode_index4(w_idx, base.get_size())
        arr = convert_to_array(space, w_value)
        loop.flatiter_setitem(self.base, arr, start, step, length)

    def descr_iter(self):
        return self

    def descr_base(self, space):
        return space.wrap(self.base)

W_FlatIterator.typedef = TypeDef(
    'flatiter',
    __iter__ = interp2app(W_FlatIterator.descr_iter),
    __getitem__ = interp2app(W_FlatIterator.descr_getitem),
    __setitem__ = interp2app(W_FlatIterator.descr_setitem),
    __len__ = interp2app(W_FlatIterator.descr_len),

#    __eq__ = interp2app(W_FlatIterator.descr_eq),
#    __ne__ = interp2app(W_FlatIterator.descr_ne),
#    __lt__ = interp2app(W_FlatIterator.descr_lt),
#    __le__ = interp2app(W_FlatIterator.descr_le),
#    __gt__ = interp2app(W_FlatIterator.descr_gt),
#    __ge__ = interp2app(W_FlatIterator.descr_ge),

    next = interp2app(W_FlatIterator.descr_next),
    base = GetSetProperty(W_FlatIterator.descr_base),
    index = GetSetProperty(W_FlatIterator.descr_index),
    coords = GetSetProperty(W_FlatIterator.descr_coords),
)
