"""
Callbacks.
"""
import sys, os, py

from rpython.rlib import clibffi, jit, jit_libffi, rgc, objectmodel
from rpython.rlib.objectmodel import keepalive_until_here
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi

from pypy.interpreter.error import OperationError, oefmt
from pypy.module._cffi_backend import cerrno, misc
from pypy.module._cffi_backend.cdataobj import W_CData
from pypy.module._cffi_backend.ctypefunc import SIZE_OF_FFI_ARG, W_CTypeFunc
from pypy.module._cffi_backend.ctypeprim import W_CTypePrimitiveSigned
from pypy.module._cffi_backend.ctypevoid import W_CTypeVoid

BIG_ENDIAN = sys.byteorder == 'big'

# ____________________________________________________________


@jit.dont_look_inside
def make_callback(space, ctype, w_callable, w_error, w_onerror):
    # Allocate a callback as a nonmovable W_CDataCallback instance, which
    # we can cast to a plain VOIDP.  As long as the object is not freed,
    # we can cast the VOIDP back to a W_CDataCallback in reveal_callback().
    cdata = objectmodel.instantiate(W_CDataCallback, nonmovable=True)
    gcref = rgc.cast_instance_to_gcref(cdata)
    raw_cdata = rgc.hide_nonmovable_gcref(gcref)
    cdata.__init__(space, ctype, w_callable, w_error, w_onerror, raw_cdata)
    return cdata

def reveal_callback(raw_ptr):
    addr = rffi.cast(llmemory.Address, raw_ptr)
    gcref = rgc.reveal_gcref(addr)
    return rgc.try_cast_gcref_to_instance(W_CDataCallback, gcref)


class Closure(object):
    """This small class is here to have a __del__ outside any cycle."""

    ll_error = lltype.nullptr(rffi.CCHARP.TO)     # set manually

    def __init__(self, ptr):
        self.ptr = ptr

    def __del__(self):
        clibffi.closureHeap.free(rffi.cast(clibffi.FFI_CLOSUREP, self.ptr))
        if self.ll_error:
            lltype.free(self.ll_error, flavor='raw')


class W_CDataCallback(W_CData):
    _immutable_fields_ = ['key_pycode']
    w_onerror = None

    def __init__(self, space, ctype, w_callable, w_error, w_onerror,
                 raw_cdata):
        raw_closure = rffi.cast(rffi.CCHARP, clibffi.closureHeap.alloc())
        self._closure = Closure(raw_closure)
        W_CData.__init__(self, space, raw_closure, ctype)
        #
        if not space.is_true(space.callable(w_callable)):
            raise oefmt(space.w_TypeError,
                        "expected a callable object, not %T", w_callable)
        self.w_callable = w_callable
        self.key_pycode = space._try_fetch_pycode(w_callable)
        if not space.is_none(w_onerror):
            if not space.is_true(space.callable(w_onerror)):
                raise oefmt(space.w_TypeError,
                            "expected a callable object for 'onerror', not %T",
                            w_onerror)
            self.w_onerror = w_onerror
        #
        fresult = self.getfunctype().ctitem
        size = fresult.size
        if size > 0:
            if fresult.is_primitive_integer and size < SIZE_OF_FFI_ARG:
                size = SIZE_OF_FFI_ARG
            self._closure.ll_error = lltype.malloc(rffi.CCHARP.TO, size,
                                                   flavor='raw', zero=True)
        if not space.is_none(w_error):
            convert_from_object_fficallback(fresult, self._closure.ll_error,
                                            w_error)
        #
        # We must setup the GIL here, in case the callback is invoked in
        # some other non-Pythonic thread.  This is the same as cffi on
        # CPython.
        if space.config.translation.thread:
            from pypy.module.thread.os_thread import setup_threads
            setup_threads(space)
        #
        cif_descr = self.getfunctype().cif_descr
        if not cif_descr:
            raise oefmt(space.w_NotImplementedError,
                        "%s: callback with unsupported argument or "
                        "return type or with '...'", self.getfunctype().name)
        with self as ptr:
            closure_ptr = rffi.cast(clibffi.FFI_CLOSUREP, ptr)
            unique_id = rffi.cast(rffi.VOIDP, raw_cdata)
            res = clibffi.c_ffi_prep_closure(closure_ptr, cif_descr.cif,
                                             invoke_callback,
                                             unique_id)
        if rffi.cast(lltype.Signed, res) != clibffi.FFI_OK:
            raise OperationError(space.w_SystemError,
                space.wrap("libffi failed to build this callback"))

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
        ctype = jit.promote(ctype)
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
        operr.write_unraisable(space, "cffi callback ", self.w_callable,
                               with_traceback=True, extra_line=extra_line)

    def write_error_return_value(self, ll_res):
        fresult = self.getfunctype().ctitem
        if fresult.size > 0:
            misc._raw_memcopy(self._closure.ll_error, ll_res, fresult.size)
            keepalive_until_here(self)   # to keep self._closure.ll_error alive


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


