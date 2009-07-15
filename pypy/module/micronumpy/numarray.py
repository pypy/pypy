
from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, NoneNotWrapped

class NumArray(Wrappable):
    def __init__(self, space, dim, dtype):
        self.dim = dim
        # ignore dtype for now
        assert len(dim) == 1
        self.storage = [0] * dim[0]

    def descr_getitem(self, space, index):
        return space.wrap(self.storage[index])
    descr_getitem.unwrap_spec = ['self', ObjSpace, int]

NumArray.typedef = TypeDef(
    'NumArray',
    __getitem__ = interp2app(NumArray.descr_getitem),
)

def unpack_dim(space, w_dim):
    if space.is_true(space.isinstance(w_dim, space.w_int)):
        return [space.int_w(w_dim)]
    else:
        raise NotImplementedError

def unpack_dtype(space, w_dtype):
    if space.is_w(w_dtype, space.w_int):
        return 'i'
    else:
        raise NotImplementedError

def zeros(space, w_dim, w_dtype):
    dim = unpack_dim(space, w_dim)
    dtype = unpack_dtype(space, w_dtype)
    return space.wrap(NumArray(space, dim, dtype))
zeros.unwrap_spec = [ObjSpace, W_Root, W_Root]
