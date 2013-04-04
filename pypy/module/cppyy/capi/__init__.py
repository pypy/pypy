from rpython.rtyper.lltypesystem import rffi, lltype

# There are two possible ways of accessing the backend through the reflection
# C-API: built it into pypy-c, or load it dynamically. The latter is preferred
# (and is the default) for use with Reflex. B/c of some builtin pythonizations,
# the former is recommended (for now) with CINT.

# Note: if builtin_capi is chosen, then inside builtin_capi.py, there is still
# the selection of the desired backend (default is Reflex).

# choose C-API access method:
#from pypy.module.cppyy.capi.loadable_capi import *
from pypy.module.cppyy.capi.builtin_capi import *

from pypy.module.cppyy.capi.capi_types import C_OBJECT,\
    C_NULL_TYPE, C_NULL_OBJECT

def direct_ptradd(ptr, offset):
    offset = rffi.cast(rffi.SIZE_T, offset)
    jit.promote(offset)
    assert lltype.typeOf(ptr) == C_OBJECT
    address = rffi.cast(rffi.CCHARP, ptr)
    return rffi.cast(C_OBJECT, lltype.direct_ptradd(address, offset))

def exchange_address(ptr, cif_descr, index):
    return rffi.ptradd(ptr, cif_descr.exchange_args[index])