@jit.dont_look_inside
def _handle_applevel_exception(callback, e, ll_res, extra_line):
    space = callback.space
    callback.write_error_return_value(ll_res)
    if callback.w_onerror is None:
        callback.print_error(e, extra_line)
    else:
        try:
            e.normalize_exception(space)
            w_t = e.w_type
            w_v = e.get_w_value(space)
            w_tb = space.wrap(e.get_traceback())
            w_res = space.call_function(callback.w_onerror,
                                        w_t, w_v, w_tb)
            if not space.is_none(w_res):
                callback.convert_result(ll_res, w_res)
        except OperationError, e2:
            # double exception! print a double-traceback...
            callback.print_error(e, extra_line)    # original traceback
            e2.write_unraisable(space, '', with_traceback=True,
                                extra_line="\nDuring the call to 'onerror', "
                                           "another exception occurred:\n\n")

def get_printable_location(key_pycode):
    if key_pycode is None:
        return 'cffi_callback <?>'
    return 'cffi_callback ' + key_pycode.get_repr()

jitdriver = jit.JitDriver(name='cffi_callback',
                          greens=['callback.key_pycode'],
                          reds=['ll_res', 'll_args', 'callback'],
                          get_printable_location=get_printable_location)

def py_invoke_callback(callback, ll_res, ll_args):
    jitdriver.jit_merge_point(callback=callback, ll_res=ll_res, ll_args=ll_args)
    extra_line = ''
    try:
        w_res = callback.invoke(ll_args)
        extra_line = "Trying to convert the result back to C:\n"
        callback.convert_result(ll_res, w_res)
    except OperationError, e:
        _handle_applevel_exception(callback, e, ll_res, extra_line)

def _invoke_callback(ffi_cif, ll_res, ll_args, ll_userdata):
    """ Callback specification.
    ffi_cif - something ffi specific, don't care
    ll_args - rffi.VOIDPP - pointer to array of pointers to args
    ll_res - rffi.VOIDP - pointer to result
    ll_userdata - a special structure which holds necessary information
                  (what the real callback is for example), casted to VOIDP
    """
    ll_res = rffi.cast(rffi.CCHARP, ll_res)
    callback = reveal_callback(ll_userdata)
    if callback is None:
        # oups!
        try:
            os.write(STDERR, "SystemError: invoking a callback "
                             "that was already freed\n")
        except:
            pass
        # In this case, we don't even know how big ll_res is.  Let's assume
        # it is just a 'ffi_arg', and store 0 there.
        misc._raw_memclear(ll_res, SIZE_OF_FFI_ARG)
        return
    #
    space = callback.space
    must_leave = False
    try:
        must_leave = space.threadlocals.try_enter_thread(space)
        py_invoke_callback(callback, ll_res, ll_args)
        #
    except Exception, e:
        # oups! last-level attempt to recover.
        try:
            os.write(STDERR, "SystemError: callback raised ")
            os.write(STDERR, str(e))
            os.write(STDERR, "\n")
        except:
            pass
        callback.write_error_return_value(ll_res)
    if must_leave:
        space.threadlocals.leave_thread(space)

def invoke_callback(ffi_cif, ll_res, ll_args, ll_userdata):
    cerrno._errno_after(rffi.RFFI_ERR_ALL | rffi.RFFI_ALT_ERRNO)
    _invoke_callback(ffi_cif, ll_res, ll_args, ll_userdata)
    cerrno._errno_before(rffi.RFFI_ERR_ALL | rffi.RFFI_ALT_ERRNO)
