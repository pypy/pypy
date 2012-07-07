"""
Callbacks.
"""
import os
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rlib.objectmodel import compute_unique_id, keepalive_until_here
from pypy.rlib import clibffi, rweakref, rgc

from pypy.module._cffi_backend.cdataobj import W_CData, W_CDataApplevelOwning
from pypy.module._cffi_backend.ctypefunc import SIZE_OF_FFI_ARG

# ____________________________________________________________


class W_CDataCallback(W_CDataApplevelOwning):
    _immutable_ = True
    ll_error = lltype.nullptr(rffi.CCHARP.TO)

    def __init__(self, space, ctype, w_callable, w_error):
        raw_closure = rffi.cast(rffi.CCHARP, clibffi.closureHeap.alloc())
        W_CData.__init__(self, space, raw_closure, ctype)
        #
        if not space.is_true(space.callable(w_callable)):
            raise operationerrfmt(space.w_TypeError,
                                  "expected a callable object, not %s",
                                  space.type(w_callable).getname(space))
        self.w_callable = w_callable
        self.w_error = w_error
        #
        fresult = self.ctype.ctitem
        size = fresult.size
        if size > 0:
            self.ll_error = lltype.malloc(rffi.CCHARP.TO, size, flavor='raw',
                                          zero=True)
        if not space.is_w(w_error, space.w_None):
            fresult.convert_from_object(self.ll_error, w_error)
        #
        self.unique_id = compute_unique_id(self)
        global_callback_mapping.set(self.unique_id, self)
        #
        cif_descr = ctype.cif_descr
        if not cif_descr:
            raise OperationError(space.w_NotImplementedError,
                                 space.wrap("callbacks with '...'"))
        res = clibffi.c_ffi_prep_closure(self.get_closure(), cif_descr.cif,
                                         invoke_callback,
                                         rffi.cast(rffi.VOIDP, self.unique_id))
        if rffi.cast(lltype.Signed, res) != clibffi.FFI_OK:
            raise OperationError(space.w_SystemError,
                space.wrap("libffi failed to build this callback"))

    def get_closure(self):
        return rffi.cast(clibffi.FFI_CLOSUREP, self._cdata)

    #@rgc.must_be_light_finalizer
    def __del__(self):
        clibffi.closureHeap.free(self.get_closure())
        if self.ll_error:
            lltype.free(self.ll_error, flavor='raw')

    def _repr_extra(self):
        space = self.space
        return 'calling ' + space.str_w(space.repr(self.w_callable))

    def invoke(self, ll_args, ll_res):
        space = self.space
        ctype = self.ctype
        args_w = []
        for i, farg in enumerate(ctype.fargs):
            ll_arg = rffi.cast(rffi.CCHARP, ll_args[i])
            args_w.append(farg.convert_to_object(ll_arg))
        fresult = ctype.ctitem
        #
        w_res = space.call(self.w_callable, space.newtuple(args_w))
        #
        if fresult.size > 0:
            fresult.convert_from_object(ll_res, w_res)

    def print_error(self, operr):
        space = self.space
        operr.write_unraisable(space, "in cffi callback", self.w_callable)

    def write_error_return_value(self, ll_res):
        fresult = self.ctype.ctitem
        if fresult.size > 0:
            # push push push at the llmemory interface (with hacks that
            # are all removed after translation)
            zero = llmemory.itemoffsetof(rffi.CCHARP.TO, 0)
            llmemory.raw_memcopy(llmemory.cast_ptr_to_adr(self.ll_error) +zero,
                                 llmemory.cast_ptr_to_adr(ll_res) + zero,
                                 fresult.size * llmemory.sizeof(lltype.Char))
            keepalive_until_here(self)


global_callback_mapping = rweakref.RWeakValueDictionary(int, W_CDataCallback)


# ____________________________________________________________

STDERR = 2

def invoke_callback(ffi_cif, ll_res, ll_args, ll_userdata):
    """ Callback specification.
    ffi_cif - something ffi specific, don't care
    ll_args - rffi.VOIDPP - pointer to array of pointers to args
    ll_restype - rffi.VOIDP - pointer to result
    ll_userdata - a special structure which holds necessary information
                  (what the real callback is for example), casted to VOIDP
    """
    ll_res = rffi.cast(rffi.CCHARP, ll_res)
    unique_id = rffi.cast(lltype.Signed, ll_userdata)
    callback = global_callback_mapping.get(unique_id)
    if callback is None:
        # oups!
        try:
            os.write(STDERR, "SystemError: invoking a callback "
                             "that was already freed\n")
        except OSError:
            pass
        # In this case, we don't even know how big ll_res is.  Let's assume
        # it is just a 'ffi_arg', and store 0 there.
        llmemory.raw_memclear(llmemory.cast_ptr_to_adr(ll_res),
                              SIZE_OF_FFI_ARG)
        return
    #
    try:
        try:
            callback.invoke(ll_args, ll_res)
        except OperationError, e:
            # got an app-level exception
            callback.print_error(e)
            callback.write_error_return_value(ll_res)
        #
    except Exception, e:
        # oups! last-level attempt to recover.
        try:
            os.write(STDERR, "SystemError: callback raised ")
            os.write(STDERR, str(e))
            os.write(STDERR, "\n")
        except OSError:
            pass
        callback.write_error_return_value(ll_res)
