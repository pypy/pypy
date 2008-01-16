
""" Interpreter-level implementation of array, exposing ll-structure
to app-level with apropriate interface
"""

from pypy.interpreter.baseobjspace import W_Root, ObjSpace, Wrappable,\
     Arguments
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef, GetSetProperty, interp_attrproperty
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.interpreter.error import OperationError, wrap_oserror
from pypy.module._ffi.structure import segfault_exception
from pypy.module._ffi.interp_ffi import unwrap_value, wrap_value, _get_type,\
     TYPEMAP
from pypy.rlib.rarithmetic import intmask

def push_elem(ll_array, pos, value):
    TP = lltype.typeOf(value)
    ll_array = rffi.cast(lltype.Ptr(rffi.CArray(TP)), ll_array)
    ll_array[pos] = value
push_elem._annspecialcase_ = 'specialize:argtype(2)'

def get_elem(ll_array, pos, ll_t):
    ll_array = rffi.cast(lltype.Ptr(rffi.CArray(ll_t)), ll_array)
    return ll_array[pos]
get_elem._annspecialcase_ = 'specialize:arg(2)'

class W_Array(Wrappable):
    def __init__(self, space, of):
        self.space = space
        self.of = of
        self.itemsize = intmask(TYPEMAP[of].c_size)

    def descr_call(self, space, w_length_or_iterable):
        if space.is_true(space.isinstance(w_length_or_iterable, space.w_int)):
            length = space.int_w(w_length_or_iterable)
            return space.wrap(W_ArrayInstance(space, self, length))
        else:
            items_w = space.unpackiterable(w_length_or_iterable)
            length = len(items_w)
            result = W_ArrayInstance(space, self, length)
            for num in range(len(items_w)):
                w_item = items_w[num]
                unwrap_value(space, push_elem, result.ll_array, num, self.of,
                             w_item, None)
            return space.wrap(result)

    def fromaddress(self, space, address, length):
        return space.wrap(W_ArrayInstance(space, self, length, address))
    fromaddress.unwrap_spec = ['self', ObjSpace, int, int]

def descr_new_array(space, w_type, of):
    _get_type(space, of)
    return space.wrap(W_Array(space, of))

W_Array.typedef = TypeDef(
    'Array',
    __new__  = interp2app(descr_new_array, unwrap_spec=[ObjSpace, W_Root, str]),
    __call__ = interp2app(W_Array.descr_call,
                          unwrap_spec=['self', ObjSpace, W_Root]),
    fromaddress = interp2app(W_Array.fromaddress),
    of = interp_attrproperty('of', W_Array),
)
W_Array.typedef.acceptable_as_base_class = False


class W_ArrayInstance(Wrappable):
    def __init__(self, space, shape, length, address=0):
        self.ll_array = lltype.nullptr(rffi.VOIDP.TO)
        self.alloced = False
        self.length = length
        self.shape = shape
        if address != 0:
            self.ll_array = rffi.cast(rffi.VOIDP, address)
        else:
            size = shape.itemsize * length
            self.ll_array = lltype.malloc(rffi.VOIDP.TO, size, flavor='raw',
                                          zero=True)


    # XXX don't allow negative indexes, nor slices

    def setitem(self, space, num, w_value):
        if num >= self.length or num < 0:
            raise OperationError(space.w_IndexError, space.w_None)
        unwrap_value(space, push_elem, self.ll_array, num, self.shape.of, w_value,
                   None)
    setitem.unwrap_spec = ['self', ObjSpace, int, W_Root]

    def getitem(self, space, num):
        if num >= self.length or num < 0:
            raise OperationError(space.w_ValueError, space.wrap(
                "Getting element %d of array sized %d" % (num, self.length)))
        return wrap_value(space, get_elem, self.ll_array, num, self.shape.of)
    getitem.unwrap_spec = ['self', ObjSpace, int]

    def getbuffer(space, self):
        return space.wrap(rffi.cast(rffi.INT, self.ll_array))

    def free(self, space):
        if not self.ll_array:
            raise segfault_exception(space, "freeing NULL pointer")
        lltype.free(self.ll_array, flavor='raw')
        self.ll_array = lltype.nullptr(rffi.VOIDP.TO)
    free.unwrap_spec = ['self', ObjSpace]

W_ArrayInstance.typedef = TypeDef(
    'ArrayInstance',
    __setitem__ = interp2app(W_ArrayInstance.setitem),
    __getitem__ = interp2app(W_ArrayInstance.getitem),
    buffer      = GetSetProperty(W_ArrayInstance.getbuffer),
    shape       = interp_attrproperty('shape', W_ArrayInstance),
    free        = interp2app(W_ArrayInstance.free),
)


