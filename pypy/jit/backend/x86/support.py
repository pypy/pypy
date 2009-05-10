from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.translator.tool.cbuild import ExternalCompilationInfo

GC_MALLOC = lltype.Ptr(lltype.FuncType([lltype.Signed], llmemory.Address))

compilation_info = ExternalCompilationInfo(libraries=['gc'])

malloc_fn_ptr = rffi.llexternal("GC_malloc",
                                [lltype.Signed], # size_t, but good enough
                                llmemory.Address,
                                compilation_info=compilation_info,
                                sandboxsafe=True,
                                _nowrapper=True)

def gc_malloc_fnaddr():
    """Returns the address of the Boehm 'malloc' function."""
    return rffi.cast(lltype.Signed, malloc_fn_ptr)
