
from pypy.interpreter.baseobjspace import W_Root, ObjSpace, Wrappable,\
     Arguments
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.module._rawffi.structure import unpack_fields
from pypy.module._rawffi.array import get_elem, push_elem
from pypy.module._rawffi.interp_rawffi import W_DataInstance, letter2tp, \
     wrap_value, unwrap_value, unwrap_truncate_int
from pypy.rlib.clibffi import USERDATA_P, CallbackFuncPtr, FUNCFLAG_CDECL
from pypy.rlib.clibffi import ffi_type_void
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
    callback_ptr = global_counter.CallbackPtr_by_number[userdata.addarg]
    w_callable = callback_ptr.w_callable
    args = callback_ptr.args
    space = callback_ptr.space
    try:
        # XXX The app-level callback gets the arguments as a list of integers.
        #     Irregular interface here.  Shows something, I say.
        w_args = space.newlist([space.wrap(rffi.cast(rffi.ULONG, ll_args[i]))
                                for i in range(len(args))])
        w_res = space.call(w_callable, w_args)
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

# XXX some weird hackery to be able to recover W_CallbackPtr object
#     out of number    
class GlobalCounter:
    def __init__(self):
        self.CallbackPtr_id = 0
        self.CallbackPtr_by_number = {}

global_counter = GlobalCounter()

class W_CallbackPtr(W_DataInstance):
    global_counter = global_counter
    
    def __init__(self, space, w_callable, w_args, w_result,
                 flags=FUNCFLAG_CDECL):
        self.space = space
        self.w_callable = w_callable
        self.args = [space.str_w(w_arg) for w_arg in space.unpackiterable(
            w_args)]
        ffiargs = [letter2tp(space, x).get_basic_ffi_type() for x in self.args]
        if not space.is_w(w_result, space.w_None):
            self.result = space.str_w(w_result)
            ffiresult = letter2tp(space, self.result).get_basic_ffi_type()
        else:
            self.result = None
            ffiresult = ffi_type_void
        # necessary to keep stuff alive
        number = global_counter.CallbackPtr_id
        global_counter.CallbackPtr_id += 1
        global_counter.CallbackPtr_by_number[number] = self
        self.number = number
        self.ll_callback = CallbackFuncPtr(ffiargs, ffiresult,
                                           callback, number, flags)
        self.ll_buffer = rffi.cast(rffi.VOIDP, self.ll_callback.ll_closure)
        if tracker.DO_TRACING:
            addr = rffi.cast(lltype.Signed, self.ll_callback.ll_closure)
            tracker.trace_allocation(addr, self)

    def free(self):
        if tracker.DO_TRACING:
            addr = rffi.cast(lltype.Signed, self.ll_callback.ll_closure)
            tracker.trace_free(addr)
        del self.global_counter.CallbackPtr_by_number[self.number]
    free.unwrap_spec = ['self']

def descr_new_callbackptr(space, w_type, w_callable, w_args, w_result,
                          flags=FUNCFLAG_CDECL):
    return W_CallbackPtr(space, w_callable, w_args, w_result, flags)
descr_new_callbackptr.unwrap_spec = [ObjSpace, W_Root, W_Root, W_Root, W_Root,
                                     int]

W_CallbackPtr.typedef = TypeDef(
    'CallbackPtr',
    __new__ = interp2app(descr_new_callbackptr),
    byptr   = interp2app(W_CallbackPtr.byptr),
    buffer  = GetSetProperty(W_CallbackPtr.getbuffer),
    free    = interp2app(W_CallbackPtr.free),
)
