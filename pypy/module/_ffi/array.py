
""" Interpreter-level implementation of array, exposing ll-structure
to app-level with apropriate interface
"""

from pypy.interpreter.baseobjspace import W_Root, ObjSpace, Wrappable,\
     Arguments
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.interpreter.error import OperationError, wrap_oserror
from pypy.module._ffi.structure import native_fmttable
from pypy.module._ffi.interp_ffi import unwrap_value, wrap_value, _get_type

def push_elem(ll_array, pos, value):
    TP = lltype.typeOf(value)
    ll_array = rffi.cast(lltype.Ptr(rffi.CArray(TP)), ll_array)
    ll_array[pos] = value
push_elem._annspecialcase_ = 'specialize:argtype(2)'

def get_elem(ll_array, pos, ll_t):
    ll_array = rffi.cast(lltype.Ptr(rffi.CArray(ll_t)), ll_array)
    return ll_array[pos]
get_elem._annspecialcase_ = 'specialize:arg(2)'

class W_ArrayInstance(Wrappable):
    def __init__(self, space, of, length):
        self.alloced = False
        self.of = of
        _get_type(space, of)
        self.length = length
        size = native_fmttable[of]['size'] * length
        self.ll_array = lltype.malloc(rffi.VOIDP.TO, size, flavor='raw',
                                      zero=True)
        self.alloced = True

    # XXX don't allow negative indexes, nor slices

    def setitem(self, space, num, w_value):
        if num >= self.length or num < 0:
            raise OperationError(space.w_ValueError, space.wrap(
                "Setting element %d of array sized %d" % (num, self.length)))
        unwrap_value(space, push_elem, self.ll_array, num, self.of, w_value,
                   None)
    setitem.unwrap_spec = ['self', ObjSpace, int, W_Root]

    def getitem(self, space, num):
        if num >= self.length or num < 0:
            raise OperationError(space.w_ValueError, space.wrap(
                "Getting element %d of array sized %d" % (num, self.length)))
        return wrap_value(space, get_elem, self.ll_array, num, self.of)
    getitem.unwrap_spec = ['self', ObjSpace, int]

    def getbuffer(space, self):
        return space.wrap(rffi.cast(rffi.INT, self.ll_array))

    def __del__(self):
        if self.alloced:
            lltype.free(self.ll_array, flavor='raw')

def descr_new_array_instance(space, w_type, of, size):
    return space.wrap(W_ArrayInstance(space, of, size))
descr_new_array_instance.unwrap_spec = [ObjSpace, W_Root, str, int]

W_ArrayInstance.typedef = TypeDef(
    'ArrayInstance',
    __new__     = interp2app(descr_new_array_instance),
    __setitem__ = interp2app(W_ArrayInstance.setitem),
    __getitem__ = interp2app(W_ArrayInstance.getitem),
    buffer      = GetSetProperty(W_ArrayInstance.getbuffer),
)
