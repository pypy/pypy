import sys
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib import clibffi


FFI_CIF = clibffi.FFI_CIFP.TO
FFI_TYPE = clibffi.FFI_TYPE_P.TO
FFI_TYPE_P = clibffi.FFI_TYPE_P
FFI_TYPE_PP = clibffi.FFI_TYPE_PP
SIZE_OF_FFI_ARG = rffi.sizeof(clibffi.ffi_arg)

# "cif_description" is a block of raw memory describing how to do the call.
# It starts with a block of memory of type FFI_CIF, which is used by libffi
# itself.  Following it, we find jit_libffi-specific information:
#
#  - 'exchange_size': an integer that tells how big a buffer we must
#    allocate for the call; this buffer should have enough room at the
#    beginning for an array of pointers to the actual argument values,
#    which is initialized internally by jit_ffi_call().
#
#  - 'exchange_result': the offset in that buffer for the result of the call.
#
#  - 'exchange_result_libffi': the actual offset passed to ffi_call().
#    Differs on big-endian machines if the result is an integer type smaller
#    than SIZE_OF_FFI_ARG (blame libffi).
#
#  - 'exchange_args[nargs]': the offset in that buffer for each argument.

CIF_DESCRIPTION = lltype.Struct(
    'CIF_DESCRIPTION',
    ('cif', FFI_CIF),
    ('exchange_size', lltype.Signed),
    ('exchange_result', lltype.Signed),
    ('exchange_result_libffi', lltype.Signed),
    ('exchange_nb_args', lltype.Signed),
    ('exchange_args', lltype.Array(lltype.Signed,
                          hints={'nolength': True, 'immutable': True})),
    hints={'immutable': True})

CIF_DESCRIPTION_P = lltype.Ptr(CIF_DESCRIPTION)


def jit_ffi_call(cif_description, func_addr, exchange_buffer):
    """Wrapper around ffi_call().  Must receive a CIF_DESCRIPTION_P that
    describes the layout of the 'exchange_buffer' of size 'exchange_size'.
    """
    buffer_array = rffi.cast(rffi.VOIDPP, exchange_buffer)
    for i in range(cif_description.exchange_nb_args):
        data = rffi.ptradd(exchange_buffer, cif_description.exchange_args[i])
        buffer_array[i] = data
    resultdata = rffi.ptradd(exchange_buffer,
                             cif_description.exchange_result_libffi)
    clibffi.c_ffi_call(cif_description.cif, func_addr,
                       rffi.cast(rffi.VOIDP, resultdata),
                       buffer_array)
