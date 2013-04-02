from rpython.rtyper.lltypesystem import rffi, lltype

# There are two possible ways of accessing the backend through the reflection
# C-API: built it into pypy-c, or load it dynamically. The latter is preferred
# (and is the default) for use with Reflex. B/c of some builtin pythonizations,
# the former is recommended (for now) with CINT.

# Note: if builtin_capi is chosen, then inside builtin_capi.py, there is still
# the selection of the desired backend (default is Reflex).

# choose C-API access method:
from loadable_capi import *
#from builtin_capi import *

# shared definitions
_C_OPAQUE_PTR = rffi.LONG
_C_OPAQUE_NULL = lltype.nullptr(rffi.LONGP.TO)# ALT: _C_OPAQUE_PTR.TO

C_SCOPE = _C_OPAQUE_PTR
C_NULL_SCOPE = rffi.cast(C_SCOPE, _C_OPAQUE_NULL)

C_TYPE = C_SCOPE
C_NULL_TYPE = C_NULL_SCOPE

C_OBJECT = _C_OPAQUE_PTR
C_NULL_OBJECT = rffi.cast(C_OBJECT, _C_OPAQUE_NULL)

C_METHOD = _C_OPAQUE_PTR
C_INDEX = rffi.LONG
C_INDEX_ARRAY = rffi.LONGP
WLAVC_INDEX = rffi.LONG

C_METHPTRGETTER = lltype.FuncType([C_OBJECT], rffi.VOIDP)
C_METHPTRGETTER_PTR = lltype.Ptr(C_METHPTRGETTER)

def direct_ptradd(ptr, offset):
    offset = rffi.cast(rffi.SIZE_T, offset)
    jit.promote(offset)
    assert lltype.typeOf(ptr) == C_OBJECT
    address = rffi.cast(rffi.CCHARP, ptr)
    return rffi.cast(C_OBJECT, lltype.direct_ptradd(address, offset))

def exchange_address(ptr, cif_descr, index):
    return rffi.ptradd(ptr, cif_descr.exchange_args[index])
