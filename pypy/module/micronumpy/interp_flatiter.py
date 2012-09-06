
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef, interp2app
from pypy.rlib import jit

class W_FlatIterator(Wrappable):
    def __init__(self, arr):
        self.base = arr
        self.iter = arr.create_iter()
        self.index = 0

    def descr_next(self, space):
        if self.iter.done():
            raise OperationError(space.w_StopIteration, space.w_None)
        w_res = self.iter.getitem()
        self.iter.next()
        self.index += 1
        return w_res

    @jit.unroll_safe
    def descr_getitem(self, space, w_idx):
        if not (space.isinstance_w(w_idx, space.w_int) or
            space.isinstance_w(w_idx, space.w_slice)):
            raise OperationError(space.w_IndexError,
                                 space.wrap('unsupported iterator index'))
        base = self.base
        start, stop, step, length = space.decode_index4(w_idx, base.get_size())
        # setslice would have been better, but flat[u:v] for arbitrary
        # shapes of array a cannot be represented as a[x1:x2, y1:y2]
        base_iter = base.create_iter()
        xxx
        return base.getitem(basei.offset)
        base_iter = ViewIterator(base.start, base.strides,
                             base.backstrides, base.shape)
        shapelen = len(base.shape)
        basei = basei.next_skip_x(shapelen, start)
        res = W_NDimArray([lngth], base.dtype, base.order)
        ri = res.create_iter()
        while not ri.done():
            flat_get_driver.jit_merge_point(shapelen=shapelen,
                                             base=base,
                                             basei=basei,
                                             step=step,
                                             res=res,
                                             ri=ri)
            w_val = base.getitem(basei.offset)
            res.setitem(ri.offset, w_val)
            basei = basei.next_skip_x(shapelen, step)
            ri = ri.next(shapelen)
        return res

    def descr_iter(self):
        return self

W_FlatIterator.typedef = TypeDef(
    'flatiter',
    __iter__ = interp2app(W_FlatIterator.descr_iter),    

    next = interp2app(W_FlatIterator.descr_next),
)
