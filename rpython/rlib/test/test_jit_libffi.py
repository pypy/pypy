import math
import ctypes
import sys
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib import clibffi
from rpython.rlib.rarithmetic import intmask
from rpython.rlib.jit_libffi import CIF_DESCRIPTION
from rpython.rlib.jit_libffi import jit_ffi_prep_cif, jit_ffi_prep_cif_var
from rpython.rlib.jit_libffi import jit_ffi_call

if sys.platform == 'win32':
    math_sin = intmask(ctypes.cast(ctypes.cdll.msvcrt.sin, ctypes.c_void_p).value)
else:    
    math_sin = intmask(ctypes.cast(ctypes.CDLL(None).sin, ctypes.c_void_p).value)
math_sin = rffi.cast(rffi.VOIDP, math_sin)

if sys.platform == 'win32':
    _snprintf = ctypes.cdll.msvcrt._snprintf
else:
    _snprintf = ctypes.CDLL(None).snprintf
c_snprintf = rffi.cast(rffi.VOIDP,
                       intmask(ctypes.cast(_snprintf, ctypes.c_void_p).value))


def test_jit_ffi_call():
    cd = lltype.malloc(CIF_DESCRIPTION, 1, flavor='raw')
    cd.abi = clibffi.FFI_DEFAULT_ABI
    cd.nargs = 1
    cd.rtype = clibffi.cast_type_to_ffitype(rffi.DOUBLE)
    atypes = lltype.malloc(clibffi.FFI_TYPE_PP.TO, 1, flavor='raw')
    atypes[0] = clibffi.cast_type_to_ffitype(rffi.DOUBLE)
    cd.atypes = atypes
    cd.exchange_size = 64    # 64 bytes of exchange data
    cd.exchange_result = 24
    cd.exchange_args[0] = 16
    #
    jit_ffi_prep_cif(cd)
    #
    assert rffi.sizeof(rffi.DOUBLE) == 8
    exb = lltype.malloc(rffi.DOUBLEP.TO, 8, flavor='raw')
    exb[2] = 1.23
    jit_ffi_call(cd, math_sin, rffi.cast(rffi.CCHARP, exb))
    res = exb[3]
    lltype.free(exb, flavor='raw')
    #
    lltype.free(atypes, flavor='raw')
    lltype.free(cd, flavor='raw')
    #
    assert res == math.sin(1.23)


def test_jit_ffi_call_var():
    # snprintf(buf, 32, "<%d>", 42): three declared arguments, then the
    # variadic part.  On some ABIs (arm64 on macOS/iOS) the variadic
    # arguments are passed differently, so ffi_prep_cif_var() is required.
    cd = lltype.malloc(CIF_DESCRIPTION, 4, flavor='raw')
    cd.abi = clibffi.FFI_DEFAULT_ABI
    cd.nargs = 4
    cd.rtype = clibffi.cast_type_to_ffitype(rffi.INT)
    atypes = lltype.malloc(clibffi.FFI_TYPE_PP.TO, 4, flavor='raw')
    atypes[0] = clibffi.ffi_type_pointer
    atypes[1] = clibffi.cast_type_to_ffitype(rffi.ULONG)   # size_t
    atypes[2] = clibffi.ffi_type_pointer
    atypes[3] = clibffi.cast_type_to_ffitype(rffi.INT)
    cd.atypes = atypes
    cd.exchange_size = 72
    cd.exchange_result = 64
    cd.exchange_args[0] = 32
    cd.exchange_args[1] = 40
    cd.exchange_args[2] = 48
    cd.exchange_args[3] = 56
    #
    res = jit_ffi_prep_cif_var(cd, 3)
    assert res == clibffi.FFI_OK
    #
    buf = lltype.malloc(rffi.CCHARP.TO, 32, flavor='raw', zero=True)
    fmt = rffi.str2charp("<%d>")
    exb = lltype.malloc(rffi.CCHARP.TO, cd.exchange_size, flavor='raw',
                        zero=True)
    rffi.cast(rffi.VOIDPP, rffi.ptradd(exb, 32))[0] = rffi.cast(rffi.VOIDP, buf)
    rffi.cast(rffi.CArrayPtr(rffi.ULONG),
              rffi.ptradd(exb, 40))[0] = rffi.cast(rffi.ULONG, 32)
    rffi.cast(rffi.VOIDPP, rffi.ptradd(exb, 48))[0] = rffi.cast(rffi.VOIDP, fmt)
    rffi.cast(rffi.INTP, rffi.ptradd(exb, 56))[0] = rffi.cast(rffi.INT, 42)
    #
    jit_ffi_call(cd, c_snprintf, exb)
    #
    count = intmask(rffi.cast(rffi.INTP, rffi.ptradd(exb, 64))[0])
    result = rffi.charp2str(buf)
    #
    lltype.free(exb, flavor='raw')
    lltype.free(fmt, flavor='raw')
    lltype.free(buf, flavor='raw')
    lltype.free(atypes, flavor='raw')
    lltype.free(cd, flavor='raw')
    #
    assert result == "<42>"
    assert count == 4
