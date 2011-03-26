
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.module._rawffi.array import get_elem, push_elem
from pypy.module._rawffi.structure import W_Structure
from pypy.module._rawffi.interp_rawffi import W_DataInstance, letter2tp, \
     wrap_value, unwrap_value, unwrap_truncate_int, unpack_argshapes
from pypy.rlib.clibffi import USERDATA_P, CallbackFuncPtr, FUNCFLAG_CDECL
from pypy.rlib.clibffi import ffi_type_void
from pypy.rlib import rweakref
from pypy.module._rawffi.tracker import tracker
from pypy.interpreter.error import OperationError
from pypy.interpreter import gateway

app = gateway.applevel('''
    def tbprint(tb, err):
        import traceback, sys
        traceback.print_tb(tb)
        print >>sys.stderr, err
''', filename=__file__)

tbprint = app.interphook("tbprint")

def callback(ll_args, ll_res, ll_userdata):
    userdata = rffi.cast(USERDATA_P, ll_userdata)
    callback_ptr = global_counter.get(userdata.addarg)
    w_callable = callback_ptr.w_callable
    argtypes = callback_ptr.argtypes
    space = callback_ptr.space
    try:
        args_w = [None] * len(argtypes)
        for i in range(len(argtypes)):
            argtype = argtypes[i]
            if isinstance(argtype, W_Structure):
                args_w[i] = argtype.fromaddress(
                    space, rffi.cast(rffi.SIZE_T, ll_args[i]))
            else:
                # XXX other types?
                args_w[i] = space.wrap(rffi.cast(rffi.ULONG, ll_args[i]))
        w_res = space.call(w_callable, space.newtuple(args_w))
        if callback_ptr.result is not None: # don't return void
            unwrap_value(space, push_elem, ll_res, 0,
                         callback_ptr.result, w_res)
    except OperationError, e:
        tbprint(space, space.wrap(e.application_traceback),
                space.wrap(e.errorstr(space)))
        # force the result to be zero
        if callback_ptr.result is not None:
            resshape = letter2tp(space, callback_ptr.result)
            for i in range(resshape.size):
                ll_res[i] = '\x00'

class W_CallbackPtr(W_DataInstance):

    def __init__(self, space, w_callable, w_args, w_result,
                 flags=FUNCFLAG_CDECL):
        self.space = space
        self.w_callable = w_callable
        self.argtypes = unpack_argshapes(space, w_args)
        ffiargs = [tp.get_basic_ffi_type() for tp in self.argtypes]
        if not space.is_w(w_result, space.w_None):
            self.result = space.str_w(w_result)
            ffiresult = letter2tp(space, self.result).get_basic_ffi_type()
        else:
            self.result = None
            ffiresult = ffi_type_void
        self.number = global_counter.add(self)
        self.ll_callback = CallbackFuncPtr(ffiargs, ffiresult,
                                           callback, self.number, flags)
        self.ll_buffer = rffi.cast(rffi.VOIDP, self.ll_callback.ll_closure)
        if tracker.DO_TRACING:
            addr = rffi.cast(lltype.Signed, self.ll_callback.ll_closure)
            tracker.trace_allocation(addr, self)

    def free(self):
        if tracker.DO_TRACING:
            addr = rffi.cast(lltype.Signed, self.ll_callback.ll_closure)
            tracker.trace_free(addr)
        global_counter.remove(self.number)

# A global storage to be able to recover W_CallbackPtr object out of number
class GlobalCounter:
    def __init__(self):
        self.callback_id = 0
        self.callbacks = rweakref.RWeakValueDictionary(int, W_CallbackPtr)

    def add(self, w_callback):
        self.callback_id += 1
        id = self.callback_id
        self.callbacks.set(id, w_callback)
        return id

    def remove(self, id):
        self.callbacks.set(id, None)

    def get(self, id):
        return self.callbacks.get(id)

global_counter = GlobalCounter()

@unwrap_spec(flags=int)
def descr_new_callbackptr(space, w_type, w_callable, w_args, w_result,
                          flags=FUNCFLAG_CDECL):
    return W_CallbackPtr(space, w_callable, w_args, w_result, flags)

W_CallbackPtr.typedef = TypeDef(
    'CallbackPtr',
    __new__ = interp2app(descr_new_callbackptr),
    byptr   = interp2app(W_CallbackPtr.byptr),
    buffer  = GetSetProperty(W_CallbackPtr.getbuffer),
    free    = interp2app(W_CallbackPtr.free),
)
