"""
Support for valgrind: tell it when we patch code in-place.
"""

from rpython.rtyper.tool import rffi_platform
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rlib.objectmodel import we_are_translated


eci = ExternalCompilationInfo(includes = ['valgrind/valgrind.h'])

try:
    rffi_platform.verify_eci(eci)
except rffi_platform.CompilationError:
    VALGRIND_DISCARD_TRANSLATIONS = None
else:
    VALGRIND_DISCARD_TRANSLATIONS = rffi.llexternal(
        "VALGRIND_DISCARD_TRANSLATIONS",
        [llmemory.Address, lltype.Signed],
        lltype.Void,
        compilation_info=eci,
        _nowrapper=True,
        sandboxsafe=True)

# ____________________________________________________________

def discard_translations(data, size):
    #if we_are_translated() and VALGRIND_DISCARD_TRANSLATIONS is not None:
    VALGRIND_DISCARD_TRANSLATIONS(llmemory.cast_int_to_adr(data), size)
