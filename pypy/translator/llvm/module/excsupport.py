
exctransform_code = '''
ccc %(returntype)s%%__entrypoint__%(entrypointname)s {
    store %%RPYTHON_EXCEPTION_VTABLE* null, %%RPYTHON_EXCEPTION_VTABLE** %%last_exception_type
    %%result = call %(cconv)s %(returntype)s%%%(entrypointname)s
    %%tmp    = load %%RPYTHON_EXCEPTION_VTABLE** %%last_exception_type
    %%exc    = seteq %%RPYTHON_EXCEPTION_VTABLE* %%tmp, null
    br bool %%exc, label %%no_exception, label %%exception

no_exception:
    ret %(returntype)s %%result

exception:
    ret %(noresult)s
}

;XXX this should use the transformation data that has the same purpose
ccc int %%__entrypoint__raised_LLVMException() {
    %%tmp    = load %%RPYTHON_EXCEPTION_VTABLE** %%last_exception_type
    %%result = cast %%RPYTHON_EXCEPTION_VTABLE* %%tmp to int
    ret int %%result
}

internal fastcc void %%unwind() {
    ret void
}
'''
