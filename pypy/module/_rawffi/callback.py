
from pypy.interpreter.baseobjspace import W_Root, ObjSpace, Wrappable,\
     Arguments
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.module._rawffi.structure import unpack_fields

def stuff(a, b):
    print "comparing"
    return int(a > b)

class W_CallbackPtr(Wrappable):
    def __init__(self, space, w_callable, w_args, w_result):
        self.w_callable = w_callable
        self.args = [space.str_w(w_arg) for w_arg in space.unpackiterable(
            w_args)]

    def getllfuncptr(space, self):
        TP = lltype.FuncType([lltype.Signed, lltype.Signed], lltype.Signed)
        ptr = lltype.functionptr(TP, stuff)
        return space.wrap(rffi.cast(rffi.Unsigned, ptr))

def descr_new_callbackptr(space, w_type, w_callable, w_args, w_result):
    return W_CallbackPtr(space, w_callable, w_args, w_result)

W_CallbackPtr.typedef = TypeDef(
    'CallbackPtr',
    buffer  = GetSetProperty(W_CallbackPtr.getllfuncptr),
    __new__ = interp2app(descr_new_callbackptr),
)
