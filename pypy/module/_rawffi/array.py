
""" Interpreter-level implementation of array, exposing ll-structure
to app-level with apropriate interface
"""

from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef, GetSetProperty, interp_attrproperty
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.interpreter.error import OperationError
from pypy.module._rawffi.interp_rawffi import segfault_exception
from pypy.module._rawffi.interp_rawffi import W_DataShape, W_DataInstance
from pypy.module._rawffi.interp_rawffi import unwrap_value, wrap_value
from pypy.module._rawffi.interp_rawffi import TYPEMAP
from pypy.module._rawffi.interp_rawffi import size_alignment
from pypy.module._rawffi.interp_rawffi import unpack_shape_with_length
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
    def __init__(self, basicffitype, size):
        # A W_Array represent the C type '*T', which can also represent
        # the type of pointers to arrays of T.  So the following fields
        # are used to describe T only.  It is 'basicffitype' possibly
        # repeated until reaching the length 'size'.
        self.basicffitype = basicffitype
        self.size = size
        self.alignment = size_alignment(basicffitype)[1]

    def allocate(self, space, length, autofree=False):
        if autofree:
            return W_ArrayInstanceAutoFree(space, self, length)
        return W_ArrayInstance(space, self, length)

    def get_basic_ffi_type(self):
        return self.basicffitype

    @unwrap_spec(length=int, autofree=bool)
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
                             self.itemcode, w_item)
        return space.wrap(result)

    def descr_repr(self, space):
        return space.wrap("<_rawffi.Array '%s' (%d, %d)>" % (self.itemcode,
                                                             self.size,
                                                             self.alignment))

    @unwrap_spec(address=r_uint, length=int)
    def fromaddress(self, space, address, length):
        return space.wrap(W_ArrayInstance(space, self, length, address))

PRIMITIVE_ARRAY_TYPES = {}
for _code in TYPEMAP:
    PRIMITIVE_ARRAY_TYPES[_code] = W_Array(TYPEMAP[_code],
                                           size_alignment(TYPEMAP[_code])[0])
    PRIMITIVE_ARRAY_TYPES[_code].itemcode = _code
ARRAY_OF_PTRS = PRIMITIVE_ARRAY_TYPES['P']

def descr_new_array(space, w_type, w_shape):
    return unpack_shape_with_length(space, w_shape)

W_Array.typedef = TypeDef(
    'Array',
    __new__  = interp2app(descr_new_array),
    __call__ = interp2app(W_Array.descr_call),
    __repr__ = interp2app(W_Array.descr_repr),
    fromaddress = interp2app(W_Array.fromaddress),
    size_alignment = interp2app(W_Array.descr_size_alignment)
)
W_Array.typedef.acceptable_as_base_class = False


class W_ArrayInstance(W_DataInstance):
    def __init__(self, space, shape, length, address=r_uint(0)):
        # Workaround for a strange behavior of libffi: make sure that
        # we always have at least 8 bytes.  For W_ArrayInstances that are
        # used as the result value of a function call, ffi_call() writes
        # 8 bytes into it even if the function's result type asks for less.
        # This strange behavior is documented.
        memsize = shape.size * length
        if memsize < 8:
            memsize = 8
        W_DataInstance.__init__(self, space, memsize, address)
        self.length = length
        self.shape = shape

    def descr_repr(self, space):
        addr = rffi.cast(lltype.Unsigned, self.ll_buffer)
        return space.wrap("<_rawffi array %x of length %d>" % (addr,
                                                               self.length))

    # This only allows non-negative indexes.  Arrays of shape 'c' also
    # support simple slices.

    def setitem(self, space, num, w_value):
        if not self.ll_buffer:
            raise segfault_exception(space, "setting element of freed array")
        if num >= self.length or num < 0:
            raise OperationError(space.w_IndexError, space.w_None)
        unwrap_value(space, push_elem, self.ll_buffer, num,
                     self.shape.itemcode, w_value)

    def descr_setitem(self, space, w_index, w_value):
        try:
            num = space.int_w(w_index)
        except OperationError, e:
            if not e.match(space, space.w_TypeError):
                raise
            self.setslice(space, w_index, w_value)
        else:
            self.setitem(space, num, w_value)

    def getitem(self, space, num):
        if not self.ll_buffer:
            raise segfault_exception(space, "accessing elements of freed array")
        if num >= self.length or num < 0:
            raise OperationError(space.w_IndexError, space.w_None)
        return wrap_value(space, get_elem, self.ll_buffer, num,
                          self.shape.itemcode)

    def descr_getitem(self, space, w_index):
        try:
            num = space.int_w(w_index)
        except OperationError, e:
            if not e.match(space, space.w_TypeError):
                raise
            return self.getslice(space, w_index)
        else:
            return self.getitem(space, num)

    def getlength(self, space):
        return space.wrap(self.length)

    @unwrap_spec(num=int)
    def descr_itemaddress(self, space, num):
        itemsize = self.shape.size
        ptr = rffi.ptradd(self.ll_buffer, itemsize * num)
        return space.wrap(rffi.cast(lltype.Unsigned, ptr))

    def getrawsize(self):
        itemsize = self.shape.size
        return itemsize * self.length

    def decodeslice(self, space, w_slice):
        if not space.is_true(space.isinstance(w_slice, space.w_slice)):
            raise OperationError(space.w_TypeError,
                                 space.wrap('index must be int or slice'))
        letter = self.shape.itemcode
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
    'ArrayInstanceAutoFree',
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
