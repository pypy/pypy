"""
Callbacks.
"""
import os

from rpython.rlib import clibffi, rweakref, jit
from rpython.rlib.objectmodel import compute_unique_id, keepalive_until_here
from rpython.rtyper.lltypesystem import lltype, rffi

from pypy.interpreter.error import OperationError, oefmt
from pypy.module._cffi_backend import cerrno, misc
from pypy.module._cffi_backend.cdataobj import W_CData
from pypy.module._cffi_backend.ctypefunc import SIZE_OF_FFI_ARG, BIG_ENDIAN, W_CTypeFunc
from pypy.module._cffi_backend.ctypeprim import W_CTypePrimitiveSigned
from pypy.module._cffi_backend.ctypevoid import W_CTypeVoid

# ____________________________________________________________


class W_CDataCallback(W_CData):
    #_immutable_fields_ = ...
    ll_error = lltype.nullptr(rffi.CCHARP.TO)

    def __init__(self, space, ctype, w_callable, w_error):
        raw_closure = rffi.cast(rffi.CCHARP, clibffi.closureHeap.alloc())
        W_CData.__init__(self, space, raw_closure, ctype)
        #
        if not space.is_true(space.callable(w_callable)):
            raise oefmt(space.w_TypeError,
                        "expected a callable object, not %T", w_callable)
        self.w_callable = w_callable
        #
        fresult = self.getfunctype().ctitem
        size = fresult.size
        if size > 0:
            if fresult.is_primitive_integer and size < SIZE_OF_FFI_ARG:
                size = SIZE_OF_FFI_ARG
            self.ll_error = lltype.malloc(rffi.CCHARP.TO, size, flavor='raw',
                                          zero=True)
        if not space.is_none(w_error):
            convert_from_object_fficallback(fresult, self.ll_error, w_error)
        #
        self.unique_id = compute_unique_id(self)
        global_callback_mapping.set(self.unique_id, self)
        #
        cif_descr = self.getfunctype().cif_descr
        if not cif_descr:
            raise OperationError(space.w_NotImplementedError,
                                 space.wrap("callbacks with '...'"))
        res = clibffi.c_ffi_prep_closure(self.get_closure(), cif_descr.cif,
                                         invoke_callback,
                                         rffi.cast(rffi.VOIDP, self.unique_id))
        if rffi.cast(lltype.Signed, res) != clibffi.FFI_OK:
            raise OperationError(space.w_SystemError,
                space.wrap("libffi failed to build this callback"))
        #
        # We must setup the GIL here, in case the callback is invoked in
        # some other non-Pythonic thread.  This is the same as cffi on
        # CPython.
        if space.config.translation.thread:
            from pypy.module.thread.os_thread import setup_threads
            setup_threads(space)

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

    def getfunctype(self):
        ctype = self.ctype
        if not isinstance(ctype, W_CTypeFunc):
            space = self.space
            raise OperationError(space.w_TypeError,
                                 space.wrap("expected a function ctype"))
        return ctype

    @jit.unroll_safe
    def invoke(self, ll_args):
        space = self.space
        ctype = self.getfunctype()
        args_w = []
        for i, farg in enumerate(ctype.fargs):
            ll_arg = rffi.cast(rffi.CCHARP, ll_args[i])
            args_w.append(farg.convert_to_object(ll_arg))
        return space.call(self.w_callable, space.newtuple(args_w))

    def convert_result(self, ll_res, w_res):
        fresult = self.getfunctype().ctitem
        convert_from_object_fficallback(fresult, ll_res, w_res)

    def print_error(self, operr, extra_line):
        space = self.space
        operr.write_unraisable(space, "callback ", self.w_callable,
                               with_traceback=True, extra_line=extra_line)

    def write_error_return_value(self, ll_res):
        fresult = self.getfunctype().ctitem
        if fresult.size > 0:
            misc._raw_memcopy(self.ll_error, ll_res, fresult.size)
            keepalive_until_here(self)


global_callback_mapping = rweakref.RWeakValueDictionary(int, W_CDataCallback)


def convert_from_object_fficallback(fresult, ll_res, w_res):
    space = fresult.space
    small_result = fresult.size < SIZE_OF_FFI_ARG
    if small_result and isinstance(fresult, W_CTypeVoid):
        if not space.is_w(w_res, space.w_None):
            raise OperationError(space.w_TypeError,
                    space.wrap("callback with the return type 'void'"
                               " must return None"))
        return
    #
    if small_result and fresult.is_primitive_integer:
        # work work work around a libffi irregularity: for integer return
        # types we have to fill at least a complete 'ffi_arg'-sized result
        # buffer.
        if type(fresult) is W_CTypePrimitiveSigned:
            # It's probably fine to always zero-extend, but you never
            # know: maybe some code somewhere expects a negative
            # 'short' result to be returned into EAX as a 32-bit
            # negative number.  Better safe than sorry.  This code
            # is about that case.  Let's ignore this for enums.
            #
            # do a first conversion only to detect overflows.  This
            # conversion produces stuff that is otherwise ignored.
            fresult.convert_from_object(ll_res, w_res)
            #
            # manual inlining and tweaking of
            # W_CTypePrimitiveSigned.convert_from_object() in order
            # to write a whole 'ffi_arg'.
            value = misc.as_long(space, w_res)
            misc.write_raw_signed_data(ll_res, value, SIZE_OF_FFI_ARG)
            return
        else:
            # zero extension: fill the '*result' with zeros, and (on big-
            # endian machines) correct the 'result' pointer to write to
            misc._raw_memclear(ll_res, SIZE_OF_FFI_ARG)
            if BIG_ENDIAN:
                diff = SIZE_OF_FFI_ARG - fresult.size
                ll_res = rffi.ptradd(ll_res, diff)
    #
    fresult.convert_from_object(ll_res, w_res)


# ____________________________________________________________

STDERR = 2


@jit.jit_callback("CFFI")
def invoke_callback(ffi_cif, ll_res, ll_args, ll_userdata):
    """ Callback specification.
    ffi_cif - something ffi specific, don't care
    ll_args - rffi.VOIDPP - pointer to array of pointers to args
    ll_restype - rffi.VOIDP - pointer to result
    ll_userdata - a special structure which holds necessary information
                  (what the real callback is for example), casted to VOIDP
    """
    e = cerrno.get_real_errno()
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
        misc._raw_memclear(ll_res, SIZE_OF_FFI_ARG)
        return
    #
    ec = None
    try:
        ec = cerrno.get_errno_container(callback.space)
        cerrno.save_errno_into(ec, e)
        extra_line = ''
        try:
            w_res = callback.invoke(ll_args)
            extra_line = "Trying to convert the result back to C:\n"
            callback.convert_result(ll_res, w_res)
        except OperationError, e:
            # got an app-level exception
            callback.print_error(e, extra_line)
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
    if ec is not None:
        cerrno.restore_errno_from(ec)
