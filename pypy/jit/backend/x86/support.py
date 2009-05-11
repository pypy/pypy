from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.translator.tool.cbuild import ExternalCompilationInfo


def gc_malloc__boehm(gcdescr):
    """Returns a pointer to the Boehm 'malloc' function."""
    compilation_info = ExternalCompilationInfo(libraries=['gc'])
    malloc_fn_ptr = rffi.llexternal("GC_malloc",
                                    [lltype.Signed], # size_t, but good enough
                                    llmemory.Address,
                                    compilation_info=compilation_info,
                                    sandboxsafe=True,
                                    _nowrapper=True)
    return malloc_fn_ptr


def gc_malloc__framework(gcdescr):
    """Returns a pointer to the framework 'malloc' function."""
    return 0       # XXX write me!


def gc_malloc_fnaddr(gcdescr):
    """Returns a pointer to the proper 'malloc' function."""
    if gcdescr is not None:
        name = gcdescr.config.translation.gctransformer
    else:
        name = "boehm"
    try:
        func = globals()['gc_malloc__' + name]
    except KeyError:
        raise NotImplementedError("GC transformer %r not supported by "
                                  "the x86 backend" % (name,))
    return func(gcdescr)
