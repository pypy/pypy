
from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, NoneNotWrapped
from pypy.rlib.debug import make_sure_not_resized

class BaseNumArray(Wrappable):
    pass

class NumArray(BaseNumArray):
    def __init__(self, space, dim, dtype):
        self.dim = dim
        self.space = space
        # ignore dtype for now
        self.storage = [0] * dim
        make_sure_not_resized(self.storage)

    def descr_getitem(self, index):
        space = self.space
        try:
            return space.wrap(self.storage[index])
        except IndexError:
            raise OperationError(space.w_IndexError,
                                 space.wrap("list index out of range"))
    descr_getitem.unwrap_spec = ['self', int]

    def descr_setitem(self, index, value):
        space = self.space
        try:
            self.storage[index] = value
        except IndexError:
            raise OperationError(space.w_IndexError,
                                 space.wrap("list index out of range"))
        return space.w_None
    descr_setitem.unwrap_spec = ['self', int, int]

    def descr_len(self):
        return self.space.wrap(len(self.storage))
    descr_len.unwrap_spec = ['self']

NumArray.typedef = TypeDef(
    'NumArray',
    __getitem__ = interp2app(NumArray.descr_getitem),
    __setitem__ = interp2app(NumArray.descr_setitem),
    __len__     = interp2app(NumArray.descr_len),
)

def compute_pos(space, indexes, dim):
    current = 1
    pos = 0
    for i in range(len(indexes)):
        index = indexes[i]
        d = dim[i]
        if index >= d or index <= -d - 1:
            raise OperationError(space.w_IndexError,
                                 space.wrap("invalid index"))
        if index < 0:
            index = d + index
        pos += index * current
        current *= d
    return pos

class MultiDimArray(BaseNumArray):
    def __init__(self, space, dim, dtype):
        self.dim = dim
        self.space = space
        # ignore dtype for now
        size = 1
        for el in dim:
            size *= el
        self.storage = [0] * size
        make_sure_not_resized(self.storage)

    def _unpack_indexes(self, space, w_index):
        indexes = [space.int_w(w_i) for w_i in space.fixedview(w_index)]
        if len(indexes) != len(self.dim):
            raise OperationError(space.w_IndexError, space.wrap(
                'Wrong index'))
        return indexes

    def descr_getitem(self, w_index):
        space = self.space
        indexes = self._unpack_indexes(space, w_index)
        pos = compute_pos(space, indexes, self.dim)
        return space.wrap(self.storage[pos])
    descr_getitem.unwrap_spec = ['self', W_Root]

    def descr_setitem(self, w_index, value):
        space = self.space
        indexes = self._unpack_indexes(space, w_index)
        pos = compute_pos(space, indexes, self.dim)
        self.storage[pos] = value
        return space.w_None
    descr_setitem.unwrap_spec = ['self', W_Root, int]

    def descr_len(self):
        return self.space.wrap(self.dim[0])
    descr_len.unwrap_spec = ['self']

MultiDimArray.typedef = TypeDef(
    'NumArray',
    __getitem__ = interp2app(MultiDimArray.descr_getitem),
    __setitem__ = interp2app(MultiDimArray.descr_setitem),
    __len__     = interp2app(MultiDimArray.descr_len),
)

def unpack_dim(space, w_dim):
    if space.is_true(space.isinstance(w_dim, space.w_int)):
        return [space.int_w(w_dim)]
    dim_w = space.fixedview(w_dim)
    return [space.int_w(w_i) for w_i in dim_w]

def unpack_dtype(space, w_dtype):
    if space.is_w(w_dtype, space.w_int):
        return 'i'
    else:
        raise NotImplementedError

def zeros(space, w_dim, w_dtype):
    dim = unpack_dim(space, w_dim)
    dtype = unpack_dtype(space, w_dtype)
    if len(dim) == 1:
        return space.wrap(NumArray(space, dim[0], dtype))
    else:
        return space.wrap(MultiDimArray(space, dim, dtype))
zeros.unwrap_spec = [ObjSpace, W_Root, W_Root]
