
from pypy.interpreter.baseobjspace import W_Root, ObjSpace, Wrappable,\
     Arguments
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.module._rawffi.structure import unpack_fields
from pypy.module._rawffi.array import get_elem, push_elem
from pypy.module._rawffi.interp_rawffi import W_DataInstance, _get_type_,\
     wrap_value, unwrap_value, unwrap_truncate_int, letter2tp
from pypy.rlib.libffi import USERDATA_P, CallbackFuncPtr

def callback(ll_args, ll_res, ll_userdata):
    userdata = rffi.cast(USERDATA_P, ll_userdata)
    callback_ptr = global_counter.CallbackPtr_by_number[userdata.addarg]
    w_callable = callback_ptr.w_callable
    res = rffi.cast(rffi.VOIDPP, ll_res)
    argtypes = callback_ptr.args
    space = callback_ptr.space
    w_args = space.newlist([wrap_value(space, get_elem, ll_args[i], 0,
                                       letter2tp(space, argtypes[i]))
                            for i in range(len(argtypes))])
    w_res = space.call(w_callable, w_args)
    unwrap_value(space, push_elem, ll_res, 0,
                 letter2tp(space, callback_ptr.result), w_res)

# XXX some weird hackery to be able to recover W_CallbackPtr object
#     out of number    
class GlobalCounter:
    def __init__(self):
        self.CallbackPtr_id = 0
        self.CallbackPtr_by_number = {}

global_counter = GlobalCounter()

class W_CallbackPtr(W_DataInstance):
    global_counter = global_counter
    
    def __init__(self, space, w_callable, w_args, w_result):
        number = global_counter.CallbackPtr_id
        global_counter.CallbackPtr_id += 1
        global_counter.CallbackPtr_by_number[number] = self
        self.space = space
        self.w_callable = w_callable
        self.number = number
        self.args = [space.str_w(w_arg) for w_arg in space.unpackiterable(
            w_args)]
        self.result = space.str_w(w_result)
        ffiargs = [_get_type_(space, arg) for arg in self.args]
        ffiresult = _get_type_(space, self.result)
        # necessary to keep stuff alive
        self.ll_callback = CallbackFuncPtr(ffiargs, ffiresult,
                                           callback, number)
        self.ll_buffer = rffi.cast(rffi.VOIDP, self.ll_callback.ll_closure)

    #def free(self):
    #    del self.global_counter.CallbackPtr_by_number[self.number]

def descr_new_callbackptr(space, w_type, w_callable, w_args, w_result):
    return W_CallbackPtr(space, w_callable, w_args, w_result)

W_CallbackPtr.typedef = TypeDef(
    'CallbackPtr',
    __new__ = interp2app(descr_new_callbackptr),
    byptr   = interp2app(W_CallbackPtr.byptr),
    buffer  = GetSetProperty(W_CallbackPtr.getbuffer),
)
