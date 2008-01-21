
from pypy.interpreter.baseobjspace import W_Root, ObjSpace, Wrappable,\
     Arguments
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.module._rawffi.structure import unpack_fields
from pypy.module._rawffi.array import get_elem
from pypy.module._rawffi.interp_rawffi import W_DataInstance, _get_type_,\
     wrap_value, unwrap_value, unwrap_truncate_int
from pypy.rlib.libffi import USERDATA_P, CallbackFuncPtr

def callback(ll_args, ll_res, ll_userdata):
    userdata = rffi.cast(USERDATA_P, ll_userdata)
    callback_ptr = W_CallbackPtr.CallbackPtr_by_number[userdata.addarg]
    w_callable = callback_ptr.w_callable
    res = rffi.cast(rffi.VOIDPP, ll_res)
    argtypes = callback_ptr.args
    space = callback_ptr.space
    w_args = space.newlist([wrap_value(space, get_elem, ll_args[i], 0,
                                       (argtypes[i], None, None))
                            for i in range(len(argtypes))])
    w_res = space.call(w_callable, w_args)
    if space.is_w(w_res, space.w_None):
        res[0] = lltype.nullptr(rffi.VOIDP.TO)
    else:
        instance = space.interpclass_w(w_res)
        if isinstance(instance, W_DataInstance):
            res[0] = instance.ll_buffer
        else:
            res[0] = unwrap_truncate_int(rffi.VOIDP, space, w_res)

class W_CallbackPtr(W_DataInstance):
    # XXX some weird hackery to be able to recover W_CallbackPtr object
    #     out of number
    CallbackPtr_by_number = {}
    CallbackPtr_id = 0
    
    def __init__(self, space, w_callable, w_args, w_result):
        number = self.CallbackPtr_id
        self.CallbackPtr_id += 1
        self.CallbackPtr_by_number[number] = self
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
        self.ll_buffer = self.ll_callback.ll_closure

    def __del__(self):
        del self.CallbackPtr_by_number[self.number]

def descr_new_callbackptr(space, w_type, w_callable, w_args, w_result):
    return W_CallbackPtr(space, w_callable, w_args, w_result)

W_CallbackPtr.typedef = TypeDef(
    'CallbackPtr',
    __new__ = interp2app(descr_new_callbackptr),
    byptr   = interp2app(W_CallbackPtr.byptr),
)
