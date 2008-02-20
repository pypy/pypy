
""" Interpreter-level implementation of array, exposing ll-structure
to app-level with apropriate interface
"""

from pypy.interpreter.baseobjspace import W_Root, ObjSpace, Wrappable,\
     Arguments
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef, GetSetProperty, interp_attrproperty
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.interpreter.error import OperationError, wrap_oserror
from pypy.module._rawffi.interp_rawffi import segfault_exception
from pypy.module._rawffi.interp_rawffi import W_DataInstance
from pypy.module._rawffi.interp_rawffi import unwrap_value, wrap_value
from pypy.module._rawffi.interp_rawffi import unpack_typecode, letter2tp
from pypy.rlib.rarithmetic import intmask, r_uint

def push_elem(ll_array, pos, value):
    TP = lltype.typeOf(value)
    ll_array = rffi.cast(rffi.CArrayPtr(TP), ll_array)
    ll_array[pos] = value
push_elem._annspecialcase_ = 'specialize:argtype(2)'

def get_elem(ll_array, pos, ll_t):
    ll_array = rffi.cast(rffi.CArrayPtr(ll_t), ll_array)
    return ll_array[pos]
get_elem._annspecialcase_ = 'specialize:arg(2)'

class W_Array(Wrappable):
    def __init__(self, space, itemtp):
        assert isinstance(itemtp, tuple)
        self.space = space
        self.itemtp = itemtp

    def allocate(self, space, length, autofree=False):
        if autofree:
            return W_ArrayInstanceAutoFree(space, self, length)
        return W_ArrayInstance(space, self, length)

    def descr_call(self, space, length, w_items=None, autofree=False):
        result = self.allocate(space, length, autofree)
        if not space.is_w(w_items, space.w_None):
            items_w = space.unpackiterable(w_items)
            iterlength = len(items_w)
            if iterlength > length:
                raise OperationError(space.w_ValueError,
                                     space.wrap("too many items for specified"
                                                " array length"))
            for num in range(iterlength):
                w_item = items_w[num]
                unwrap_value(space, push_elem, result.ll_buffer, num,
                             self.itemtp, w_item)
        return space.wrap(result)

    def descr_repr(self, space):
        return space.wrap("<_rawffi.Array '%s' (%d, %d)>" % self.itemtp)
    descr_repr.unwrap_spec = ['self', ObjSpace]

    def fromaddress(self, space, address, length):
        return space.wrap(W_ArrayInstance(space, self, length, address))
    fromaddress.unwrap_spec = ['self', ObjSpace, r_uint, int]

    def descr_gettypecode(self, space, length):
        _, itemsize, alignment = self.itemtp
        return space.newtuple([space.wrap(itemsize * length),
                               space.wrap(alignment)])
    descr_gettypecode.unwrap_spec = ['self', ObjSpace, int]

class ArrayCache:
    def __init__(self, space):
        self.space = space
        self.cache = {}
        self.array_of_ptr = self.get_array_type(letter2tp(space, 'P'))

    def get_array_type(self, itemtp):
        try:
            return self.cache[itemtp]
        except KeyError:
            result = W_Array(self.space, itemtp)
            self.cache[itemtp] = result
            return result

def get_array_cache(space):
    return space.fromcache(ArrayCache)

def descr_new_array(space, w_type, w_itemtp):
    itemtp = unpack_typecode(space, w_itemtp)
    array_type = get_array_cache(space).get_array_type(itemtp)
    return space.wrap(array_type)

W_Array.typedef = TypeDef(
    'Array',
    __new__  = interp2app(descr_new_array,
                          unwrap_spec=[ObjSpace, W_Root, W_Root]),
    __call__ = interp2app(W_Array.descr_call,
                          unwrap_spec=['self', ObjSpace, int, W_Root, int]),
    __repr__ = interp2app(W_Array.descr_repr),
    fromaddress = interp2app(W_Array.fromaddress),
    gettypecode = interp2app(W_Array.descr_gettypecode),
)
W_Array.typedef.acceptable_as_base_class = False


class W_ArrayInstance(W_DataInstance):
    def __init__(self, space, shape, length, address=r_uint(0)):
        _, itemsize, _ = shape.itemtp
        W_DataInstance.__init__(self, space, itemsize * length, address)
        self.length = length
        self.shape = shape

    def descr_repr(self, space):
        addr = rffi.cast(lltype.Unsigned, self.ll_buffer)
        return space.wrap("<_rawffi array %x of length %d>" % (addr,
                                                               self.length))
    descr_repr.unwrap_spec = ['self', ObjSpace]

    # XXX don't allow negative indexes, nor slices

    def setitem(self, space, num, w_value):
        if not self.ll_buffer:
            raise segfault_exception(space, "setting element of freed array")
        if num >= self.length or num < 0:
            raise OperationError(space.w_IndexError, space.w_None)
        unwrap_value(space, push_elem, self.ll_buffer, num, self.shape.itemtp,
                     w_value)
    setitem.unwrap_spec = ['self', ObjSpace, int, W_Root]

    def getitem(self, space, num):
        if not self.ll_buffer:
            raise segfault_exception(space, "accessing elements of freed array")
        if num >= self.length or num < 0:
            raise OperationError(space.w_IndexError, space.w_None)
        return wrap_value(space, get_elem, self.ll_buffer, num,
                          self.shape.itemtp)
    getitem.unwrap_spec = ['self', ObjSpace, int]

    def getlength(self, space):
        return space.wrap(self.length)
    getlength.unwrap_spec = ['self', ObjSpace]

    def descr_itemaddress(self, space, num):
        _, itemsize, _ = self.shape.itemtp
        ptr = rffi.ptradd(self.ll_buffer, itemsize * num)
        return space.wrap(rffi.cast(lltype.Unsigned, ptr))
    descr_itemaddress.unwrap_spec = ['self', ObjSpace, int]

W_ArrayInstance.typedef = TypeDef(
    'ArrayInstance',
    __repr__    = interp2app(W_ArrayInstance.descr_repr),
    __setitem__ = interp2app(W_ArrayInstance.setitem),
    __getitem__ = interp2app(W_ArrayInstance.getitem),
    __len__     = interp2app(W_ArrayInstance.getlength),
    buffer      = GetSetProperty(W_ArrayInstance.getbuffer),
    shape       = interp_attrproperty('shape', W_ArrayInstance),
    free        = interp2app(W_ArrayInstance.free),
    byptr       = interp2app(W_ArrayInstance.byptr),
    itemaddress = interp2app(W_ArrayInstance.descr_itemaddress),
)
W_ArrayInstance.typedef.acceptable_as_base_class = False


class W_ArrayInstanceAutoFree(W_ArrayInstance):
    def __init__(self, space, shape, length):
        W_ArrayInstance.__init__(self, space, shape, length, 0)

    def __del__(self):
        if self.ll_buffer:
            self._free()

