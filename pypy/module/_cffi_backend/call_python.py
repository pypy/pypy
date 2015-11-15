import os
from rpython.rlib.objectmodel import specialize, instantiate
from rpython.rlib.rarithmetic import intmask
from rpython.rlib import jit
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper.annlowlevel import llhelper

from pypy.interpreter.error import oefmt
from pypy.interpreter.gateway import interp2app
from pypy.module._cffi_backend import parse_c_type
from pypy.module._cffi_backend import cerrno
from pypy.module._cffi_backend import cffi_opcode
from pypy.module._cffi_backend import realize_c_type
from pypy.module._cffi_backend.realize_c_type import getop, getarg


STDERR = 2
CALLPY_FN = lltype.FuncType([parse_c_type.PCALLPY, rffi.CCHARP],
                            lltype.Void)


def get_printable_location(callpython):
    with callpython as ptr:
        callpy = rffi.cast(parse_c_type.PCALLPY, ptr)
        return 'cffi_call_python ' + rffi.charp2str(callpy.g_name)

jitdriver = jit.JitDriver(name='cffi_call_python',
                          greens=['callpython'],
                          reds=['ll_args'],
                          get_printable_location=get_printable_location)

def py_invoke_callpython(callpython, ll_args):
    jitdriver.jit_merge_point(callpython=callpython, ll_args=ll_args)
    # the same buffer is used both for passing arguments and the result value
    callpython.do_invoke(ll_args, ll_args)


def _cffi_call_python(ll_callpy, ll_args):
    """Invoked by the helpers generated from CFFI_CALL_PYTHON in the cdef.

       'callpy' is a static structure that describes which of the
       CFFI_CALL_PYTHON is called.  It has got fields 'name' and
       'type_index' describing the function, and more reserved fields
       that are initially zero.  These reserved fields are set up by
       ffi.call_python(), which invokes init_call_python() below.

       'args' is a pointer to an array of 8-byte entries.  Each entry
       contains an argument.  If an argument is less than 8 bytes, only
       the part at the beginning of the entry is initialized.  If an
       argument is 'long double' or a struct/union, then it is passed
       by reference.

       'args' is also used as the place to write the result to.  In all
       cases, 'args' is at least 8 bytes in size.
    """
    from pypy.module._cffi_backend.ccallback import reveal_callback

    cerrno._errno_after(rffi.RFFI_ERR_ALL | rffi.RFFI_ALT_ERRNO)

    if not ll_callpy.c_reserved1:
        # Not initialized!  We don't have a space at all, so just
        # write the error to the file descriptor stderr.  (xxx cpython's
        # cffi writes it to sys.stderr)
        try:
            funcname = rffi.charp2str(ll_callpy.c_name)
            msg = ("CFFI_CALL_PYTHON: function %s() called, but no code was "
                   "attached to it yet with ffi.call_python('%s').  "
                   "Returning 0.\n" % (funcname, funcname))
            os.write(STDERR, msg)
        except:
            pass
        for i in range(intmask(ll_callpy.c_size_of_result)):
            ll_args[i] = '\x00'
    else:
        callpython = reveal_callback(ll_callpy.c_reserved1)
        space = callpython.space
        must_leave = False
        try:
            must_leave = space.threadlocals.try_enter_thread(space)
            py_invoke_callpython(callpython, ll_args)
            #
        except Exception, e:
            # oups! last-level attempt to recover.
            try:
                os.write(STDERR, "SystemError: call_python function raised ")
                os.write(STDERR, str(e))
                os.write(STDERR, "\n")
            except:
                pass
            callpython.write_error_return_value(ll_res)
        if must_leave:
            space.threadlocals.leave_thread(space)

    cerrno._errno_before(rffi.RFFI_ERR_ALL | rffi.RFFI_ALT_ERRNO)


def get_ll_cffi_call_python():
    return llhelper(lltype.Ptr(CALLPY_FN), _cffi_call_python)


class Cache:
    def __init__(self, space):
        self.cache_dict = {}


def callpy_deco(space, w_ffi, w_python_callable, w_name, w_error, w_onerror):
    from pypy.module._cffi_backend.ffi_obj import W_FFIObject
    from pypy.module._cffi_backend.ccallback import W_CallPython

    ffi = space.interp_w(W_FFIObject, w_ffi)

    if space.is_w(w_name, space.w_None):
        XXX
    else:
        name = space.str_w(w_name)

    ctx = ffi.ctxobj.ctx
    index = parse_c_type.search_in_globals(ctx, name)
    if index < 0:
        raise callpy_not_found(ffi, name)

    g = ctx.c_globals[index]
    if getop(g.c_type_op) != cffi_opcode.OP_CALL_PYTHON:
        raise callpy_not_found(ffi, name)

    w_ct = realize_c_type.realize_c_type(ffi, ctx.c_types, getarg(g.c_type_op))

    # make a W_CallPython instance, which is nonmovable; then cast it
    # to a raw pointer and assign it to the field 'reserved1' of the
    # callpy object from C.  We must make sure to keep it alive forever,
    # or at least until ffi.call_python() is used again to change the
    # binding.  Note that the W_CallPython is never exposed to the user.
    callpy = rffi.cast(parse_c_type.PCALLPY, g.c_address)
    callpython = instantiate(W_CallPython, nonmovable=True)
    callpython.__init__(space, rffi.cast(rffi.CCHARP, callpy), w_ct,
                        w_python_callable, w_error, w_onerror)

    key = rffi.cast(lltype.Signed, callpy)
    space.fromcache(Cache).cache_dict[key] = callpython
    callpy.c_reserved1 = rffi.cast(rffi.CCHARP, callpython.hide_object())

    # return a cdata of type function-pointer, equal to the one
    # obtained by reading 'lib.bar' (see lib_obj.py)
    ptr = lltype.direct_fieldptr(g, 'c_size_or_direct_fn')
    return w_ct.convert_to_object(rffi.cast(rffi.CCHARP, ptr))


def callpy_not_found(ffi, name):
    raise oefmt(ffi.w_FFIError,
                "ffi.call_python('%s'): name not found as a "
                "CFFI_CALL_PYTHON line from the cdef", name)

@specialize.memo()
def get_generic_decorator(space):
    return space.wrap(interp2app(callpy_deco))
