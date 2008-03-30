
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
from pypy.module._rawffi.interp_rawffi import W_DataShape, W_DataInstance
from pypy.module._rawffi.interp_rawffi import unwrap_value, wrap_value
from pypy.module._rawffi.interp_rawffi import letter2tp
from pypy.module._rawffi.interp_rawffi import unpack_to_size_alignment
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

class W_Array(W_DataShape):
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

    def _size_alignment(self):
        _, itemsize, alignment = self.itemtp
        return itemsize, alignment

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

def descr_new_array(space, w_type, w_shape):
    itemtp = unpack_to_size_alignment(space, w_shape)
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
    size_alignment = interp2app(W_Array.descr_size_alignment)
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

    # This only allows non-negative indexes.  Arrays of shape 'c' also
    # support simple slices.

    def setitem(self, space, num, w_value):
        if not self.ll_buffer:
            raise segfault_exception(space, "setting element of freed array")
        if num >= self.length or num < 0:
            raise OperationError(space.w_IndexError, space.w_None)
        unwrap_value(space, push_elem, self.ll_buffer, num, self.shape.itemtp,
                     w_value)

    def descr_setitem(self, space, w_index, w_value):
        try:
            num = space.int_w(w_index)
        except OperationError, e:
            if not e.match(space, space.w_TypeError):
                raise
            self.setslice(space, w_index, w_value)
        else:
            self.setitem(space, num, w_value)
    descr_setitem.unwrap_spec = ['self', ObjSpace, W_Root, W_Root]

    def getitem(self, space, num):
        if not self.ll_buffer:
            raise segfault_exception(space, "accessing elements of freed array")
        if num >= self.length or num < 0:
            raise OperationError(space.w_IndexError, space.w_None)
        return wrap_value(space, get_elem, self.ll_buffer, num,
                          self.shape.itemtp)

    def descr_getitem(self, space, w_index):
        try:
            num = space.int_w(w_index)
        except OperationError, e:
            if not e.match(space, space.w_TypeError):
                raise
            return self.getslice(space, w_index)
        else:
            return self.getitem(space, num)
    descr_getitem.unwrap_spec = ['self', ObjSpace, W_Root]

    def getlength(self, space):
        return space.wrap(self.length)
    getlength.unwrap_spec = ['self', ObjSpace]

    def descr_itemaddress(self, space, num):
        _, itemsize, _ = self.shape.itemtp
        ptr = rffi.ptradd(self.ll_buffer, itemsize * num)
        return space.wrap(rffi.cast(lltype.Unsigned, ptr))
    descr_itemaddress.unwrap_spec = ['self', ObjSpace, int]

    def getrawsize(self):
        _, itemsize, _ = self.shape.itemtp
        return itemsize * self.length

    def decodeslice(self, space, w_slice):
        if not space.is_true(space.isinstance(w_slice, space.w_slice)):
            raise OperationError(space.w_TypeError,
                                 space.wrap('index must be int or slice'))
        letter, _, _ = self.shape.itemtp
        if letter != 'c':
            raise OperationError(space.w_TypeError,
                                 space.wrap("only 'c' arrays support slicing"))
        w_start = space.getattr(w_slice, space.wrap('start'))
        w_stop = space.getattr(w_slice, space.wrap('stop'))
        w_step = space.getattr(w_slice, space.wrap('step'))

        if space.is_w(w_start, space.w_None):
            start = 0
        else:
            start = space.int_w(w_start)
        if space.is_w(w_stop, space.w_None):
            stop = self.length
        else:
            stop = space.int_w(w_stop)
        if not space.is_w(w_step, space.w_None):
            step = space.int_w(w_step)
            if step != 1:
                raise OperationError(space.w_ValueError,
                                     space.wrap("no step support"))
        if not (0 <= start <= stop <= self.length):
            raise OperationError(space.w_ValueError,
                                 space.wrap("slice out of bounds"))
        if not self.ll_buffer:
            raise segfault_exception(space, "accessing a freed array")
        return start, stop

    def getslice(self, space, w_slice):
        start, stop = self.decodeslice(space, w_slice)
        ll_buffer = self.ll_buffer
        result = [ll_buffer[i] for i in range(start, stop)]
        return space.wrap(''.join(result))

    def setslice(self, space, w_slice, w_value):
        start, stop = self.decodeslice(space, w_slice)
        value = space.bufferstr_w(w_value)
        if start + len(value) != stop:
            raise OperationError(space.w_ValueError,
                                 space.wrap("cannot resize array"))
        ll_buffer = self.ll_buffer
        for i in range(len(value)):
            ll_buffer[start + i] = value[i]

W_ArrayInstance.typedef = TypeDef(
    'ArrayInstance',
    __repr__    = interp2app(W_ArrayInstance.descr_repr),
    __setitem__ = interp2app(W_ArrayInstance.descr_setitem),
    __getitem__ = interp2app(W_ArrayInstance.descr_getitem),
    __len__     = interp2app(W_ArrayInstance.getlength),
    __buffer__  = interp2app(W_ArrayInstance.descr_buffer),
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

W_ArrayInstanceAutoFree.typedef = TypeDef(
    'ArrayInstanceWithFree',
    __repr__    = interp2app(W_ArrayInstance.descr_repr),
    __setitem__ = interp2app(W_ArrayInstance.descr_setitem),
    __getitem__ = interp2app(W_ArrayInstance.descr_getitem),
    __len__     = interp2app(W_ArrayInstance.getlength),
    __buffer__  = interp2app(W_ArrayInstance.descr_buffer),
    buffer      = GetSetProperty(W_ArrayInstance.getbuffer),
    shape       = interp_attrproperty('shape', W_ArrayInstance),
    byptr       = interp2app(W_ArrayInstance.byptr),
    itemaddress = interp2app(W_ArrayInstance.descr_itemaddress),
)
W_ArrayInstanceAutoFree.typedef.acceptable_as_base_class = False
