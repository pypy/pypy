
from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, NoneNotWrapped
from pypy.rpython.lltypesystem import lltype

TP = lltype.GcArray(lltype.Float)

class BaseBytecode(Wrappable):
    pass

class Add(BaseBytecode):
    def __init__(self, left, right):
        self.left = left
        self.right = right

class SingleDimArray(Wrappable):
    def __init__(self, size):
        self.size = size
        self.storage = lltype.malloc(TP, size, zero=True)

    def descr_getitem(self, space, item):
        if item < 0:
            raise operationerrfmt(space.w_TypeError,
              '%d below zero', item)
        if item > self.size:
            raise operationerrfmt(space.w_TypeError,
              '%d above array size', item)
        return space.wrap(self.storage[item])
    descr_getitem.unwrap_spec = ['self', ObjSpace, int]

    def descr_setitem(self, space, item, value):
        if item < 0:
            raise operationerrfmt(space.w_TypeError,
              '%d below zero', item)
        if item > self.size:
            raise operationerrfmt(space.w_TypeError,
              '%d above array size', item)
        self.storage[item] = value
    descr_setitem.unwrap_spec = ['self', ObjSpace, int, float]

    def descr_add(self, space, w_other):
        return space.wrap(Add(self, w_other))
    descr_add.unwrap_spec = ['self', ObjSpace, W_Root]

def descr_new_numarray(space, w_type, w_size_or_iterable):
    if space.isinstance_w(w_size_or_iterable, space.w_int):
        arr = SingleDimArray(space.int_w(w_size_or_iterable))
    else:
        l = space.listview(w_size_or_iterable)
        arr = SingleDimArray(len(l))
        i = 0
        for w_elem in l:
            arr.storage[i] = space.float_w(space.float(w_elem))
            i += 1
    return space.wrap(arr)
descr_new_numarray.unwrap_spec = [ObjSpace, W_Root, W_Root]

SingleDimArray.typedef = TypeDef(
    'numarray',
    __new__ = interp2app(descr_new_numarray),
    __getitem__ = interp2app(SingleDimArray.descr_getitem),
    __setitem__ = interp2app(SingleDimArray.descr_setitem),
    __add__ = interp2app(SingleDimArray.descr_add),
)

