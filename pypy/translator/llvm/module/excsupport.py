
invokeunwind_code = '''
;XXX this should probably store the last_exception_type
ccc %(returntype)s%%__entrypoint__%(entrypointname)s {
    %%result = invoke %(cconv)s %(returntype)s%%%(entrypointname)s to label %%no_exception except label %%exception

no_exception:
    store %%RPYTHON_EXCEPTION_VTABLE* null, %%RPYTHON_EXCEPTION_VTABLE** %%last_exception_type
    ret %(returntype)s %%result

exception:
    ret %(noresult)s
}

ccc int %%__entrypoint__raised_LLVMException() {
    %%tmp    = load %%RPYTHON_EXCEPTION_VTABLE** %%last_exception_type
    %%result = cast %%RPYTHON_EXCEPTION_VTABLE* %%tmp to int
    ret int %%result
}

internal fastcc void %%unwind() {
    unwind
}
'''

explicit_code = '''
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

ccc int %%__entrypoint__raised_LLVMException() {
    %%tmp    = load %%RPYTHON_EXCEPTION_VTABLE** %%last_exception_type
    %%result = cast %%RPYTHON_EXCEPTION_VTABLE* %%tmp to int
    ret int %%result
}

internal fastcc void %%unwind() {
    ret void
}
'''

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

none_code = '''
ccc %(returntype)s%%__entrypoint__%(entrypointname)s {
    %%result = call %(cconv)s %(returntype)s%%%(entrypointname)s
    ret %(returntype)s %%result
}

ccc int %%__entrypoint__raised_LLVMException() {
    ret int 0
}

internal fastcc void %%unwind() {
    ret void
}
'''
